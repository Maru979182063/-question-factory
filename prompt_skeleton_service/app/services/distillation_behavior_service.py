from __future__ import annotations

from collections import Counter
from typing import Any

from app.core.exceptions import DomainError
from app.schemas.distillation import (
    AgentAdjustmentPlan,
    BehaviorAggregateCount,
    BehaviorDistillationAggregateSummary,
    BehaviorDistillationExtractRequest,
    BehaviorDistillationPacket,
    BehaviorDistillationReport,
    BehaviorFinalOutcome,
    BehaviorItemTrace,
    BehaviorReportFinding,
    BehaviorReviewActionTrace,
    BehaviorUsageEventTrace,
    BehaviorVersionTrace,
    CandidatePatch,
    DifficultyDimension,
    DistillationEvidence,
)
from app.services.question_repository import QuestionRepository


class DistillationBehaviorService:
    def __init__(self, repository: QuestionRepository) -> None:
        self.repository = repository

    def build_packet(self, request: BehaviorDistillationExtractRequest) -> BehaviorDistillationPacket:
        item_ids = self._resolve_item_ids(request)
        item_traces = [self._build_item_trace(item_id) for item_id in item_ids]
        if not item_traces:
            raise DomainError(
                "No history-backed items matched the behavior distillation request.",
                status_code=404,
                details=request.model_dump(),
            )

        aggregate_summary = self._build_aggregate_summary(item_traces)
        candidate_patch_hints = self._build_candidate_patch_hints(item_traces, aggregate_summary)
        selected_agent_adjustment = self._select_agent_adjustment(candidate_patch_hints)
        report = self._build_report(item_traces, aggregate_summary, candidate_patch_hints)
        return BehaviorDistillationPacket(
            filters={
                "item_id": request.item_id,
                "question_type": request.question_type,
                "question_card_id": request.question_card_id,
                "limit": request.limit,
            },
            aggregate_summary=aggregate_summary,
            candidate_patch_hints=candidate_patch_hints,
            selected_agent_adjustment=selected_agent_adjustment,
            report=report,
            item_traces=item_traces if request.include_item_traces else [],
            notes=[
                "behavior distillation packet is extracted from question_item_versions, question_review_actions, and question_usage_events",
                "use this packet as a later-stage distillation input, not as an online self-learning source",
            ],
        )

    def _resolve_item_ids(self, request: BehaviorDistillationExtractRequest) -> list[str]:
        if request.item_id:
            if self.repository.get_item(request.item_id) is None:
                raise DomainError(
                    "Question item not found for behavior distillation.",
                    status_code=404,
                    details={"item_id": request.item_id},
                )
            return [request.item_id]

        candidate_ids: list[str] = []
        for unit in self.repository.list_feedback_backtest_units(
            question_type=request.question_type,
            question_card_id=request.question_card_id,
            limit=max(request.limit * 6, 120),
        ):
            item_id = str(unit.get("item_id") or "").strip()
            if item_id and item_id not in candidate_ids:
                candidate_ids.append(item_id)
            if len(candidate_ids) >= request.limit:
                return candidate_ids[: request.limit]

        fallback_items = self.repository.list_items(
            question_type=request.question_type,
            limit=max(request.limit * 6, 120),
        )
        for item in fallback_items:
            question_card_id = self._extract_question_card_id(item)
            if request.question_card_id and question_card_id != request.question_card_id:
                continue
            item_id = str(item.get("item_id") or "").strip()
            if item_id and item_id not in candidate_ids:
                candidate_ids.append(item_id)
            if len(candidate_ids) >= request.limit:
                break
        return candidate_ids[: request.limit]

    def _build_item_trace(self, item_id: str) -> BehaviorItemTrace:
        item = self.repository.get_item(item_id)
        if item is None:
            raise DomainError("Question item not found.", status_code=404, details={"item_id": item_id})
        history = self.repository.get_item_history(item_id) or {}
        versions = list(reversed(history.get("versions") or []))
        actions = list(reversed(history.get("review_actions") or []))
        usage_events = list(reversed(self.repository.list_usage_events(item_id=item_id, limit=100)))

        version_traces = [
            BehaviorVersionTrace(
                version_no=int(version.get("version_no") or 1),
                parent_version_no=version.get("parent_version_no"),
                source_action=str(version.get("source_action") or ""),
                target_difficulty=version.get("target_difficulty"),
                changed_fields=list((version.get("diff_summary") or {}).get("changed_fields") or []),
                material_changed=bool((version.get("diff_summary") or {}).get("material_changed")),
                difficulty_changed=bool((version.get("diff_summary") or {}).get("difficulty_changed")),
                prompt_changed=bool((version.get("diff_summary") or {}).get("prompt_changed")),
                stem_changed=bool((version.get("diff_summary") or {}).get("stem_changed")),
                options_changed=bool((version.get("diff_summary") or {}).get("options_changed")),
                analysis_changed=bool((version.get("diff_summary") or {}).get("analysis_changed")),
                created_at=version.get("created_at"),
            )
            for version in versions
        ]
        review_action_traces = [self._review_action_trace(action) for action in actions]
        usage_event_traces = [self._usage_event_trace(event) for event in usage_events]

        changed_field_counter: Counter[str] = Counter()
        failed_threshold_counter: Counter[str] = Counter()
        for trace in version_traces:
            changed_field_counter.update(trace.changed_fields)
        for trace in review_action_traces:
            changed_field_counter.update(trace.changed_fields)
            failed_threshold_counter.update(trace.failed_threshold_names)

        latest_download_variant = None
        for trace in reversed(usage_event_traces):
            if trace.event_type == "download":
                latest_download_variant = trace.download_variant

        final_outcome = self._infer_final_outcome(item, review_action_traces, latest_download_variant)
        return BehaviorItemTrace(
            item_id=item_id,
            question_type=item.get("question_type"),
            business_subtype=item.get("business_subtype"),
            question_card_id=self._extract_question_card_id(item),
            current_status=item.get("current_status"),
            current_version_no=int(item.get("current_version_no", 1) or 1),
            revision_count=int(item.get("revision_count", 0) or 0),
            final_outcome=final_outcome,
            latest_download_variant=latest_download_variant,
            version_traces=version_traces,
            review_action_traces=review_action_traces,
            usage_event_traces=usage_event_traces,
            hot_changed_fields=[entry[0] for entry in changed_field_counter.most_common(5)],
            failed_threshold_names=[entry[0] for entry in failed_threshold_counter.most_common(5)],
        )

    def _build_aggregate_summary(self, item_traces: list[BehaviorItemTrace]) -> BehaviorDistillationAggregateSummary:
        outcome_counter: Counter[str] = Counter()
        action_counter: Counter[str] = Counter()
        changed_field_counter: Counter[str] = Counter()
        threshold_counter: Counter[str] = Counter()
        truth_touched_count = 0
        material_boundary_cross_count = 0
        total_versions = 0
        total_review_actions = 0
        total_usage_events = 0
        total_downloads = 0

        for trace in item_traces:
            outcome_counter.update([trace.final_outcome])
            total_versions += len(trace.version_traces)
            total_review_actions += len(trace.review_action_traces)
            total_usage_events += len(trace.usage_event_traces)
            total_downloads += sum(1 for event in trace.usage_event_traces if event.event_type == "download")
            action_counter.update(action.action_type for action in trace.review_action_traces if action.action_type)
            changed_field_counter.update(trace.hot_changed_fields)
            for action in trace.review_action_traces:
                changed_field_counter.update(action.changed_fields)
                threshold_counter.update(action.failed_threshold_names)
                if action.truth_touched:
                    truth_touched_count += 1
                if action.material_boundary_crossed:
                    material_boundary_cross_count += 1

        item_count = len(item_traces)
        return BehaviorDistillationAggregateSummary(
            item_count=item_count,
            total_versions=total_versions,
            total_review_actions=total_review_actions,
            total_usage_events=total_usage_events,
            total_downloads=total_downloads,
            outcome_distribution=dict(outcome_counter),
            action_distribution=dict(action_counter),
            changed_field_distribution=dict(changed_field_counter),
            top_changed_fields=self._counter_entries(changed_field_counter),
            top_action_types=self._counter_entries(action_counter),
            top_failed_thresholds=self._counter_entries(threshold_counter),
            accepted_direct_rate=self._rate(outcome_counter.get("accepted_direct", 0), item_count),
            accepted_after_edit_rate=self._rate(outcome_counter.get("accepted_after_edit", 0), item_count),
            discard_rate=self._rate(outcome_counter.get("discarded", 0), item_count),
            download_rate=self._rate(total_downloads, item_count),
            truth_touched_rate=self._rate(truth_touched_count, total_review_actions),
            material_boundary_cross_rate=self._rate(material_boundary_cross_count, total_review_actions),
            recommended_hypotheses=self._recommended_hypotheses(
                outcome_counter=outcome_counter,
                changed_field_counter=changed_field_counter,
                threshold_counter=threshold_counter,
                item_count=item_count,
            ),
        )

    def _review_action_trace(self, action: dict[str, Any]) -> BehaviorReviewActionTrace:
        payload = dict(action.get("payload") or {})
        backtest = payload.get("feedback_backtest_unit") or {}
        return BehaviorReviewActionTrace(
            action_id=str(action.get("action_id") or ""),
            action_type=str(action.get("action_type") or ""),
            from_version_no=action.get("from_version_no"),
            to_version_no=action.get("to_version_no"),
            result_status=action.get("result_status"),
            operator=action.get("operator"),
            changed_fields=list(payload.get("changed_fields") or []),
            truth_touched=payload.get("truth_touched"),
            material_boundary_crossed=payload.get("material_boundary_crossed"),
            accepted_as_is=backtest.get("accepted_as_is"),
            revised_then_kept=backtest.get("revised_then_kept"),
            discarded=backtest.get("discarded"),
            failed_threshold_names=list(backtest.get("failed_threshold_names") or []),
            created_at=action.get("created_at"),
        )

    def _usage_event_trace(self, event: dict[str, Any]) -> BehaviorUsageEventTrace:
        payload = dict(event.get("payload") or {})
        return BehaviorUsageEventTrace(
            event_id=str(event.get("event_id") or ""),
            event_type=str(event.get("event_type") or ""),
            operator=event.get("operator"),
            download_variant=payload.get("download_variant"),
            created_at=event.get("created_at"),
            payload=payload,
        )

    def _infer_final_outcome(
        self,
        item: dict[str, Any],
        review_actions: list[BehaviorReviewActionTrace],
        latest_download_variant: str | None,
    ) -> BehaviorFinalOutcome:
        if latest_download_variant == "accepted_after_edit":
            return "accepted_after_edit"
        if latest_download_variant == "accepted_direct":
            return "accepted_direct"
        if any(action.discarded for action in review_actions) or str(item.get("current_status") or "") == "discarded":
            return "discarded"
        if any(action.revised_then_kept for action in review_actions) or int(item.get("revision_count", 0) or 0) > 0:
            return "accepted_after_edit"
        if any(action.accepted_as_is for action in review_actions) or str(item.get("current_status") or "") == "approved":
            return "accepted_direct"
        return "pending"

    def _build_candidate_patch_hints(
        self,
        item_traces: list[BehaviorItemTrace],
        summary: BehaviorDistillationAggregateSummary,
    ) -> list[CandidatePatch]:
        hints: list[CandidatePatch] = []
        thresholds = {entry.key for entry in summary.top_failed_thresholds}
        changed_fields = {entry.key: entry.count for entry in summary.top_changed_fields}
        actions = {entry.key: entry.count for entry in summary.top_action_types}

        if "options" in changed_fields or "distractor_similarity_low" in thresholds:
            hints.extend(
                self._build_patch_group(
                    dimension="distractor_similarity",
                    direction="raise",
                    priority="high" if (summary.accepted_after_edit_rate or 0.0) >= 0.4 else "medium",
                    target_payloads={
                        "question_card": {
                            "summary": "基于历史人工修题，提高 distractor 竞争度默认约束",
                            "payload": {"change": {"distractor_strength": "high"}},
                            "expected_effect": "减少用户反复手改 options 的情况。",
                        },
                        "prompt_assets": {
                            "summary": "把高频 options 人工修订模式回收成 distractor prompt 守卫",
                            "payload": {
                                "add_lines": [
                                    "错误项必须保持同题域、同语法位置、近长度，不要做成显眼假项。"
                                ]
                            },
                            "expected_effect": "让首轮生成更接近用户最终接受的干扰项风格。",
                        },
                        "validator_contract": {
                            "summary": "把高频失败阈值转成 distractor 竞争度校验",
                            "payload": {"require_checks": ["distractor_surface_similarity", "single_correct_answer_guard"]},
                            "expected_effect": "把需要人工兜底的弱干扰项提前挡掉。",
                        },
                    },
                    evidence=self._aggregate_evidence(item_traces, focus="options"),
                )
            )

        if "analysis" in changed_fields:
            hints.extend(
                self._build_patch_group(
                    dimension="blank_function_ambiguity",
                    direction="raise",
                    priority="medium",
                    target_payloads={
                        "prompt_assets": {
                            "summary": "基于历史解析改动，收紧 function/logic 解释口径",
                            "payload": {
                                "add_lines": [
                                    "analysis 必须明确解释正确项为何承担该空位功能，错误项为何在功能位或逻辑位失配。"
                                ]
                            },
                            "expected_effect": "减少用户对 analysis 的反复手工修订。",
                        },
                        "validator_contract": {
                            "summary": "为 analysis 补 function-role 一致性检查",
                            "payload": {"require_checks": ["function_role_alignment", "logic_relation_alignment"]},
                            "expected_effect": "提高题面和解析之间的功能绑定稳定性。",
                        },
                    },
                    evidence=self._aggregate_evidence(item_traces, focus="analysis"),
                )
            )

        if (summary.material_boundary_cross_rate or 0.0) >= 0.2:
            hints.extend(
                self._build_patch_group(
                    dimension="global_context_dependency",
                    direction="raise",
                    priority="medium",
                    target_payloads={
                        "material_mapping": {
                            "summary": "基于历史材料越界修订，调整材料映射优先级",
                            "payload": {"prefer_signals": ["paragraph_level_axis", "explicit_transition_anchor"]},
                            "expected_effect": "减少用户因为材料不撑题而手改材料或改题的情况。",
                        },
                        "question_card": {
                            "summary": "将材料支撑要求显式收回题卡契约",
                            "payload": {"change": {"semantic_scope": "paragraph_level", "context_dependency": "high"}},
                            "expected_effect": "让题卡提前约束对段落主轴的依赖。",
                        },
                    },
                    evidence=self._aggregate_evidence(item_traces, focus="material"),
                )
            )

        if (summary.truth_touched_rate or 0.0) >= 0.2:
            hints.extend(
                self._build_patch_group(
                    dimension="local_binding_complexity",
                    direction="raise",
                    priority="medium",
                    target_payloads={
                        "question_card": {
                            "summary": "基于历史 truth-like 改动，收紧题卡局部绑定要求",
                            "payload": {"change": {"bidirectional_validation": "high", "reference_dependency": "medium"}},
                            "expected_effect": "减少用户不得不去改 stem / answer / type slot 真值层字段的情况。",
                        },
                        "validator_contract": {
                            "summary": "增加局部绑定 hard guard",
                            "payload": {"require_checks": ["backward_anchor_alignment", "forward_anchor_alignment"]},
                            "expected_effect": "优先拦截需要修改真值层才能成立的候选题。",
                        },
                    },
                    evidence=self._aggregate_evidence(item_traces, focus="truth"),
                )
            )

        if not hints and actions.get("manual_edit", 0):
            hints.extend(
                self._build_patch_group(
                    dimension="blank_function_ambiguity",
                    direction="raise",
                    priority="low",
                    target_payloads={
                        "prompt_assets": {
                            "summary": "把通用 manual_edit 模式回收到 prompt guard",
                            "payload": {"add_lines": ["先判断空位功能，再生成和解释选项。"]},
                            "expected_effect": "给后续行为蒸馏留一个最小可执行抓手。",
                        }
                    },
                    evidence=self._aggregate_evidence(item_traces, focus="manual_edit"),
                )
            )
        return hints

    def _build_patch_group(
        self,
        *,
        dimension: DifficultyDimension,
        direction: str,
        priority: str,
        target_payloads: dict[str, dict[str, Any]],
        evidence: list[DistillationEvidence],
    ) -> list[CandidatePatch]:
        patches: list[CandidatePatch] = []
        for target, payload in target_payloads.items():
            patches.append(
                CandidatePatch(
                    patch_id=f"behavior.{target}.{dimension}.{direction}",
                    target=target,  # type: ignore[arg-type]
                    dimension=dimension,
                    direction=direction,  # type: ignore[arg-type]
                    priority=priority,  # type: ignore[arg-type]
                    summary=str(payload.get("summary") or ""),
                    rationale=f"derived from stable human edit traces for {dimension}",
                    proposed_change=dict(payload.get("payload") or {}),
                    expected_effect=str(payload.get("expected_effect") or ""),
                    evidence=evidence,
                )
            )
        return patches

    def _aggregate_evidence(self, item_traces: list[BehaviorItemTrace], *, focus: str) -> list[DistillationEvidence]:
        sample_items = item_traces[:3]
        payload = {
            "focus": focus,
            "item_ids": [item.item_id for item in sample_items],
            "final_outcomes": [item.final_outcome for item in sample_items],
            "hot_changed_fields": [item.hot_changed_fields for item in sample_items],
            "failed_threshold_names": [item.failed_threshold_names for item in sample_items],
        }
        return [
            DistillationEvidence(
                source="behavior_trace_aggregate",
                summary=f"human edit aggregate focused on {focus}",
                payload=payload,
            )
        ]

    def _select_agent_adjustment(self, patches: list[CandidatePatch]) -> AgentAdjustmentPlan | None:
        if not patches:
            return None
        selected = patches[: min(3, len(patches))]
        return AgentAdjustmentPlan(
            round_label="behavior_distillation_round1",
            selected_patch_ids=[patch.patch_id for patch in selected],
            instruction_summary="Apply the top behavior-derived patch hints offline, then compare whether manual edits and discard rates decrease on the next replay batch.",
            evaluation_focus=[patch.dimension for patch in selected],
            stop_conditions=[
                "manual_edit remains the dominant final path",
                "discard rate does not improve after applying the selected hints",
            ],
        )

    def _build_report(
        self,
        item_traces: list[BehaviorItemTrace],
        summary: BehaviorDistillationAggregateSummary,
        patches: list[CandidatePatch],
    ) -> BehaviorDistillationReport:
        findings: list[BehaviorReportFinding] = []
        if (summary.accepted_after_edit_rate or 0.0) > (summary.accepted_direct_rate or 0.0):
            findings.append(
                BehaviorReportFinding(
                    finding_id="after_edit_dominant",
                    severity="high",
                    title="修改后保留多于直接通过",
                    summary="当前首轮出题与最终可用题之间存在稳定人工修订带，适合做行为蒸馏。",
                    evidence={
                        "accepted_after_edit_rate": summary.accepted_after_edit_rate,
                        "accepted_direct_rate": summary.accepted_direct_rate,
                    },
                )
            )
        if summary.top_changed_fields:
            findings.append(
                BehaviorReportFinding(
                    finding_id="hot_fields",
                    severity="medium",
                    title="高频改动字段已收敛",
                    summary="用户修改集中在少数几个字段，说明可控项已经有明确蒸馏入口。",
                    evidence={"top_changed_fields": [entry.model_dump() for entry in summary.top_changed_fields]},
                )
            )
        if summary.top_failed_thresholds:
            findings.append(
                BehaviorReportFinding(
                    finding_id="threshold_failures",
                    severity="medium",
                    title="失败阈值可直接转蒸馏输入",
                    summary="已有高频失败阈值记录，后续可以直接接入 validator contract 蒸馏。",
                    evidence={"top_failed_thresholds": [entry.model_dump() for entry in summary.top_failed_thresholds]},
                )
            )

        executive_summary = (
            f"行为蒸馏已覆盖 {summary.item_count} 道题、{summary.total_review_actions} 次 review action、"
            f"{summary.total_downloads} 次 download 事件；当前最值得优先吸收的信号是 "
            f"{', '.join(entry.key for entry in summary.top_changed_fields[:3]) or '高频改动字段尚未收敛'}。"
        )
        next_steps = [
            "先应用前 1-3 个 behavior candidate patch hints 到离线回放环境。",
            "重新比较 accepted_after_edit_rate、discard_rate 和 top_failed_thresholds 是否下降。",
            "再把 behavior report 与 truth distillation report 对齐，看两条链是否指向同一组 patch 目标。",
        ]
        if patches:
            next_steps.insert(1, f"当前已生成 {len(patches)} 个 candidate patch hints，可直接进入人工审核。")
        return BehaviorDistillationReport(
            executive_summary=executive_summary,
            findings=findings,
            recommended_next_steps=next_steps,
        )

    @staticmethod
    def _extract_question_card_id(item: dict[str, Any]) -> str | None:
        request_snapshot = item.get("request_snapshot") if isinstance(item.get("request_snapshot"), dict) else {}
        material_selection = item.get("material_selection") if isinstance(item.get("material_selection"), dict) else {}
        value = str(
            request_snapshot.get("question_card_id")
            or material_selection.get("question_card_id")
            or ""
        ).strip()
        return value or None

    @staticmethod
    def _counter_entries(counter: Counter[str], limit: int = 5) -> list[BehaviorAggregateCount]:
        return [BehaviorAggregateCount(key=key, count=count) for key, count in counter.most_common(limit)]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        if denominator <= 0:
            return None
        return round(numerator / denominator, 4)

    def _recommended_hypotheses(
        self,
        *,
        outcome_counter: Counter[str],
        changed_field_counter: Counter[str],
        threshold_counter: Counter[str],
        item_count: int,
    ) -> list[str]:
        hypotheses: list[str] = []
        accepted_after_edit_rate = self._rate(outcome_counter.get("accepted_after_edit", 0), item_count) or 0.0
        accepted_direct_rate = self._rate(outcome_counter.get("accepted_direct", 0), item_count) or 0.0
        discard_rate = self._rate(outcome_counter.get("discarded", 0), item_count) or 0.0

        if accepted_after_edit_rate > accepted_direct_rate:
            hypotheses.append("修改后保留占比高于直接通过，说明当前基础出题与最终可用题之间存在稳定人工修订模式。")
        if discard_rate >= 0.3:
            hypotheses.append("discard 占比偏高，建议把高频失败阈值和高频改动字段纳入下一轮 validator / prompt 蒸馏。")
        if changed_field_counter.get("options", 0) >= max(2, item_count // 2):
            hypotheses.append("options 是高频改动字段，优先检查 distractor 构造和唯一正确性口径。")
        if changed_field_counter.get("analysis", 0) >= max(2, item_count // 2):
            hypotheses.append("analysis 是高频改动字段，说明解析协议与题面真值绑定还不够稳定。")
        if threshold_counter:
            hypotheses.append("已有高频失败阈值记录，可把这些阈值直接转成 behavior distillation 的 validator contract 候选输入。")
        if not hypotheses:
            hypotheses.append("当前历史动作样本量仍偏少，先继续沉淀版本链和 review action，再观察稳定修订模式。")
        return hypotheses

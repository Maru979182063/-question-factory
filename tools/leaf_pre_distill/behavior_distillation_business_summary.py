from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUMMARY_ARTIFACT_NAMES = {
    "summary": "behavior_distillation_business_summary.json",
    "report": "behavior_distillation_business_report.md",
    "formalization_evidence": "behavior_distillation_formalization_evidence.json",
    "view": "behavior_distillation_business_view.json",
    "view_report": "behavior_distillation_business_view_report.md",
}

TARGET_LAYER_VALUES = {
    "question_card",
    "material_card",
    "prompt_assets",
    "validator_contract",
    "runtime_mapping",
    "material_mapping",
    "review_process",
    "unknown",
}


def run_behavior_distillation_business_summary(
    *,
    output_dir: str | Path,
    behavior_packet_path: str | Path | None = None,
    run_detail_path: str | Path | None = None,
    agent_review_feedback_path: str | Path | None = None,
    validator_result_path: str | Path | None = None,
    truth_gold_regression_results_path: str | Path | None = None,
    material_quality_regression_results_path: str | Path | None = None,
) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    behavior_packet = _load_optional_json(behavior_packet_path)
    run_detail = _load_optional_json(run_detail_path)
    feedback = _load_optional_json(agent_review_feedback_path)
    validator_result = _load_optional_json(validator_result_path)
    truth_regression = _load_optional_json(truth_gold_regression_results_path)
    material_regression = _load_optional_json(material_quality_regression_results_path)
    summary = build_behavior_distillation_business_summary(
        behavior_packet=behavior_packet,
        run_detail=run_detail,
        agent_review_feedback=feedback,
        validator_result=validator_result,
        truth_gold_regression=truth_regression,
        material_quality_regression=material_regression,
        source_paths={
            "behavior_packet_path": str(behavior_packet_path or ""),
            "run_detail_path": str(run_detail_path or ""),
            "agent_review_feedback_path": str(agent_review_feedback_path or ""),
            "validator_result_path": str(validator_result_path or ""),
            "truth_gold_regression_results_path": str(truth_gold_regression_results_path or ""),
            "material_quality_regression_results_path": str(material_quality_regression_results_path or ""),
        },
    )
    report = render_behavior_distillation_business_report(summary)
    evidence = build_behavior_distillation_formalization_evidence(summary)
    view = build_behavior_distillation_business_view(summary=summary, run_detail=run_detail)
    view_report = render_behavior_distillation_business_view_report(view)
    summary_path = output_path / SUMMARY_ARTIFACT_NAMES["summary"]
    report_path = output_path / SUMMARY_ARTIFACT_NAMES["report"]
    evidence_path = output_path / SUMMARY_ARTIFACT_NAMES["formalization_evidence"]
    view_path = output_path / SUMMARY_ARTIFACT_NAMES["view"]
    view_report_path = output_path / SUMMARY_ARTIFACT_NAMES["view_report"]
    _write_json(summary_path, summary)
    report_path.write_text(report, encoding="utf-8")
    _write_json(evidence_path, evidence)
    _write_json(view_path, view)
    view_report_path.write_text(view_report, encoding="utf-8")
    return {
        "behavior_distillation_business_summary": str(summary_path),
        "behavior_distillation_business_report": str(report_path),
        "behavior_distillation_formalization_evidence": str(evidence_path),
        "behavior_distillation_business_view": str(view_path),
        "behavior_distillation_business_view_report": str(view_report_path),
    }


def build_behavior_distillation_business_summary(
    *,
    behavior_packet: dict[str, Any] | None = None,
    run_detail: dict[str, Any] | None = None,
    agent_review_feedback: dict[str, Any] | None = None,
    validator_result: dict[str, Any] | None = None,
    truth_gold_regression: dict[str, Any] | None = None,
    material_quality_regression: dict[str, Any] | None = None,
    source_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_paths = source_paths or {}
    aggregate = (behavior_packet or {}).get("aggregate_summary") or {}
    source = {
        "behavior_packet_path": source_paths.get("behavior_packet_path", ""),
        "run_id": str((behavior_packet or {}).get("run_id") or (run_detail or {}).get("run_id") or ""),
        "sample_count": _as_int(aggregate.get("item_count") or (run_detail or {}).get("sample_count")),
        "review_count": _as_int(aggregate.get("total_review_actions") or (run_detail or {}).get("review_count")),
        "patch_count": _as_int(aggregate.get("total_patch_actions") or (run_detail or {}).get("patch_count")),
        "promotion_count": _as_int(aggregate.get("total_promotion_actions") or (run_detail or {}).get("promotion_count")),
    }
    missing = _missing_inputs(
        behavior_packet=behavior_packet,
        run_detail=run_detail,
        agent_review_feedback=agent_review_feedback,
        validator_result=validator_result,
        truth_gold_regression=truth_gold_regression,
        material_quality_regression=material_quality_regression,
    )
    edit_fields = _collect_edit_fields(behavior_packet, run_detail)
    failure_patterns = _collect_failure_patterns(behavior_packet, validator_result)
    feedback_items = _collect_user_feedback(agent_review_feedback)
    candidates = _build_candidate_signals(
        edit_fields=edit_fields,
        failure_patterns=failure_patterns,
        feedback_items=feedback_items,
        behavior_packet=behavior_packet or {},
        truth_gold_regression=truth_gold_regression,
        material_quality_regression=material_quality_regression,
    )
    not_recommended = [
        {
            "signal_id": item["signal_id"],
            "reason": item["reason"],
            "recommended_status": item["recommended_status"],
        }
        for item in candidates
        if item.get("recommended_status") in {"single_case_only", "do_not_promote", "blocked"}
    ]
    blocking_issues = []
    if not behavior_packet:
        blocking_issues.append("behavior_packet_missing")
    if source["review_count"] <= 0:
        blocking_issues.append("review_records_missing")
    if _has_conflict(validator_result) or _has_conflict(truth_gold_regression) or _has_conflict(material_quality_regression):
        blocking_issues.append("validator_or_regression_conflict")
    overview = _business_overview(aggregate, source, candidates, blocking_issues)
    summary = {
        "summary_version": "v1",
        "status": "blocked" if blocking_issues else ("partial" if missing else "completed"),
        "formalized": False,
        "writeback_allowed": False,
        "executor_allowed": False,
        "requires_human_review": True,
        "source": source,
        "business_overview": overview,
        "high_frequency_edit_fields": edit_fields,
        "high_frequency_failure_patterns": failure_patterns,
        "high_frequency_user_feedback": feedback_items,
        "candidate_improvement_signals": candidates,
        "not_recommended_for_promotion": not_recommended,
        "missing_evidence": missing,
        "blocking_issues": blocking_issues,
        "recommended_next_action": _recommended_next_action(source, candidates, blocking_issues),
    }
    assert_business_summary_boundaries(summary)
    return summary


def render_behavior_distillation_business_report(summary: dict[str, Any]) -> str:
    overview = summary.get("business_overview") or {}
    source = summary.get("source") or {}
    lines = [
        "# Behavior Distillation Business Summary",
        "",
        "> 业务蒸馏结果是 evidence，不是正式配置；高频修改不等于自动改题卡，这里不会调用 executor。",
        "",
        "## 审核总体情况",
        "",
        f"- 样本数: {source.get('sample_count', 0)}",
        f"- 审核动作: {source.get('review_count', 0)}",
        f"- 补丁动作: {source.get('patch_count', 0)}",
        f"- 晋级记录: {source.get('promotion_count', 0)}",
        f"- 主导模式: {overview.get('dominant_review_pattern') or 'unknown'}",
        f"- 总体质量信号: {overview.get('overall_quality_signal') or 'unknown'}",
        "",
        "## 人话摘要",
        "",
        _human_overview_sentence(summary),
        "",
        "## 高频修改字段",
        "",
    ]
    edit_fields = summary.get("high_frequency_edit_fields") or []
    if edit_fields:
        for item in edit_fields:
            lines.append(f"- `{item.get('field')}` 出现 {item.get('count', 0)} 次：{_field_business_sentence(item.get('field'))}")
    else:
        lines.append("- 暂未观察到稳定的高频修改字段。")
    lines.extend(["", "## 高频失败模式", ""])
    failures = summary.get("high_frequency_failure_patterns") or []
    if failures:
        for item in failures:
            lines.append(f"- `{item.get('pattern')}` 出现 {item.get('count', 0)} 次：{item.get('business_description')}")
    else:
        lines.append("- 暂未观察到稳定的高频失败模式。")
    lines.extend(["", "## 候选沉淀建议", ""])
    candidates = summary.get("candidate_improvement_signals") or []
    if candidates:
        for item in candidates:
            lines.append(
                f"- {item.get('business_description')} target_layer=`{item.get('target_layer')}`, "
                f"support=`{item.get('support_level')}`, risk=`{item.get('risk_level')}`, "
                f"status=`{item.get('recommended_status')}`。{item.get('reason')}"
            )
    else:
        lines.append("- 还没有足够行为证据形成候选沉淀建议。")
    lines.extend(["", "## 不建议沉淀项", ""])
    skipped = summary.get("not_recommended_for_promotion") or []
    if skipped:
        for item in skipped:
            lines.append(f"- `{item.get('signal_id')}`: {item.get('reason')}")
    else:
        lines.append("- 当前没有明确的不建议沉淀项。")
    lines.extend(
        [
            "",
            "## 下一步建议",
            "",
            f"- `{summary.get('recommended_next_action')}`",
            "- 正式落位仍需 formalization packet、readiness gate、人审、回归和受控写回。",
            "- 单个用户反馈不能直接沉淀为规则。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_behavior_distillation_formalization_evidence(summary: dict[str, Any]) -> dict[str, Any]:
    suitable = [
        item.get("signal_id")
        for item in summary.get("candidate_improvement_signals") or []
        if item.get("recommended_status") == "suitable_for_formalization_packet"
    ]
    evidence = {
        "evidence_version": "v1",
        "artifact_type": "behavior_distillation_formalization_evidence",
        "promotion_evidence_only": True,
        "attach_to": "leaf_pre_distill_report",
        "direct_formal_config": False,
        "independent_promotion_target": False,
        "formalized": False,
        "writeback_allowed": False,
        "executor_allowed": False,
        "summary_ref": SUMMARY_ARTIFACT_NAMES["summary"],
        "report_ref": SUMMARY_ARTIFACT_NAMES["report"],
        "suitable_signal_ids": suitable,
    }
    assert_business_summary_boundaries(evidence)
    return evidence


def build_behavior_distillation_business_view(
    *,
    summary: dict[str, Any],
    run_detail: dict[str, Any] | None = None,
    formalization_packet: dict[str, Any] | None = None,
    readiness_gate: dict[str, Any] | None = None,
    before_after_pairs: list[dict[str, Any]] | None = None,
    technical_refs: list[str] | None = None,
) -> dict[str, Any]:
    source = summary.get("source") or {}
    overview = summary.get("business_overview") or {}
    packet_context = (formalization_packet or {}).get("family_context") or {}
    run_context = (run_detail or {}).get("family_context") or {}
    stage = _infer_business_stage(summary=summary, formalization_packet=formalization_packet, readiness_gate=readiness_gate)
    comparisons = _extract_before_after_comparisons(before_after_pairs=before_after_pairs, run_detail=run_detail, summary=summary)
    action_clusters = _build_action_clusters(summary)
    problem_summary = _build_business_problem_summary(summary)
    missing = list(summary.get("missing_evidence") or [])
    if not comparisons:
        for item in [
            "missing_before_after_question_pair",
            "missing_same_material_parameter_trace",
            "missing_validator_before_after_result",
        ]:
            if item not in missing:
                missing.append(item)
    landing = _build_landing_status(summary=summary, formalization_packet=formalization_packet, readiness_gate=readiness_gate)
    view = {
        "view_version": "v1",
        "status": summary.get("status") or "partial",
        "formalized": False,
        "writeback_allowed": False,
        "executor_allowed": False,
        "family_context": {
            "stage": stage,
            "leaf_id": packet_context.get("child_family_id") or run_context.get("child_family_id") or source.get("run_id") or "unknown",
            "question_type": packet_context.get("mother_family_id") or run_context.get("question_type") or "unknown",
            "business_subtype": packet_context.get("business_subtype") or run_context.get("business_subtype") or packet_context.get("leaf_label") or "unknown",
            "sample_count": source.get("sample_count", 0),
            "review_count": source.get("review_count", 0),
            "patch_count": source.get("patch_count", 0),
            "promotion_count": source.get("promotion_count", 0),
            "overall_status": _quality_label(overview.get("overall_quality_signal")),
        },
        "business_problem_summary": problem_summary,
        "action_clusters": action_clusters,
        "action_problem_items": _build_action_problem_items(problem_summary, action_clusters),
        "distilled_recommendations": _build_distilled_recommendations(summary),
        "before_after_comparisons": comparisons,
        "landing_status": landing,
        "technical_refs": technical_refs or [
            "behavior_distillation_business_summary.json",
            "behavior_distillation_formalization_evidence.json",
        ],
        "missing_evidence": missing,
    }
    assert_business_summary_boundaries(view)
    return view


def render_behavior_distillation_business_view_report(view: dict[str, Any]) -> str:
    context = view.get("family_context") or {}
    landing = view.get("landing_status") or {}
    lines = [
        "# 业务视图：本阶段叶族问题与沉淀建议",
        "",
        "> 业务蒸馏结果是 evidence，不是正式配置；blocked 不等于失败，只表示当前证据或流程还没满足落位条件。",
        "",
        "## 当前阶段与叶族",
        "",
        f"- 当前阶段：{context.get('stage')}",
        f"- 当前题型或叶族：{context.get('leaf_id')}",
        f"- 样本数：{context.get('sample_count', 0)}",
        f"- 审核数：{context.get('review_count', 0)}",
        f"- 修改数：{context.get('patch_count', 0)}",
        f"- 沉淀包数：{context.get('promotion_count', 0)}",
        f"- 当前整体状态：{context.get('overall_status')}",
        "",
        "## 高频问题抽象",
        "",
    ]
    problems = view.get("business_problem_summary") or []
    if problems:
        for item in problems:
            lines.append(f"- {item.get('problem_name')}：{item.get('business_explanation')} 证据：{item.get('evidence_source')}；建议：{item.get('current_suggestion')}")
    else:
        lines.append("- 当前没有足够重复出现的问题，建议继续观察。")
    lines.extend(["", "## 蒸馏后结果", ""])
    recommendations = view.get("distilled_recommendations") or []
    if recommendations:
        for item in recommendations:
            lines.append(f"- {item.get('recommendation')} 建议进入：{item.get('asset_label')}；风险：{item.get('risk')}；缺口：{', '.join(item.get('missing_evidence') or []) or '暂无明确缺口'}。")
    else:
        lines.append("- 暂无可送审的沉淀建议。")
    lines.extend(["", "## 前后题目对比", ""])
    comparisons = view.get("before_after_comparisons") or []
    if comparisons:
        for item in comparisons:
            lines.append(f"- 同一材料参数 `{item.get('material_parameter')}`：修改字段 `{item.get('changed_fields')}`，原因：{item.get('change_reason')}")
    else:
        lines.append("- 当前行为蒸馏包缺少可展示的 before/after 题目对比。需要接入 review version chain 或 patch diff 后展示。")
    lines.extend(
        [
            "",
            "## 当前是否可以落位",
            "",
            f"- 当前能否落位：{landing.get('landing_label')}",
            f"- 不能落位的原因：{', '.join(landing.get('blocked_reasons') or []) or '无'}",
            f"- 下一步建议：{landing.get('next_action')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_business_problem_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    for item in summary.get("high_frequency_edit_fields") or []:
        field = item.get("field")
        problems.append(
            {
                "problem_name": _problem_name(field),
                "business_explanation": item.get("business_description") or _field_business_sentence(field),
                "evidence_source": "审核修改字段",
                "support": _support_label(item.get("count")),
                "current_suggestion": _status_label(_status_for_support(item.get("count"))),
                "technical_detail": {"field": field, "count": item.get("count", 0)},
            }
        )
    for item in summary.get("high_frequency_failure_patterns") or []:
        pattern = item.get("pattern")
        problems.append(
            {
                "problem_name": _problem_name(pattern),
                "business_explanation": item.get("business_description") or _failure_business_sentence(pattern),
                "evidence_source": "失败模式统计",
                "support": _support_label(item.get("count")),
                "current_suggestion": _status_label(_status_for_support(item.get("count"))),
                "technical_detail": {"pattern": pattern, "count": item.get("count", 0)},
            }
        )
    for item in summary.get("high_frequency_user_feedback") or []:
        feedback = item.get("feedback") or item.get("dimension")
        problems.append(
            {
                "problem_name": _problem_name(feedback),
                "business_explanation": _feedback_business_sentence(str(feedback or "")),
                "evidence_source": "用户反馈",
                "support": _support_label(item.get("count")),
                "current_suggestion": _status_label(_status_for_support(item.get("count"))),
                "technical_detail": {"dimension": item.get("dimension"), "severity": item.get("severity"), "count": item.get("count", 0)},
            }
        )
    return problems[:12]


def _build_action_clusters(summary: dict[str, Any]) -> list[dict[str, Any]]:
    source = summary.get("source") or {}
    leaf_id = source.get("run_id") or "unknown"
    clusters = []
    for item in summary.get("high_frequency_edit_fields") or []:
        field = item.get("field") or "unknown"
        count = _as_int(item.get("count"))
        clusters.append(
            {
                "cluster_id": _slug(f"{leaf_id}_{field}")[:90],
                "leaf_id": leaf_id,
                "modified_field": field,
                "affected_items": [],
                "action_types": ["patch_or_review_edit"],
                "repeated_action": f"{count} 次集中修改 {_problem_name(field)}",
                "count": count,
            }
        )
    return sorted(clusters, key=lambda item: (-_as_int(item.get("count")), str(item.get("modified_field"))))


def _build_action_problem_items(problems: list[dict[str, Any]], action_clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for index, problem in enumerate(problems):
        cluster = next(
            (item for item in action_clusters if _problem_name(item.get("modified_field")) == problem.get("problem_name")),
            action_clusters[index] if index < len(action_clusters) else {},
        )
        items.append(
            {
                "problem_id": f"problem_{index + 1}",
                "title": problem.get("problem_name"),
                "affected_leaf": cluster.get("leaf_id") or "unknown",
                "affected_items": cluster.get("affected_items") or [],
                "repeated_action": cluster.get("repeated_action") or f"{problem.get('support')} 的相似修改",
                "modified_fields": [cluster.get("modified_field")] if cluster.get("modified_field") else [],
                "inferred_from_actions": f"{problem.get('evidence_source')}：{cluster.get('repeated_action') or problem.get('support')}",
                "business_judgment": problem.get("business_explanation"),
                "status_label": problem.get("current_suggestion"),
                "technical_detail": problem.get("technical_detail") or {},
            }
        )
    return items


def _build_distilled_recommendations(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for signal in summary.get("candidate_improvement_signals") or []:
        rows.append(
            {
                "recommendation": signal.get("business_description"),
                "asset_label": _asset_label(signal.get("target_layer")),
                "reason": signal.get("reason"),
                "risk": _risk_label(signal.get("risk_level")),
                "status_label": _status_label(signal.get("recommended_status")),
                "missing_evidence": _missing_for_signal(signal, summary),
                "technical_detail": {
                    "signal_id": signal.get("signal_id"),
                    "target_layer": signal.get("target_layer"),
                    "recommended_status": signal.get("recommended_status"),
                },
            }
        )
    return rows


def _extract_before_after_comparisons(
    *,
    before_after_pairs: list[dict[str, Any]] | None,
    run_detail: dict[str, Any] | None,
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = before_after_pairs or summary.get("before_after_comparisons") or (run_detail or {}).get("before_after_comparisons") or []
    comparisons: list[dict[str, Any]] = []
    for item in candidates if isinstance(candidates, list) else []:
        before = item.get("before") or item.get("before_question") or item.get("original_question")
        after = item.get("after") or item.get("after_question") or item.get("modified_question")
        if before is None or after is None:
            continue
        comparisons.append(
            {
                "material_parameter": item.get("material_parameter") or item.get("material_params") or "unknown",
                "before_question": before,
                "after_question": after,
                "changed_fields": item.get("changed_fields") or item.get("field") or [],
                "change_reason": item.get("change_reason") or item.get("reason") or "",
                "validator_result_change": item.get("validator_result_change") or item.get("validator_delta") or "unknown",
                "human_review_change": item.get("human_review_change") or item.get("review_delta") or "unknown",
            }
        )
    return comparisons


def _build_landing_status(
    *,
    summary: dict[str, Any],
    formalization_packet: dict[str, Any] | None,
    readiness_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    signals = summary.get("candidate_improvement_signals") or []
    suitable = [item for item in signals if item.get("recommended_status") == "suitable_for_formalization_packet"]
    blocked_reasons = list(summary.get("blocking_issues") or [])
    if summary.get("missing_evidence"):
        blocked_reasons.extend(f"缺少证据:{item}" for item in summary.get("missing_evidence") or [])
    if formalization_packet and formalization_packet.get("blocking_issues"):
        blocked_reasons.extend(f"送审包:{item}" for item in formalization_packet.get("blocking_issues") or [])
    if readiness_gate and readiness_gate.get("blocking_issues"):
        blocked_reasons.extend(f"readiness:{item}" for item in readiness_gate.get("blocking_issues") or [])
    can_enter_packet = bool(suitable) and summary.get("status") != "blocked"
    can_enter_review = summary.get("status") != "blocked" and bool(signals)
    return {
        "can_formalize": False,
        "can_enter_formalization_packet": can_enter_packet,
        "can_enter_review": can_enter_review,
        "landing_label": "仅可进入送审包" if can_enter_packet else ("仅可继续观察" if can_enter_review else "不能落位"),
        "blocked_reasons": sorted(set(blocked_reasons)),
        "next_action": _business_next_action(summary.get("recommended_next_action")),
    }


def _infer_business_stage(
    *,
    summary: dict[str, Any],
    formalization_packet: dict[str, Any] | None,
    readiness_gate: dict[str, Any] | None,
) -> str:
    if readiness_gate:
        return "readiness"
    if formalization_packet:
        return "formalization review"
    action = summary.get("recommended_next_action")
    if action == "formalization_packet":
        return "review / packet"
    if action == "blocked":
        return "blocked review"
    return "proto trial / review"


def _problem_name(value: Any) -> str:
    text = str(value or "").lower()
    raw = str(value or "")
    if "distractor" in text or "option" in text or "干扰" in raw:
        return "干扰项不够迷惑"
    if "material" in text or "passage" in text or "source" in text or "材料" in raw:
        return "材料上下文不足"
    if "真题" in raw or "style" in text:
        return "题目不像真题"
    if "answer" in text or "答案" in raw:
        return "答案稳定性风险"
    if "analysis" in text or "解析" in raw:
        return "解析说服力不足"
    return raw or "未命名问题"


def _asset_label(target_layer: Any) -> str:
    labels = {
        "question_card": "题卡",
        "material_card": "材料卡",
        "prompt_assets": "prompt",
        "validator_contract": "validator",
        "runtime_mapping": "runtime",
        "material_mapping": "材料映射",
        "review_process": "审核流程",
        "unknown": "仅观察",
    }
    return labels.get(str(target_layer or "unknown"), "仅观察")


def _status_label(status: Any) -> str:
    labels = {
        "suitable_for_formalization_packet": "建议进入送审包",
        "observe_more": "继续观察",
        "needs_more_samples": "继续观察",
        "single_case_only": "仅个例，不沉淀",
        "do_not_promote": "不沉淀",
        "blocked": "证据冲突，blocked",
    }
    return labels.get(str(status or ""), "继续观察")


def _risk_label(risk: Any) -> str:
    return {"low": "低", "medium": "中", "high": "高，暂缓"}.get(str(risk or ""), "未知")


def _support_label(count: Any) -> str:
    value = _as_int(count)
    if value >= 3:
        return f"高频，出现 {value} 次"
    if value == 2:
        return "中等支持，出现 2 次"
    if value == 1:
        return "单例，出现 1 次"
    return "暂无计数"


def _status_for_support(count: Any) -> str:
    value = _as_int(count)
    if value >= 3:
        return "observe_more"
    if value == 1:
        return "single_case_only"
    return "observe_more"


def _quality_label(value: Any) -> str:
    return {
        "stable": "稳定",
        "needs_attention": "需关注",
        "blocked": "blocked",
        "unknown": "继续观察",
    }.get(str(value or "unknown"), "继续观察")


def _business_next_action(value: Any) -> str:
    return {
        "human_review": "先人工确认候选沉淀点",
        "observe_more": "继续观察更多样本",
        "formalization_packet": "可进入送审包，但不能直接落位",
        "collect_more_samples": "补充更多样本和回归证据",
        "blocked": "先处理阻塞证据",
    }.get(str(value or ""), "继续观察更多样本")


def _missing_for_signal(signal: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    missing = []
    if signal.get("requires_human_confirmation", True):
        missing.append("人工确认")
    if signal.get("requires_regression", True):
        missing.append("回归证据")
    for item in summary.get("missing_evidence") or []:
        if "regression" in str(item):
            missing.append(str(item))
    return sorted(set(missing))


def _collect_edit_fields(behavior_packet: dict[str, Any] | None, run_detail: dict[str, Any] | None) -> list[dict[str, Any]]:
    aggregate = (behavior_packet or {}).get("aggregate_summary") or {}
    fields = aggregate.get("top_changed_fields") or aggregate.get("changed_field_distribution") or []
    items = _normalize_count_items(fields, "field")
    patches = (run_detail or {}).get("latest_patches") or (run_detail or {}).get("patches") or []
    counts = {item["field"]: _as_int(item.get("count")) for item in items}
    for patch in patches if isinstance(patches, list) else []:
        field = patch.get("field") or patch.get("target") or patch.get("target_layer")
        if field:
            counts[str(field)] = counts.get(str(field), 0) + 1
    return [
        {
            "field": field,
            "count": count,
            "business_description": _field_business_sentence(field),
        }
        for field, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
        if count > 0
    ]


def _collect_failure_patterns(behavior_packet: dict[str, Any] | None, validator_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    aggregate = (behavior_packet or {}).get("aggregate_summary") or {}
    patterns = _normalize_count_items(aggregate.get("top_failed_thresholds") or aggregate.get("failure_patterns") or [], "pattern")
    counts = {item["pattern"]: _as_int(item.get("count")) for item in patterns}
    for issue in (validator_result or {}).get("issues") or (validator_result or {}).get("failures") or []:
        key = issue.get("code") or issue.get("check_id") or issue.get("type")
        if key:
            counts[str(key)] = counts.get(str(key), 0) + 1
    return [
        {
            "pattern": pattern,
            "count": count,
            "business_description": _failure_business_sentence(pattern),
        }
        for pattern, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
        if count > 0
    ]


def _collect_user_feedback(agent_review_feedback: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not agent_review_feedback:
        return []
    raw_items = agent_review_feedback.get("normalized_feedback")
    if raw_items is None:
        raw_items = agent_review_feedback.get("feedback") or agent_review_feedback.get("items") or []
    if isinstance(raw_items, str):
        raw_items = [{"summary": raw_items}]
    counts: dict[str, dict[str, Any]] = {}
    for item in raw_items if isinstance(raw_items, list) else []:
        text = str(item.get("summary") or item.get("raw_feedback") or item.get("text") or item.get("dimension") or "").strip()
        if not text:
            continue
        key = str(item.get("dimension") or text)
        bucket = counts.setdefault(
            key,
            {"feedback": text, "dimension": item.get("dimension") or "unknown", "severity": item.get("severity") or "medium", "count": 0},
        )
        bucket["count"] += _as_int(item.get("count") or 1)
        if item.get("severity") == "high":
            bucket["severity"] = "high"
    return sorted(counts.values(), key=lambda item: (-item["count"], str(item["dimension"])))


def _build_candidate_signals(
    *,
    edit_fields: list[dict[str, Any]],
    failure_patterns: list[dict[str, Any]],
    feedback_items: list[dict[str, Any]],
    behavior_packet: dict[str, Any],
    truth_gold_regression: dict[str, Any] | None,
    material_quality_regression: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in edit_fields:
        field = str(item.get("field") or "unknown")
        candidates.append(_candidate_signal("edit", field, _as_int(item.get("count")), item.get("business_description") or "", [item]))
    for item in failure_patterns:
        pattern = str(item.get("pattern") or "unknown")
        candidates.append(_candidate_signal("failure", pattern, _as_int(item.get("count")), item.get("business_description") or "", [item]))
    for item in feedback_items:
        text = str(item.get("feedback") or item.get("dimension") or "用户反馈")
        candidates.append(_candidate_signal("feedback", text, _as_int(item.get("count")), _feedback_business_sentence(text), [item], severity=item.get("severity")))
    for hint in behavior_packet.get("candidate_patch_hints") or []:
        key = str(hint.get("dimension") or hint.get("target") or hint.get("patch_id") or "candidate_patch")
        candidates.append(_candidate_signal("patch_hint", key, 2, str(hint.get("summary") or hint.get("rationale") or "行为蒸馏包给出的候选补丁提示。"), [hint]))
    merged = _merge_candidates(candidates)
    has_regression = bool(truth_gold_regression or material_quality_regression)
    for item in merged:
        count = _as_int(item.get("support_count"))
        target_layer = str(item.get("target_layer") or "unknown")
        risk = item.get("risk_level")
        item["support_level"] = "high" if count >= 3 else ("medium" if count == 2 else "low")
        if count <= 1:
            item["recommended_status"] = "single_case_only"
            item["reason"] = "这个反馈或修改目前只是单例，可能是人工偏好，不建议进入题卡配置。"
        elif target_layer == "unknown":
            item["recommended_status"] = "observe_more"
            item["reason"] = "出现过多次，但还不能明确映射到安全的正式层级，建议继续观察。"
        elif risk == "high":
            item["recommended_status"] = "observe_more"
            item["reason"] = "信号可能影响旧题型或答案稳定性，需要人审和回归后再判断。"
        elif has_regression:
            item["recommended_status"] = "suitable_for_formalization_packet"
            item["reason"] = "信号多次出现，且已有回归类证据，可作为 formalization packet 的候选 evidence。"
        else:
            item["recommended_status"] = "observe_more"
            item["reason"] = "信号多次出现，但缺少 truth_gold/material regression 支撑，不能直接写回。"
    return merged


def _candidate_signal(kind: str, key: str, count: int, description: str, evidence: list[dict[str, Any]], severity: str | None = None) -> dict[str, Any]:
    layer, risk = _infer_target_layer_and_risk(key, severity)
    signal_id = _slug(f"{kind}_{key}")[:80]
    return {
        "signal_id": signal_id,
        "business_description": description or _field_business_sentence(key),
        "technical_hint": f"{kind}:{key}",
        "target_layer": layer,
        "evidence": evidence,
        "support_count": count,
        "support_level": "low",
        "risk_level": risk,
        "recommended_status": "observe_more",
        "reason": "",
        "requires_regression": True,
        "requires_human_confirmation": True,
    }


def _merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in candidates:
        key = item["signal_id"]
        if key not in merged:
            merged[key] = item
            continue
        merged[key]["support_count"] = _as_int(merged[key].get("support_count")) + _as_int(item.get("support_count"))
        merged[key]["evidence"].extend(item.get("evidence") or [])
        if merged[key].get("risk_level") != "high" and item.get("risk_level") == "high":
            merged[key]["risk_level"] = "high"
    return list(merged.values())


def _business_overview(aggregate: dict[str, Any], source: dict[str, Any], candidates: list[dict[str, Any]], blocking_issues: list[str]) -> dict[str, Any]:
    direct = _rate(aggregate.get("direct_pass_count"), source.get("review_count")) or aggregate.get("direct_pass_rate")
    rejected = _rate(aggregate.get("rejected_count"), source.get("review_count")) or aggregate.get("rejected_rate")
    modified = _rate(source.get("patch_count"), source.get("review_count")) or aggregate.get("modified_then_kept_rate")
    if blocking_issues:
        quality = "blocked"
    elif rejected and rejected >= 0.3:
        quality = "needs_attention"
    elif modified and modified >= 0.5:
        quality = "needs_attention"
    elif source.get("review_count"):
        quality = "stable"
    else:
        quality = "unknown"
    dominant = "unknown"
    rates = {"direct_pass": direct or 0, "modified_then_kept": modified or 0, "rejected": rejected or 0}
    if source.get("review_count"):
        dominant = max(rates.items(), key=lambda pair: pair[1])[0]
    if any(item.get("risk_level") == "high" for item in candidates):
        quality = "needs_attention" if quality == "stable" else quality
    return {
        "direct_pass_rate": direct,
        "modified_then_kept_rate": modified,
        "rejected_rate": rejected,
        "dominant_review_pattern": dominant,
        "overall_quality_signal": quality,
    }


def _recommended_next_action(source: dict[str, Any], candidates: list[dict[str, Any]], blocking_issues: list[str]) -> str:
    if blocking_issues:
        return "blocked"
    if _as_int(source.get("sample_count")) < 3 or _as_int(source.get("review_count")) < 3:
        return "collect_more_samples"
    if any(item.get("risk_level") == "high" for item in candidates):
        return "human_review"
    if any(item.get("recommended_status") == "suitable_for_formalization_packet" for item in candidates):
        return "formalization_packet"
    if candidates:
        return "observe_more"
    return "human_review"


def _field_business_sentence(field: str | None) -> str:
    text = str(field or "").lower()
    if "distractor" in text or "option" in text or "干扰" in text:
        return "用户经常修改干扰项或解释，说明错项迷惑性可能不足。"
    if "material" in text or "passage" in text or "source" in text or "材料" in text:
        return "多次修改材料片段，说明材料筛选或切片规则需要继续验证。"
    if "analysis" in text or "rationale" in text or "解析" in text:
        return "解析被反复修改，说明解释链路或答案依据可能不够稳定。"
    if "stem" in text or "question" in text or "题干" in text:
        return "题干被反复调整，说明题目表达或任务边界可能不够清楚。"
    if "answer" in text or "gold" in text or "答案" in text:
        return "答案相关字段被修改，属于高风险信号，需要人审和回归。"
    return "该字段出现重复修改，但还需要人工确认它是否代表结构性规律。"


def _failure_business_sentence(pattern: str | None) -> str:
    text = str(pattern or "").lower()
    if "abstract" in text or "center" in text or "主旨" in text:
        return "多次驳回过度抽象主旨项，说明抽象层级约束可能需要进入 validator_contract。"
    if "distractor" in text or "option" in text:
        return "干扰项相关失败反复出现，可能指向错项机制不足。"
    if "material" in text or "source" in text:
        return "材料相关失败反复出现，需要继续验证材料筛选和切片规则。"
    return "该失败模式重复出现，建议继续观察并结合 validator/regression 证据判断。"


def _feedback_business_sentence(text: str) -> str:
    lower = text.lower()
    if "干扰" in text or "distractor" in lower:
        return "用户反复指出干扰项不够迷惑，可能指向错项机制不足。"
    if "不像真题" in text or "真题" in text:
        return "用户多次指出题目不像真题，说明题面风格或考查机制需要更多样本验证。"
    if "材料" in text:
        return "用户反馈集中在材料，说明材料筛选、切片或证据对齐还不稳定。"
    return f"用户反馈集中在“{text}”，需要判断它是结构性问题还是单次偏好。"


def _infer_target_layer_and_risk(key: str, severity: str | None = None) -> tuple[str, str]:
    text = key.lower()
    if "answer" in text or "gold" in text or "答案" in key:
        return "validator_contract", "high"
    if "material" in text or "passage" in text or "source" in text or "材料" in key:
        return "material_mapping", "medium" if severity != "high" else "high"
    if "distractor" in text or "option" in text or "干扰" in key:
        return "validator_contract", "medium"
    if "abstract" in text or "center" in text or "主旨" in key:
        return "validator_contract", "medium"
    if "review" in text or "审核" in key:
        return "review_process", "low"
    if "stem" in text or "question" in text or "题干" in key or "不像真题" in key:
        return "question_card", "medium"
    return "unknown", "medium" if severity == "high" else "low"


def _human_overview_sentence(summary: dict[str, Any]) -> str:
    edits = summary.get("high_frequency_edit_fields") or []
    feedback = summary.get("high_frequency_user_feedback") or []
    if edits and feedback:
        return (
            f"系统观察到：用户多次修改 `{edits[0].get('field')}`，并反复反馈“{feedback[0].get('feedback')}”。"
            "这个信号可以作为 formalization packet 的候选证据，但不能直接写回。"
        )
    if edits:
        return f"系统观察到：用户多次修改 `{edits[0].get('field')}`。当前应先作为 evidence 观察，不应自动改题卡。"
    return "当前修改样本不足，不能沉淀为正式规则，只建议继续观察。"


def _missing_inputs(**inputs: Any) -> list[str]:
    labels = {
        "behavior_packet": "behavior_packet",
        "run_detail": "run_detail",
        "agent_review_feedback": "agent_review_feedback",
        "validator_result": "validator_result",
        "truth_gold_regression": "truth_gold_regression_results",
        "material_quality_regression": "material_quality_regression_results",
    }
    return [labels[key] for key, value in inputs.items() if not value]


def _normalize_count_items(raw: Any, key_name: str) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        return [{key_name: key, "count": value} for key, value in raw.items()]
    items: list[dict[str, Any]] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            items.append({key_name: str(item), "count": 1})
            continue
        key = item.get(key_name) or item.get("key") or item.get("field") or item.get("name") or item.get("threshold") or item.get("pattern")
        if key:
            items.append({key_name: str(key), "count": _as_int(item.get("count") or item.get("value") or 1)})
    return items


def _rate(numerator: Any, denominator: Any) -> float | None:
    den = _as_int(denominator)
    if den <= 0 or numerator is None:
        return None
    return round(_as_int(numerator) / den, 4)


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def _has_conflict(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    text = json.dumps(payload, ensure_ascii=False).lower()
    return "conflict" in text or '"status": "blocked"' in text


def _load_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_business_summary_boundaries(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False).lower()
    for token in ['"formalized": true', '"writeback_allowed": true', '"executor_allowed": true']:
        if token in text:
            raise ValueError(f"behavior distillation business summary violates boundary: {token}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build behavior distillation business summary artifacts.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--behavior-packet")
    parser.add_argument("--run-detail")
    parser.add_argument("--agent-review-feedback")
    parser.add_argument("--validator-result")
    parser.add_argument("--truth-gold-regression-results")
    parser.add_argument("--material-quality-regression-results")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    artifacts = run_behavior_distillation_business_summary(
        output_dir=args.output_dir,
        behavior_packet_path=args.behavior_packet,
        run_detail_path=args.run_detail,
        agent_review_feedback_path=args.agent_review_feedback,
        validator_result_path=args.validator_result,
        truth_gold_regression_results_path=args.truth_gold_regression_results,
        material_quality_regression_results_path=args.material_quality_regression_results,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

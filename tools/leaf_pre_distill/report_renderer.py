from __future__ import annotations

from typing import Any


def render_markdown_report(
    *,
    manifest: dict[str, Any],
    candidate_report: dict[str, Any],
    slot_projection: dict[str, Any],
    llm_probe: dict[str, Any] | None = None,
    bootstrap_discovery: dict[str, Any] | None = None,
    axis_confirmation: dict[str, Any] | None = None,
    formal_patch_draft: dict[str, Any] | None = None,
    formal_writeback_plan: dict[str, Any] | None = None,
    gold_reconstruction: dict[str, Any] | None = None,
    truth_gold_regression: dict[str, Any] | None = None,
    source_discovery_preparation: dict[str, Any] | None = None,
    source_candidate_search: dict[str, Any] | None = None,
    source_candidate_review: dict[str, Any] | None = None,
    source_text_evidence: dict[str, Any] | None = None,
    source_gold_alignment: dict[str, Any] | None = None,
    material_quality_regression: dict[str, Any] | None = None,
    material_protocol_draft: dict[str, Any] | None = None,
    agent_review_feedback: dict[str, Any] | None = None,
    behavior_distillation_business_summary: dict[str, Any] | None = None,
    behavior_distillation_business_view: dict[str, Any] | None = None,
    new_leaf_formalization_packet: dict[str, Any] | None = None,
    runtime_activation_plan: dict[str, Any] | None = None,
    formalization_readiness_gate: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"# 叶族预蒸馏报告：{manifest['leaf_label']}")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- job_id: `{manifest['job_id']}`")
    lines.append(f"- mother_family_id: `{manifest['mother_family_id']}`")
    if manifest.get("child_family_id"):
        lines.append(f"- child_family_id: `{manifest['child_family_id']}`")
    lines.append(f"- sample_count: `{candidate_report['sample_count']}`")
    lines.append(f"- clean_leaf_boundary: `{manifest.get('clean_leaf_boundary')}`")
    lines.append("")

    lines.append("## 字段候选")
    lines.append("")
    lines.append("| field | value | layer | support | confidence | evidence |")
    lines.append("|---|---|---|---:|---|---|")
    for candidate in candidate_report.get("field_candidates") or []:
        evidence = ", ".join(candidate.get("evidence_examples") or [])
        lines.append(
            "| `{field}` | `{value}` | `{layer}` | {support:.1%} | {confidence} | {evidence} |".format(
                field=candidate["field_path"],
                value=candidate["proposed_value"],
                layer=candidate["target_layer"],
                support=float(candidate["support_rate"]),
                confidence=candidate["confidence"],
                evidence=evidence,
            )
        )
    lines.append("")

    lines.append("## 推荐落位")
    lines.append("")
    lines.append("```yaml")
    lines.extend(_yamlish(slot_projection).splitlines())
    lines.append("```")
    lines.append("")

    if candidate_report.get("schema_gaps"):
        lines.append("## Schema Gap")
        lines.append("")
        for gap in candidate_report["schema_gaps"]:
            lines.append(f"- `{gap['field']}`: {gap['reason']}；建议：{gap['suggested_resolution']}")
        lines.append("")

    lines.append("## 消融问题")
    lines.append("")
    for candidate in candidate_report.get("field_candidates") or []:
        if candidate.get("confidence") == "low":
            continue
        lines.append(f"- {candidate['ablation_question']}")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    high = candidate_report.get("summary", {}).get("high_confidence_count", 0)
    medium = candidate_report.get("summary", {}).get("medium_confidence_count", 0)
    lines.append(f"本轮产出高置信字段 `{high}` 个，中置信字段 `{medium}` 个。建议先作为候选报告进入蒸馏台 review，不直接写回正式题卡。")
    if bootstrap_discovery is not None:
        _append_bootstrap_discovery_section(lines, bootstrap_discovery)
    if axis_confirmation is not None:
        _append_axis_confirmation_section(lines, axis_confirmation)
    if formal_patch_draft is not None:
        _append_formal_patch_draft_section(lines, formal_patch_draft)
    if formal_writeback_plan is not None:
        _append_formal_writeback_plan_section(lines, formal_writeback_plan)
    if gold_reconstruction is not None:
        _append_gold_reconstruction_section(lines, gold_reconstruction)
    if truth_gold_regression is not None:
        _append_truth_gold_regression_section(lines, truth_gold_regression)
    if source_discovery_preparation is not None:
        _append_source_discovery_preparation_section(lines, source_discovery_preparation)
    if source_candidate_search is not None:
        _append_source_candidate_search_section(lines, source_candidate_search)
    if source_candidate_review is not None:
        _append_source_candidate_review_section(lines, source_candidate_review)
    if source_text_evidence is not None:
        _append_source_text_evidence_section(lines, source_text_evidence)
    if source_gold_alignment is not None:
        _append_source_gold_alignment_section(lines, source_gold_alignment)
    if material_quality_regression is not None:
        _append_material_quality_regression_section(lines, material_quality_regression)
    if material_protocol_draft is not None:
        _append_material_protocol_draft_section(lines, material_protocol_draft)
    if agent_review_feedback is not None:
        _append_agent_review_feedback_section(lines, agent_review_feedback)
    if behavior_distillation_business_summary is not None:
        _append_behavior_distillation_business_summary_section(lines, behavior_distillation_business_summary)
    if behavior_distillation_business_view is not None:
        _append_behavior_distillation_business_view_section(lines, behavior_distillation_business_view)
    if new_leaf_formalization_packet is not None:
        _append_new_leaf_formalization_packet_section(lines, new_leaf_formalization_packet)
    if runtime_activation_plan is not None:
        _append_runtime_activation_plan_section(lines, runtime_activation_plan)
    if formalization_readiness_gate is not None:
        _append_formalization_readiness_gate_section(lines, formalization_readiness_gate)
    if llm_probe is not None:
        _append_llm_probe_section(lines, llm_probe)
    return "\n".join(lines) + "\n"


def _append_source_text_evidence_section(lines: list[str], manifest: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Source Text Evidence")
    lines.append("")
    lines.append("> Source text evidence is reviewable material-line evidence. It does not verify original source, ingest passage_service, write material_card, or write card_specs.")
    lines.append("")
    lines.append(f"- status: `{manifest.get('status')}`")
    lines.append(f"- count: `{manifest.get('result_count')}`")
    lines.append(f"- blocked_count: `{manifest.get('blocked_count')}`")
    lines.append(f"- human_review_required: `{bool(manifest.get('requires_human_review'))}`")
    lines.append(f"- verified_original_source_count: `{manifest.get('verified_original_source_count', 0)}`")
    lines.append(f"- readiness_conclusion: `ready_for_source_gold_alignment={bool(manifest.get('ready_for_source_gold_alignment'))}`")
    lines.append("- next_action: `source_gold_alignment_or_manual_text_review`")


def _append_source_gold_alignment_section(lines: list[str], summary: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Source/Gold Alignment")
    lines.append("")
    lines.append("> Source/gold alignment compares source text evidence with reconstructed gold. It is not source verification and cannot approve material_card writeback.")
    lines.append("")
    lines.append(f"- status: `{summary.get('status')}`")
    lines.append(f"- count: `{summary.get('alignment_count')}`")
    lines.append(f"- blocked_count: `{summary.get('blocked_count')}`")
    lines.append(f"- human_review_required: `{bool(summary.get('needs_human_review_count'))}`")
    lines.append(f"- verified_original_source_count: `{summary.get('verified_original_source_count', 0)}`")
    lines.append(f"- readiness_conclusion: `ready_for_material_quality_regression={bool(summary.get('ready_for_material_quality_regression'))}`")
    lines.append("- next_action: `human_alignment_review_or_material_quality_regression`")


def _append_material_quality_regression_section(lines: list[str], results: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Material Quality Regression")
    lines.append("")
    lines.append("> Material quality regression is readiness evidence, not formal material_card approval. High scores cannot auto-approve writeback.")
    lines.append("")
    lines.append(f"- status: `{results.get('status')}`")
    lines.append(f"- count: `{len(results.get('dimensions') or [])}`")
    lines.append(f"- blocked_count: `{len(results.get('blocking_issues') or [])}`")
    lines.append(f"- human_review_required: `{bool(results.get('requires_human_review'))}`")
    lines.append(f"- verified_original_source_count: `{results.get('verified_original_source_count', 0)}`")
    lines.append(f"- readiness_conclusion: `ready_for_material_card_formalization={bool(results.get('ready_for_material_card_formalization'))}`")
    lines.append(f"- next_action: `{results.get('recommended_next_action')}`")


def _append_agent_review_feedback_section(lines: list[str], feedback: dict[str, Any]) -> None:
    items = feedback.get("normalized_feedback") or []
    blocking = [item.get("dimension") for item in items if item.get("severity") == "high"]
    lines.append("")
    lines.append("## Agent Review Feedback")
    lines.append("")
    lines.append("> 用户反馈是 evidence，不直接改题卡、材料卡、prompt、validator、runtime，也不触发写回。")
    lines.append("")
    lines.append(f"- status: `{feedback.get('status')}`")
    lines.append(f"- feedback_count: `{len(items)}`")
    lines.append(f"- high_severity_count: `{len(blocking)}`")
    lines.append(f"- writeback_allowed: `{bool(feedback.get('writeback_allowed'))}`")
    lines.append(f"- formalized: `{bool(feedback.get('formalized'))}`")
    lines.append(f"- blocking_issues: `{blocking}`")
    lines.append("- recommended_next_action: `feed_into_formalization_packet`")


def _append_behavior_distillation_business_summary_section(lines: list[str], summary: dict[str, Any]) -> None:
    overview = summary.get("business_overview") or {}
    signals = summary.get("candidate_improvement_signals") or []
    suitable = [item for item in signals if item.get("recommended_status") == "suitable_for_formalization_packet"]
    lines.append("")
    lines.append("## Behavior Distillation Business Summary")
    lines.append("")
    lines.append("> 业务蒸馏结果是 evidence，不是正式配置；高频修改不等于自动改题卡，不会调用 executor。")
    lines.append("")
    lines.append(f"- status: `{summary.get('status')}`")
    lines.append(f"- overall_quality_signal: `{overview.get('overall_quality_signal')}`")
    lines.append(f"- candidate_signal_count: `{len(signals)}`")
    lines.append(f"- suitable_for_formalization_count: `{len(suitable)}`")
    lines.append(f"- recommended_next_action: `{summary.get('recommended_next_action')}`")
    lines.append(f"- writeback_allowed: `{bool(summary.get('writeback_allowed'))}`")
    lines.append(f"- executor_allowed: `{bool(summary.get('executor_allowed'))}`")


def _append_behavior_distillation_business_view_section(lines: list[str], view: dict[str, Any]) -> None:
    context = view.get("family_context") or {}
    landing = view.get("landing_status") or {}
    lines.append("")
    lines.append("## Behavior Distillation Business View")
    lines.append("")
    lines.append("> 业务视图只展示人话结论；JSON 技术细节应默认折叠。它不是正式配置、审批或写回。")
    lines.append("")
    lines.append(f"- stage: `{context.get('stage')}`")
    lines.append(f"- leaf_id: `{context.get('leaf_id')}`")
    lines.append(f"- problem_count: `{len(view.get('business_problem_summary') or [])}`")
    lines.append(f"- recommendation_count: `{len(view.get('distilled_recommendations') or [])}`")
    lines.append(f"- comparison_count: `{len(view.get('before_after_comparisons') or [])}`")
    lines.append(f"- landing_label: `{landing.get('landing_label')}`")
    lines.append(f"- writeback_allowed: `{bool(view.get('writeback_allowed'))}`")


def _append_new_leaf_formalization_packet_section(lines: list[str], packet: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## New Leaf Formalization Packet")
    lines.append("")
    lines.append("> 正式化送审包只汇总 evidence 和 draft，不执行写回。")
    lines.append("")
    lines.append(f"- status: `{packet.get('status')}`")
    lines.append(f"- family_context: `{packet.get('family_context')}`")
    lines.append(f"- target_candidate_count: `{len(packet.get('formal_target_candidates') or [])}`")
    lines.append(f"- blocking_issues: `{packet.get('blocking_issues') or []}`")
    lines.append(f"- recommended_next_action: `{packet.get('recommended_next_action')}`")
    lines.append(f"- writeback_allowed: `{bool(packet.get('writeback_allowed'))}`")


def _append_runtime_activation_plan_section(lines: list[str], plan: dict[str, Any]) -> None:
    proto = plan.get("proto_vs_formal") or {}
    lines.append("")
    lines.append("## Runtime Activation Plan")
    lines.append("")
    lines.append("> Runtime 接入计划是只读草案，不修改 input_decoder、generation、validator、prompt 或 runtime 配置。")
    lines.append("")
    lines.append(f"- status: `{plan.get('status')}`")
    lines.append(f"- family_context: `{plan.get('family_context')}`")
    lines.append(f"- can_run_proto_trial: `{bool(proto.get('can_run_proto_trial'))}`")
    lines.append(f"- can_run_formal_generation: `{bool(proto.get('can_run_formal_generation'))}`")
    lines.append(f"- activation_blockers: `{plan.get('activation_blockers') or []}`")
    lines.append(f"- writeback_allowed: `{bool(plan.get('writeback_allowed'))}`")


def _append_formalization_readiness_gate_section(lines: list[str], gate: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Formalization Readiness Gate")
    lines.append("")
    lines.append("> Readiness gate 只判断能否进入下一步，不自动 approve，不自动 executor，不写正式配置。")
    lines.append("")
    lines.append(f"- status: `{gate.get('status')}`")
    lines.append(f"- family_context: `{gate.get('family_context')}`")
    lines.append(f"- blocking_issues: `{gate.get('blocking_issues') or []}`")
    lines.append(f"- recommended_next_action: `{gate.get('recommended_next_action')}`")
    lines.append(f"- writeback_allowed: `{bool(gate.get('writeback_allowed'))}`")


def _append_material_protocol_draft_section(lines: list[str], digest: dict[str, Any]) -> None:
    family_context = digest.get("family_context") or {}
    gaps = digest.get("missing_evidence") or []
    lines.append("")
    lines.append("## Material Protocol Draft")
    lines.append("")
    lines.append("> Material protocol assets are draft-only evidence. They do not write material_card, card_specs, runtime mapping, prompt, validator, question_card, or material library.")
    lines.append("")
    lines.append(f"- family_context: `{family_context}`")
    lines.append(f"- system_alignment: `{bool(digest.get('system_alignment_findings_summary'))}`")
    lines.append("- material_card_draft_status: `draft_only when generated`")
    lines.append("- prompt_assets_draft_status: `draft_only when generated`")
    lines.append("- quality_regression_draft_status: `draft_only when generated`")
    lines.append("- bridge_mapping_draft_status: `draft_only when generated`")
    lines.append(f"- evidence_gaps_count: `{len(gaps)}`")
    next_required = [
        "crawl approval before body fetch",
        "source body fetch before source/gold alignment",
        "material quality regression before writeback plan",
    ]
    lines.append("")
    lines.append("### Next Required Evidence")
    lines.append("")
    for item in next_required:
        lines.append(f"- {item}")
    lines.append("")


def _append_source_candidate_review_section(lines: list[str], review: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Source Candidate Human Review")
    lines.append("")
    lines.append("> Human-reviewed source seeds are not verified sources. Crawl seed manifests are not crawl approval.")
    lines.append("> No material_card, material library, card_specs, prompt, validator, runtime, or promotion target has been changed.")
    lines.append("")
    lines.append(f"- accepted_count: `{review.get('accepted_count')}`")
    lines.append(f"- rejected_count: `{review.get('rejected_count')}`")
    lines.append(f"- deferred_count: `{review.get('deferred_count')}`")
    lines.append(f"- seed_count: `{review.get('seed_count')}`")
    lines.append(f"- risky_accepted_seed_count: `{review.get('risky_accepted_seed_count')}`")
    lines.append(f"- verified_original_source_count: `{review.get('verified_original_source_count')}`")
    lines.append("- crawl_allowed: `False`")
    lines.append("- ready_for_material_card_draft: `False`")
    warnings = review.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append("### Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")


def _append_source_candidate_search_section(lines: list[str], summary: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Source Candidate Search")
    lines.append("")
    lines.append("> Candidate sources are unverified. This is not source confirmation, not material_card generation, and not passage-service writeback.")
    lines.append("> No material library, card_specs, prompt, validator, runtime, or promotion target has been changed.")
    lines.append("")
    lines.append(f"- sample_count: `{summary.get('sample_count')}`")
    lines.append(f"- query_count: `{summary.get('query_count')}`")
    lines.append(f"- candidate_count: `{summary.get('candidate_count')}`")
    lines.append(f"- source_risk_counts: `{summary.get('source_risk_counts') or {}}`")
    lines.append(f"- ready_for_human_source_review: `{bool(summary.get('ready_for_human_source_review'))}`")
    lines.append(f"- ready_for_material_card_draft: `{bool(summary.get('ready_for_material_card_draft'))}`")
    blockers = summary.get("main_blockers") or []
    if blockers:
        lines.append("")
        lines.append("### Main Blockers")
        lines.append("")
        for blocker in blockers:
            lines.append(f"- {blocker}")
    lines.append("")


def _append_source_discovery_preparation_section(lines: list[str], profile: dict[str, Any]) -> None:
    conclusion = profile.get("material_line_conclusion") or {}
    lines.append("")
    lines.append("## Source Discovery Preparation")
    lines.append("")
    lines.append("> This is material-line preparation only. It is not card protocol landing, a formal material_card, or a web search executor.")
    lines.append("> No material library, card_specs, prompt, validator, runtime, or promotion target has been changed.")
    lines.append("")
    lines.append(f"- status: `{profile.get('status') or ''}`")
    lines.append(f"- gold_source: `{profile.get('gold_source') or ''}`")
    lines.append(f"- using_raw_sample_material: `{bool(profile.get('using_raw_sample_material'))}`")
    lines.append(f"- sample_count: `{profile.get('sample_count')}`")
    lines.append(f"- requires_source_article_count: `{profile.get('requires_source_article_count')}`")
    lines.append(f"- needs_human_review_count: `{profile.get('needs_human_review_count')}`")
    lines.append(f"- ready_for_source_discovery: `{bool(conclusion.get('ready_for_source_discovery'))}`")
    lines.append(f"- ready_for_material_card_draft: `{bool(conclusion.get('ready_for_material_card_draft'))}`")
    blockers = conclusion.get("main_blockers") or []
    if blockers:
        lines.append("")
        lines.append("### Main Blockers")
        lines.append("")
        for blocker in blockers:
            lines.append(f"- {blocker}")
    lines.append("")


def _append_bootstrap_discovery_section(lines: list[str], discovery: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Bootstrap Leaf Discovery")
    lines.append("")
    lines.append("> Candidate axes are hypotheses, not fields. No formal config has been changed.")
    lines.append("> bootstrap_discovery is an evidence attachment only, not a promotion target.")
    lines.append("")
    lines.append(f"- enabled: `{bool(discovery.get('enabled'))}`")
    lines.append(f"- known_family_matched: `{bool(discovery.get('known_family_matched'))}`")
    lines.append("- promotion_allowed: `False`")

    proto = discovery.get("proto_mother_family") or {}
    lines.append("")
    lines.append("### Proto Mother Family")
    lines.append("")
    lines.append(f"- label: `{proto.get('label') or ''}`")
    lines.append(f"- confidence: `{proto.get('confidence') or ''}`")
    lines.append(f"- status: `{proto.get('status') or ''}`")
    if proto.get("description"):
        lines.append(f"- description: {proto['description']}")
    lines.append("")

    lines.append("### Candidate Axes")
    lines.append("")
    axes = discovery.get("candidate_axes") or []
    if axes:
        lines.append("| axis | values | support | status | risk |")
        lines.append("|---|---|---|---|---|")
        for axis in axes:
            values = ", ".join(axis.get("values") or [])
            lines.append(
                "| `{axis}` | {values} | {support} | {status} | {risk} |".format(
                    axis=axis.get("axis") or "",
                    values=values,
                    support=axis.get("support_estimate") or "",
                    status=axis.get("status") or "",
                    risk=axis.get("risk") or "",
                )
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Distractor Taxonomy")
    lines.append("")
    taxonomy = discovery.get("distractor_taxonomy") or []
    if taxonomy:
        lines.append("| mode | status | description |")
        lines.append("|---|---|---|")
        for item in taxonomy:
            lines.append(
                "| `{mode}` | {status} | {description} |".format(
                    mode=item.get("mode") or "",
                    status=item.get("status") or "",
                    description=item.get("description") or "",
                )
            )
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Schema Gap Hypotheses")
    lines.append("")
    gaps = discovery.get("schema_gap_hypotheses") or []
    if gaps:
        for gap in gaps:
            lines.append(f"- `{gap.get('gap') or ''}`: {gap.get('reason') or ''} ({gap.get('status') or ''})")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Next Human Questions")
    lines.append("")
    questions = discovery.get("next_human_questions") or []
    if questions:
        for question in questions:
            lines.append(f"- {question}")
    else:
        lines.append("- None")
    lines.append("")


def _append_llm_probe_section(lines: list[str], llm_probe: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## LLM Field Probe")
    lines.append("")
    lines.append("> This probe is auxiliary evidence only. It is not a promotion decision and cannot update formal config.")
    lines.append("")
    lines.append(f"- enabled: `{bool(llm_probe.get('enabled'))}`")
    lines.append(f"- usable: `{bool(llm_probe.get('usable'))}`")
    lines.append(f"- model: `{llm_probe.get('model') or ''}`")
    lines.append("- should_promote: `False`")
    if llm_probe.get("leaf_signature"):
        lines.append(f"- leaf_signature: {llm_probe['leaf_signature']}")
    lines.append("")

    confirmed = llm_probe.get("confirmed_fields") or {}
    lines.append("### Confirmed Fields")
    lines.append("")
    if confirmed:
        for field_path, proposed_value in confirmed.items():
            lines.append(f"- `{field_path}`: `{proposed_value}`")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Field Risks")
    lines.append("")
    risks = llm_probe.get("field_risks") or []
    if risks:
        for risk in risks:
            field_path = risk.get("field_path") or "general"
            lines.append(f"- `{field_path}`: {risk.get('risk') or ''}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("### Schema Gap Comments")
    lines.append("")
    comments = llm_probe.get("schema_gap_comments") or []
    if comments:
        for comment in comments:
            lines.append(f"- `{comment.get('field') or ''}`: {comment.get('comment') or ''}")
    else:
        lines.append("- None")
    lines.append("")

    warnings = llm_probe.get("warnings") or []
    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

def _append_axis_confirmation_section(lines: list[str], confirmation: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Axis Confirmation")
    lines.append("")
    lines.append("> Proto-confirmed decisions are not formal fields. No formal config has been changed.")
    lines.append("> axis_confirmation is an evidence attachment only, not a promotion target.")
    lines.append("")
    lines.append(f"- enabled: `{bool(confirmation.get('enabled'))}`")
    lines.append(f"- status: `{confirmation.get('status') or ''}`")
    lines.append("- formalized: `False`")
    lines.append("- promotion_allowed: `False`")
    proto = confirmation.get("proto_mother_family") or {}
    lines.append(f"- proto_mother_family: `{proto.get('label') or ''}` ({proto.get('status') or ''})")
    lines.append("")

    decisions = confirmation.get("axis_decisions") or []
    lines.append("### Proto-Confirmed Decisions")
    lines.append("")
    if decisions:
        lines.append("| source | decision | confirmed_name | target_layer | status |")
        lines.append("|---|---|---|---|---|")
        for decision in decisions:
            source = f"{decision.get('source_type') or ''}:{decision.get('source_id') or ''}"
            lines.append(
                "| `{source}` | {decision} | `{name}` | `{target}` | {status} |".format(
                    source=source,
                    decision=decision.get("decision") or "",
                    name=decision.get("confirmed_name") or "",
                    target=decision.get("target_layer") or "",
                    status=decision.get("status") or "",
                )
            )
    else:
        lines.append("- None")
    lines.append("")

    rejected = confirmation.get("rejected_or_deferred") or []
    if rejected:
        lines.append("### Rejected Or Deferred")
        lines.append("")
        for item in rejected:
            source = f"{item.get('source_type') or ''}:{item.get('source_id') or ''}"
            lines.append(f"- `{source}`: {item.get('decision') or ''} ({item.get('status') or ''})")
        lines.append("")

    warnings = confirmation.get("warnings") or []
    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")


def _append_formal_patch_draft_section(lines: list[str], draft: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Formal Patch Draft")
    lines.append("")
    lines.append("> This is a draft-only artifact. It does not write back to card_specs or formal runtime config.")
    lines.append("> formal_patch_draft is an evidence attachment only unless a human creates explicit canonical target patches.")
    lines.append("")
    lines.append(f"- enabled: `{bool(draft.get('enabled'))}`")
    lines.append(f"- status: `{draft.get('status') or ''}`")
    lines.append("- writeback_allowed: `False`")
    lines.append("- formalized: `False`")
    lines.append("- promotion_allowed: `False`")
    lines.append(f"- proto_family: `{draft.get('proto_family') or ''}`")
    lines.append(f"- proto_child_family: `{draft.get('proto_child_family') or ''}`")
    lines.append("")

    patches = draft.get("target_patches") or []
    lines.append("### Target Patch Drafts")
    lines.append("")
    if patches:
        lines.append("| target | scope_key | draft_status | decisions |")
        lines.append("|---|---|---|---:|")
        for patch in patches:
            decisions = ((patch.get("patch") or {}).get("proto_confirmed_decisions") or [])
            lines.append(
                "| `{target}` | `{scope}` | {status} | {count} |".format(
                    target=patch.get("target") or "",
                    scope=patch.get("scope_key") or "",
                    status=patch.get("draft_status") or "",
                    count=len(decisions),
                )
            )
    else:
        lines.append("- None")
    lines.append("")

    warnings = draft.get("warnings") or []
    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")


def _append_formal_writeback_plan_section(lines: list[str], plan: dict[str, Any]) -> None:
    lines.append("")
    lines.append("## Formal Writeback Plan")
    lines.append("")
    lines.append("> Preview only. This plan does not write card_specs, prompt assets, validator rules, or runtime mappings.")
    lines.append("")
    lines.append(f"- status: `{plan.get('status') or ''}`")
    lines.append("- writeback_allowed: `False`")
    lines.append(f"- requires_explicit_approval: `{bool(plan.get('requires_explicit_approval'))}`")
    lines.append(f"- proto_family: `{plan.get('proto_family') or ''}`")
    lines.append(f"- proto_child_family: `{plan.get('proto_child_family') or ''}`")
    lines.append("")
    lines.append("### Planned Files")
    lines.append("")
    items = plan.get("writeback_items") or []
    if items:
        lines.append("| target | file | operation |")
        lines.append("|---|---|---|")
        for item in items:
            lines.append(
                "| `{target}` | `{file}` | {operation} |".format(
                    target=item.get("target") or "",
                    file=item.get("target_file") or "",
                    operation=item.get("operation") or "",
                )
            )
    else:
        lines.append("- None")
    lines.append("")
    impact = plan.get("legacy_family_impact") or {}
    lines.append("### Legacy Family Impact")
    lines.append("")
    lines.append(f"- sentence_fill: `{impact.get('sentence_fill') or ''}`")
    lines.append(f"- sentence_order: `{impact.get('sentence_order') or ''}`")
    lines.append(f"- center_understanding: `{impact.get('center_understanding') or ''}`")
    lines.append(f"- shared_config_touch: `{impact.get('shared_config_touch')}`")
    lines.append("")


def _append_truth_gold_regression_section(lines: list[str], results: dict[str, Any]) -> None:
    summary = results.get("summary") or {}
    lines.append("")
    lines.append("## Truth Gold Regression")
    lines.append("")
    lines.append("> Quality regression evidence only. This is not formal writeback approval.")
    lines.append("> High fit does not imply true-question quality; it can indicate source overfit.")
    lines.append("")
    lines.append(f"- mode: `{results.get('mode') or ''}`")
    lines.append(f"- gold_sample_count: `{results.get('gold_sample_count')}`")
    lines.append(f"- generated_item_count: `{results.get('generated_item_count')}`")
    lines.append(f"- fit_type: `{summary.get('fit_type') or ''}`")
    lines.append(f"- ready_for_user_sample_review: `{summary.get('ready_for_user_sample_review')}`")
    lines.append(f"- ready_for_formalization: `{summary.get('ready_for_formalization')}`")
    lines.append("")


def _append_gold_reconstruction_section(lines: list[str], summary: dict[str, Any]) -> None:
    artifacts = summary.get("artifacts") or {}
    lines.append("")
    lines.append("## Gold Reconstruction")
    lines.append("")
    lines.append("> Model-based gold schema reconstruction evidence only. This is not protocol field discovery or formal config.")
    lines.append("")
    lines.append(f"- mode: `{summary.get('mode') or ''}`")
    lines.append(f"- model: `{summary.get('model') or ''}`")
    lines.append(f"- input_count: `{summary.get('input_count')}`")
    lines.append(f"- result_count: `{summary.get('result_count')}`")
    lines.append(f"- model_safe_input: `{artifacts.get('model_safe_gold_reconstruction_input') or ''}`")
    if artifacts.get("gold_reconstruction_results"):
        lines.append(f"- results: `{artifacts.get('gold_reconstruction_results')}`")
    if artifacts.get("gold_reconstruction_report"):
        lines.append(f"- report: `{artifacts.get('gold_reconstruction_report')}`")
    lines.append("")


def _yamlish(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(_yamlish(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {item!r}" if isinstance(item, str) else f"{pad}{key}: {item}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(_yamlish(item, indent + 2))
            else:
                lines.append(f"{pad}- {item}")
        return "\n".join(lines)
    return f"{pad}{value}"

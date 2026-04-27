from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MarkerRule:
    action: str
    markers: tuple[str, ...]
    field_path: str
    proposed_value: str
    target_layer: str
    uniqueness_source: tuple[str, ...] = ()
    distractor_modes: tuple[str, ...] = ()


RULES: dict[str, tuple[MarkerRule, ...]] = {
    "sentence_order": (
        MarkerRule(
            action="detect_opening_anchor",
            markers=("背景引入", "背景铺垫", "引出话题", "宏观话题", "社会热词", "人们常说"),
            field_path="opening_anchor_type",
            proposed_value="background_intro",
            target_layer="canonical_slot",
            uniqueness_source=("role_order_conflict", "reference_dependency"),
            distractor_modes=("wrong_opening", "block_swap"),
        ),
        MarkerRule(
            action="detect_binding_pair",
            markers=("关联词", "不仅", "更要", "递进", "捆绑", "紧密相连", "构成递进", "关联词-其他"),
            field_path="local_binding_strength",
            proposed_value="high",
            target_layer="canonical_slot",
            uniqueness_source=("binding_violation", "reference_dependency"),
            distractor_modes=("local_binding_break", "connector_mislead"),
        ),
        MarkerRule(
            action="detect_timeline_progression",
            markers=("时间顺序", "时间脉络", "先后", "之后", "此前", "以来", "古代", "近代", "现代", "首先", "其次"),
            field_path="ordering_logic",
            proposed_value="timeline_progression",
            target_layer="material_card_overlay",
            uniqueness_source=("role_order_conflict", "binding_violation"),
            distractor_modes=("block_swap", "local_adjacency_break"),
        ),
        MarkerRule(
            action="detect_closure_position",
            markers=("确定尾句", "尾句", "适合做尾句", "做尾句", "总结", "结论"),
            field_path="closing_anchor_type",
            proposed_value="conclusion",
            target_layer="canonical_slot",
            uniqueness_source=("closure_position", "reference_dependency"),
            distractor_modes=("wrong_closing", "summary_misplace", "block_swap"),
        ),
    ),
    "sentence_fill": (
        MarkerRule(
            action="detect_blank_position_opening",
            markers=("横线在开头", "开头", "概括后文", "总起", "引出话题"),
            field_path="blank_position",
            proposed_value="opening",
            target_layer="canonical_slot",
            uniqueness_source=("function_mismatch", "scope_mismatch"),
            distractor_modes=("function_mismatch", "wrong_direction"),
        ),
        MarkerRule(
            action="detect_blank_position_middle",
            markers=("横线在中间", "中间", "承上启下", "承上", "启下", "衔接"),
            field_path="blank_position",
            proposed_value="middle",
            target_layer="canonical_slot",
            uniqueness_source=("function_mismatch", "reference_failure"),
            distractor_modes=("weak_forward_link", "weak_backward_link", "wrong_direction"),
        ),
        MarkerRule(
            action="detect_blank_position_ending",
            markers=("横线在结尾", "结尾", "总结前文", "结论", "收束"),
            field_path="blank_position",
            proposed_value="ending",
            target_layer="canonical_slot",
            uniqueness_source=("function_mismatch", "scope_mismatch"),
            distractor_modes=("overgeneralization", "undergeneralization"),
        ),
        MarkerRule(
            action="detect_bidirectional_bridge",
            markers=("承上启下", "前后", "双向", "衔接", "照应"),
            field_path="bidirectional_validation",
            proposed_value="high",
            target_layer="canonical_slot",
            uniqueness_source=("reference_failure", "function_mismatch"),
            distractor_modes=("weak_forward_link", "weak_backward_link"),
        ),
    ),
    "center_understanding": (
        MarkerRule(
            action="detect_turning_relation",
            markers=("转折", "然而", "但是", "但", "不过", "实际上"),
            field_path="relation_type",
            proposed_value="turning",
            target_layer="business_feature_projection",
            uniqueness_source=("relation_focus",),
            distractor_modes=("scope_shift", "partial_reading"),
        ),
        MarkerRule(
            action="detect_parallel_relation",
            markers=("并列", "同时", "此外", "另一方面", "一方面"),
            field_path="relation_type",
            proposed_value="parallel",
            target_layer="business_feature_projection",
            uniqueness_source=("relation_focus",),
            distractor_modes=("single_dimension_only", "partial_reading"),
        ),
        MarkerRule(
            action="detect_countermeasure_relation",
            markers=("对策", "措施", "应该", "需要", "必须", "通过"),
            field_path="relation_type",
            proposed_value="countermeasure",
            target_layer="business_feature_projection",
            uniqueness_source=("task_landing",),
            distractor_modes=("unsupported_extension", "scope_shift"),
        ),
    ),
}


def build_behavior_trace(sample: dict[str, Any], *, mother_family_id: str) -> dict[str, Any]:
    text = "\n".join(
        str(sample.get(key) or "")
        for key in ("leaf_label", "stem", "analysis", "exam_points", "raw_text")
    )
    observed_actions = []
    uniqueness_sources: list[str] = []
    distractor_modes: list[str] = []
    for rule in RULES.get(mother_family_id, ()):
        evidence = [marker for marker in rule.markers if marker in text]
        if not evidence:
            continue
        observed_actions.append(
            {
                "action": rule.action,
                "field_path": rule.field_path,
                "proposed_value": rule.proposed_value,
                "target_layer": rule.target_layer,
                "evidence": evidence,
                "evidence_count": sum(text.count(marker) for marker in rule.markers),
            }
        )
        uniqueness_sources.extend(item for item in rule.uniqueness_source if item not in uniqueness_sources)
        distractor_modes.extend(item for item in rule.distractor_modes if item not in distractor_modes)

    return {
        "sample_id": sample["sample_id"],
        "qid": sample.get("qid"),
        "source_file_name": sample.get("source_file_name"),
        "mother_family_id": mother_family_id,
        "leaf_label": sample.get("leaf_label"),
        "observed_actions": observed_actions,
        "uniqueness_source": uniqueness_sources,
        "distractor_modes": distractor_modes,
        "confidence": _confidence(len(observed_actions)),
    }


def _confidence(action_count: int) -> str:
    if action_count >= 3:
        return "high"
    if action_count >= 1:
        return "medium"
    return "low"

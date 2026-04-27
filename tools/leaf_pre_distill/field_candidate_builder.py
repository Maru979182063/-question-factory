from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def build_field_candidates(
    *,
    mother_family_id: str,
    leaf_label: str,
    samples: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> dict[str, Any]:
    sample_count = len(samples)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        for action in trace.get("observed_actions") or []:
            key = (
                str(action.get("field_path") or ""),
                str(action.get("proposed_value") or ""),
                str(action.get("target_layer") or ""),
            )
            grouped[key].append({"trace": trace, "action": action})

    candidates: list[dict[str, Any]] = []
    for (field_path, proposed_value, target_layer), rows in sorted(grouped.items()):
        support_count = len({row["trace"]["sample_id"] for row in rows})
        evidence_count = sum(int(row["action"].get("evidence_count") or 0) for row in rows)
        evidence_counter: Counter[str] = Counter()
        uniqueness_counter: Counter[str] = Counter()
        distractor_counter: Counter[str] = Counter()
        for row in rows:
            evidence_counter.update(row["action"].get("evidence") or [])
            uniqueness_counter.update(row["trace"].get("uniqueness_source") or [])
            distractor_counter.update(row["trace"].get("distractor_modes") or [])
        support_rate = round(support_count / sample_count, 4) if sample_count else 0.0
        candidates.append(
            {
                "field_path": field_path,
                "proposed_value": proposed_value,
                "target_layer": target_layer,
                "support_count": support_count,
                "sample_count": sample_count,
                "support_rate": support_rate,
                "confidence": _confidence(support_rate, sample_count),
                "evidence_count": evidence_count,
                "evidence_examples": [entry[0] for entry in evidence_counter.most_common(8)],
                "uniqueness_source": [entry[0] for entry in uniqueness_counter.most_common(6)],
                "distractor_modes": [entry[0] for entry in distractor_counter.most_common(6)],
                "ablation_question": _ablation_question(field_path, proposed_value),
            }
        )

    schema_gaps = _schema_gaps(mother_family_id, candidates)
    return {
        "mother_family_id": mother_family_id,
        "leaf_label": leaf_label,
        "sample_count": sample_count,
        "field_candidates": candidates,
        "schema_gaps": schema_gaps,
        "summary": {
            "high_confidence_count": sum(1 for item in candidates if item["confidence"] == "high"),
            "medium_confidence_count": sum(1 for item in candidates if item["confidence"] == "medium"),
            "low_confidence_count": sum(1 for item in candidates if item["confidence"] == "low"),
        },
    }


def build_slot_projection_draft(report: dict[str, Any]) -> dict[str, Any]:
    canonical_updates: dict[str, Any] = {}
    overlay_updates: dict[str, Any] = {}
    validator_candidates: list[str] = []
    promotion_targets = {"leaf_pre_distill_report"}

    for candidate in report.get("field_candidates") or []:
        if candidate.get("confidence") == "low":
            continue
        field_path = candidate["field_path"]
        value = candidate["proposed_value"]
        target_layer = candidate["target_layer"]
        if target_layer == "canonical_slot":
            canonical_updates[field_path] = value
            promotion_targets.add("question_card")
        elif target_layer == "business_feature_projection":
            overlay_updates[field_path] = value
            promotion_targets.add("business_feature_card")
        else:
            overlay_updates[field_path] = value
            promotion_targets.add("material_card")
        validator_candidates.append(_validator_candidate(field_path, value))

    if report.get("schema_gaps"):
        promotion_targets.add("schema_gap_report")

    return {
        "mother_family_id": report["mother_family_id"],
        "leaf_label": report["leaf_label"],
        "canonical_slot_updates": canonical_updates,
        "overlay_updates": overlay_updates,
        "schema_gaps": report.get("schema_gaps") or [],
        "validator_contract_candidates": sorted(set(validator_candidates)),
        "promotion_targets": sorted(promotion_targets),
    }


def _confidence(support_rate: float, sample_count: int) -> str:
    if support_rate >= 0.85 and sample_count >= 30:
        return "high"
    if support_rate >= 0.60 and sample_count >= 15:
        return "medium"
    return "low"


def _schema_gaps(mother_family_id: str, candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for candidate in candidates:
        if candidate.get("confidence") == "low":
            continue
        if (
            mother_family_id == "sentence_order"
            and candidate["field_path"] == "ordering_logic"
            and candidate["proposed_value"] == "timeline_progression"
        ):
            gaps.append(
                {
                    "field": "timeline_progression_as_middle_structure",
                    "reason": "timeline progression is better represented as ordering_logic or material overlay than as middle_structure_type",
                    "suggested_resolution": "keep middle_structure_type=local_binding and encode ordering_logic=timeline_progression",
                }
            )
    return gaps


def _ablation_question(field_path: str, proposed_value: str) -> str:
    return f"去掉 {field_path}={proposed_value} 后，唯一性、错项强度或生成稳定性是否明显下降？"


def _validator_candidate(field_path: str, value: str) -> str:
    normalized = f"{field_path}_{value}".replace(".", "_")
    return f"check_{normalized}_evidence"

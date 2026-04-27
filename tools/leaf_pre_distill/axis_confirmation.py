from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONFIRMING_ACTIONS = {
    "keep",
    "rename",
    "merge",
    "split",
    "promote_to_proto_field",
    "map_to_seed_marker",
    "map_to_prompt_guard",
    "map_to_material_mapping",
    "map_to_validator_candidate",
    "map_to_distractor_taxonomy",
}

DEFER_ACTIONS = {
    "drop",
    "reject",
    "defer",
    "downgrade_to_note",
}

SOURCE_TYPES = {
    "candidate_axis",
    "distractor_taxonomy",
    "proto_mother_family",
    "evidence_anchor",
}


def load_axis_decisions(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("axis decision JSON must be an object.")
    return payload


def build_axis_confirmation(
    *,
    manifest: dict[str, Any],
    bootstrap_discovery: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    source_index = _source_index(bootstrap_discovery)
    warnings: list[str] = []
    confirmed: list[dict[str, Any]] = []
    rejected_or_deferred: list[dict[str, Any]] = []

    for index, raw_decision in enumerate(decision_payload.get("decisions") or [], start=1):
        if not isinstance(raw_decision, dict):
            rejected_or_deferred.append(
                {
                    "decision_index": index,
                    "decision": "reject",
                    "status": "rejected",
                    "reason": "decision item is not an object",
                    "raw_decision": raw_decision,
                }
            )
            continue

        source_type = str(raw_decision.get("source_type") or "candidate_axis").strip()
        source_id = str(raw_decision.get("source_id") or raw_decision.get("axis") or raw_decision.get("mode") or "").strip()
        action = str(raw_decision.get("action") or "").strip()
        source_key = (source_type, source_id)

        if source_type not in SOURCE_TYPES:
            warnings.append(f"Unsupported source_type ignored: {source_type}")
            rejected_or_deferred.append(_rejected_decision(raw_decision, source_type, source_id, action, "unsupported_source_type"))
            continue
        if action not in CONFIRMING_ACTIONS and action not in DEFER_ACTIONS:
            warnings.append(f"Unsupported action ignored: {action or '<empty>'}")
            rejected_or_deferred.append(_rejected_decision(raw_decision, source_type, source_id, action, "unsupported_action"))
            continue
        if source_key not in source_index:
            warnings.append(f"Unknown source ignored: {source_type}:{source_id}")
            rejected_or_deferred.append(_rejected_decision(raw_decision, source_type, source_id, action, "unknown_source"))
            continue

        if action in DEFER_ACTIONS:
            rejected_or_deferred.append(
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "decision": action,
                    "status": "deferred" if action in {"defer", "downgrade_to_note"} else "rejected",
                    "rationale": str(raw_decision.get("rationale") or ""),
                }
            )
            continue

        confirmed.append(
            _confirmed_decision(
                raw_decision=raw_decision,
                source_type=source_type,
                source_id=source_id,
                action=action,
                source_item=source_index[source_key],
            )
        )

    proto = bootstrap_discovery.get("proto_mother_family") or {}
    proto_label = str(decision_payload.get("proto_family_label") or proto.get("label") or manifest.get("mother_family_id") or "")
    status = "proto_confirmed" if confirmed else "no_confirmed_axes"

    return {
        "confirmation_version": "v1",
        "enabled": True,
        "source": "human_axis_confirmation",
        "status": status,
        "formalized": False,
        "promotion_allowed": False,
        "reviewer": decision_payload.get("reviewer"),
        "proto_mother_family": {
            "label": proto_label,
            "source_label": proto.get("label"),
            "status": "proto_confirmed" if confirmed else "hypothesis",
            "formal": False,
        },
        "source_artifacts": {
            "bootstrap_discovery": "bootstrap_discovery.json",
            "manifest_job_id": manifest.get("job_id"),
        },
        "axis_decisions": confirmed,
        "rejected_or_deferred": rejected_or_deferred,
        "warnings": warnings,
        "limits": [
            "proto_confirmed is not formal.",
            "confirmed axes are not fields by default.",
            "confirmed axes are not automatically written to card_specs.",
            "formal patch drafts require a separate draft step and human review.",
        ],
    }


def _source_index(bootstrap_discovery: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    proto = bootstrap_discovery.get("proto_mother_family") or {}
    proto_label = str(proto.get("label") or "")
    if proto_label:
        index[("proto_mother_family", proto_label)] = proto
    for axis in bootstrap_discovery.get("candidate_axes") or []:
        axis_id = str(axis.get("axis") or "")
        if axis_id:
            index[("candidate_axis", axis_id)] = axis
    for item in bootstrap_discovery.get("distractor_taxonomy") or []:
        mode = str(item.get("mode") or "")
        if mode:
            index[("distractor_taxonomy", mode)] = item
    for anchor in bootstrap_discovery.get("evidence_anchors") or []:
        anchor_type = str(anchor.get("anchor_type") or "")
        if anchor_type:
            index[("evidence_anchor", anchor_type)] = anchor
    return index


def _confirmed_decision(
    *,
    raw_decision: dict[str, Any],
    source_type: str,
    source_id: str,
    action: str,
    source_item: dict[str, Any],
) -> dict[str, Any]:
    confirmed_name = str(raw_decision.get("target_name") or raw_decision.get("confirmed_name") or source_id)
    target_layer = str(raw_decision.get("target_layer") or _default_target_layer(action, source_type))
    return {
        "source_type": source_type,
        "source_id": source_id,
        "decision": action,
        "confirmed_name": confirmed_name,
        "target_layer": target_layer,
        "status": "proto_confirmed",
        "formal": False,
        "rationale": str(raw_decision.get("rationale") or ""),
        "source_status": source_item.get("status"),
        "evidence_examples": list(source_item.get("evidence_examples") or [])[:6],
        "support_estimate": source_item.get("support_estimate"),
        "risk": source_item.get("risk"),
    }


def _rejected_decision(
    raw_decision: dict[str, Any],
    source_type: str,
    source_id: str,
    action: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "decision": action,
        "status": "rejected",
        "reason": reason,
        "rationale": str(raw_decision.get("rationale") or ""),
    }


def _default_target_layer(action: str, source_type: str) -> str:
    if action == "map_to_prompt_guard":
        return "prompt_assets"
    if action == "map_to_material_mapping":
        return "material_mapping"
    if action == "map_to_validator_candidate":
        return "validator_contract"
    if action == "map_to_distractor_taxonomy" or source_type == "distractor_taxonomy":
        return "signal_layer"
    if action == "map_to_seed_marker":
        return "signal_layer"
    return "business_feature_card"


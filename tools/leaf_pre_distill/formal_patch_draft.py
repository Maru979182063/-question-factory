from __future__ import annotations

from typing import Any


CANONICAL_DRAFT_TARGETS = {
    "question_card",
    "business_feature_card",
    "material_card",
    "signal_layer",
    "runtime_mapping",
    "prompt_assets",
    "validator_contract",
    "material_mapping",
}


def build_formal_patch_draft(
    *,
    manifest: dict[str, Any],
    axis_confirmation: dict[str, Any],
    target_filter: list[str] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    allowed_targets = _target_filter(target_filter, warnings)
    decisions = [
        decision
        for decision in axis_confirmation.get("axis_decisions") or []
        if decision.get("status") == "proto_confirmed"
    ]
    if not decisions:
        return _blocked_draft(
            manifest=manifest,
            axis_confirmation=axis_confirmation,
            warnings=warnings + ["No proto_confirmed axis decisions were available for draft generation."],
        )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        target = str(decision.get("target_layer") or "business_feature_card")
        if target not in CANONICAL_DRAFT_TARGETS:
            warnings.append(f"Decision target_layer is not a canonical draft target and was skipped: {target}")
            continue
        if allowed_targets is not None and target not in allowed_targets:
            continue
        grouped.setdefault(target, []).append(decision)

    target_patches = [
        _target_patch(
            target=target,
            decisions=target_decisions,
            manifest=manifest,
            axis_confirmation=axis_confirmation,
        )
        for target, target_decisions in sorted(grouped.items())
    ]
    if not target_patches:
        return _blocked_draft(
            manifest=manifest,
            axis_confirmation=axis_confirmation,
            warnings=warnings + ["No confirmed decisions matched canonical formal patch draft targets."],
        )

    return {
        "draft_version": "v1",
        "enabled": True,
        "source": "axis_confirmation",
        "status": "draft_only",
        "writeback_allowed": False,
        "formalized": False,
        "promotion_allowed": False,
        "proto_family": axis_confirmation.get("proto_mother_family", {}).get("label") or manifest.get("mother_family_id"),
        "proto_child_family": manifest.get("child_family_id"),
        "leaf_label": manifest.get("leaf_label"),
        "target_patches": target_patches,
        "warnings": warnings,
        "limits": _limits(),
    }


def _target_filter(target_filter: list[str] | None, warnings: list[str]) -> set[str] | None:
    if not target_filter:
        return None
    allowed: set[str] = set()
    for target in target_filter:
        normalized = str(target or "").strip()
        if not normalized:
            continue
        if normalized not in CANONICAL_DRAFT_TARGETS:
            warnings.append(f"Ignored unknown formal patch draft target: {normalized}")
            continue
        allowed.add(normalized)
    return allowed


def _target_patch(
    *,
    target: str,
    decisions: list[dict[str, Any]],
    manifest: dict[str, Any],
    axis_confirmation: dict[str, Any],
) -> dict[str, Any]:
    proto_family = axis_confirmation.get("proto_mother_family", {}).get("label") or manifest.get("mother_family_id")
    scope_key = _scope_key(target=target, proto_family=str(proto_family or ""), child_family_id=manifest.get("child_family_id"))
    return {
        "target": target,
        "scope_key": scope_key,
        "draft_status": "draft_only",
        "writeback_allowed": False,
        "formalized": False,
        "patch": {
            "experimental": True,
            "formalized": False,
            "source": "axis_confirmation",
            "proto_family": proto_family,
            "proto_child_family": manifest.get("child_family_id"),
            "leaf_label": manifest.get("leaf_label"),
            "proto_confirmed_decisions": [_decision_patch_payload(decision) for decision in decisions],
        },
    }


def _decision_patch_payload(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": decision.get("source_type"),
        "source_id": decision.get("source_id"),
        "confirmed_name": decision.get("confirmed_name"),
        "decision": decision.get("decision"),
        "status": "proto_confirmed",
        "formal": False,
        "rationale": decision.get("rationale") or "",
        "evidence_examples": list(decision.get("evidence_examples") or [])[:6],
        "support_estimate": decision.get("support_estimate"),
        "risk": decision.get("risk"),
    }


def _blocked_draft(
    *,
    manifest: dict[str, Any],
    axis_confirmation: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "draft_version": "v1",
        "enabled": True,
        "source": "axis_confirmation",
        "status": "blocked",
        "writeback_allowed": False,
        "formalized": False,
        "promotion_allowed": False,
        "proto_family": axis_confirmation.get("proto_mother_family", {}).get("label") or manifest.get("mother_family_id"),
        "proto_child_family": manifest.get("child_family_id"),
        "leaf_label": manifest.get("leaf_label"),
        "target_patches": [],
        "warnings": warnings,
        "limits": _limits(),
    }


def _scope_key(*, target: str, proto_family: str, child_family_id: Any) -> str:
    child = str(child_family_id or "proto_leaf")
    if target == "business_feature_card":
        return f"proto.{proto_family}.{child}.feature.v0"
    if target == "prompt_assets":
        return f"proto_{proto_family}_{child}_prompt"
    if target == "validator_contract":
        return f"proto.{proto_family}.{child}.validator.v0"
    if target == "runtime_mapping":
        return f"proto.{proto_family}.{child}.runtime.v0"
    if target == "material_mapping":
        return f"proto.{proto_family}.{child}.material_mapping.v0"
    if target == "signal_layer":
        return f"proto.{proto_family}.{child}.signal.v0"
    if target == "material_card":
        return f"proto.{proto_family}.{child}.material.v0"
    return f"proto.{proto_family}.{child}.question.v0"


def _limits() -> list[str]:
    return [
        "This file is a patch draft, not a formal config change.",
        "writeback_allowed is false.",
        "formalized is false.",
        "Each target patch must still go through human review, patch, and promotion.",
        "No card_specs writeback has occurred.",
    ]


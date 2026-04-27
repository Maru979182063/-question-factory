from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


TARGET_FILE_PLANS = {
    "business_feature_card": "card_specs/business_feature_slots/examples/{proto_family}_{proto_child_family}.proto.yaml",
    "signal_layer": "card_specs/normalized/signal_layers/{proto_family}_signal_layer.proto.yaml",
    "material_mapping": "card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml",
    "runtime_mapping": "card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml",
    "prompt_assets": "prompt_skeleton_service/configs/prompt_templates.yaml",
    "validator_contract": "card_specs/validator_contracts/proto/{proto_family}_{proto_child_family}.validator.yaml",
    "material_card": "card_specs/normalized/material_cards/{proto_family}_material_cards.proto.yaml",
    "question_card": "card_specs/normalized/question_cards/{proto_family}_standard_question_card.proto.yaml",
}

SHARED_TARGETS = {"material_mapping", "runtime_mapping", "prompt_assets"}


def build_formal_writeback_plan(
    *,
    formal_patch_draft: dict[str, Any],
    reviewer: str | None = None,
) -> dict[str, Any]:
    proto_family = str(formal_patch_draft.get("proto_family") or "proto")
    proto_child_family = str(formal_patch_draft.get("proto_child_family") or "proto_leaf")
    target_patches = formal_patch_draft.get("target_patches") or []
    writeback_items = [
        _writeback_item(
            target_patch=target_patch,
            proto_family=proto_family,
            proto_child_family=proto_child_family,
        )
        for target_patch in target_patches
        if isinstance(target_patch, dict)
    ]

    return {
        "plan_version": "v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "formal_patch_draft",
        "status": "preview_only",
        "writeback_allowed": False,
        "requires_explicit_approval": True,
        "reviewer": reviewer,
        "proto_family": proto_family,
        "proto_child_family": proto_child_family,
        "leaf_label": formal_patch_draft.get("leaf_label"),
        "writeback_items": writeback_items,
        "legacy_family_impact": _legacy_family_impact(writeback_items),
        "regression_requirements": [
            "Run sentence_fill regression before writeback.",
            "Run sentence_order regression before writeback.",
            "Run center_understanding regression before writeback.",
            "Run word_usage proto route regression before writeback.",
        ],
        "rollback_note": (
            "No files are changed by this plan. If later writeback is approved, revert the exact files "
            "listed in writeback_items or apply the inverse diff from formal_writeback_diff.md."
        ),
        "limits": [
            "This is a writeback preview, not a writeback.",
            "writeback_allowed is false.",
            "Explicit approval is required before any formal file changes.",
            "No card_specs, prompt assets, validator, runtime mapping, or generation files are modified by this plan.",
        ],
    }


def render_formal_writeback_diff(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Formal Writeback Diff Preview")
    lines.append("")
    lines.append("> Preview only. No files have been changed.")
    lines.append("")
    lines.append(f"- status: `{plan.get('status')}`")
    lines.append(f"- writeback_allowed: `{plan.get('writeback_allowed')}`")
    lines.append(f"- requires_explicit_approval: `{plan.get('requires_explicit_approval')}`")
    lines.append(f"- proto_family: `{plan.get('proto_family')}`")
    lines.append(f"- proto_child_family: `{plan.get('proto_child_family')}`")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    items = plan.get("writeback_items") or []
    if not items:
        lines.append("- No target files proposed.")
    for item in items:
        lines.append(f"- `{item.get('target')}` -> `{item.get('target_file')}` ({item.get('operation')})")
    lines.append("")

    lines.append("## Proposed Additions")
    lines.append("")
    for item in items:
        lines.append(f"### {item.get('target')}")
        lines.append("")
        lines.append(f"File: `{item.get('target_file')}`")
        lines.append("")
        for addition in item.get("proposed_additions") or []:
            lines.append(f"- `{addition.get('name')}`: {addition.get('summary')}")
        if item.get("prompt_guards"):
            lines.append("")
            lines.append("Prompt guards:")
            for guard in item["prompt_guards"]:
                lines.append(f"- {guard}")
        if item.get("validator_candidates"):
            lines.append("")
            lines.append("Validator candidates:")
            for candidate in item["validator_candidates"]:
                lines.append(f"- `{candidate}`")
        lines.append("")

    lines.append("## Legacy Family Impact")
    lines.append("")
    impact = plan.get("legacy_family_impact") or {}
    lines.append(f"- sentence_fill: `{impact.get('sentence_fill')}`")
    lines.append(f"- sentence_order: `{impact.get('sentence_order')}`")
    lines.append(f"- center_understanding: `{impact.get('center_understanding')}`")
    lines.append(f"- shared_config_touch: `{impact.get('shared_config_touch')}`")
    lines.append("")

    lines.append("## Rollback")
    lines.append("")
    lines.append(plan.get("rollback_note") or "No rollback note.")
    lines.append("")

    lines.append("## Regression Requirements")
    lines.append("")
    for requirement in plan.get("regression_requirements") or []:
        lines.append(f"- {requirement}")
    lines.append("")
    return "\n".join(lines)


def _writeback_item(*, target_patch: dict[str, Any], proto_family: str, proto_child_family: str) -> dict[str, Any]:
    target = str(target_patch.get("target") or "")
    patch = target_patch.get("patch") or {}
    decisions = patch.get("proto_confirmed_decisions") or []
    target_file_template = TARGET_FILE_PLANS.get(target, "card_specs/proto/{proto_family}_{proto_child_family}.yaml")
    target_file = target_file_template.format(proto_family=proto_family, proto_child_family=proto_child_family)
    return {
        "target": target,
        "scope_key": target_patch.get("scope_key"),
        "target_file": target_file,
        "operation": "append_or_create_preview",
        "writeback_allowed": False,
        "requires_explicit_approval": True,
        "proposed_additions": [_addition_from_decision(decision) for decision in decisions],
        "prompt_guards": _prompt_guards(target, decisions),
        "validator_candidates": _validator_candidates(target, decisions),
        "shared_config_touch": target in SHARED_TARGETS,
        "rollback": f"Remove the additions for scope_key={target_patch.get('scope_key') or '<unknown>'} from {target_file}.",
    }


def _addition_from_decision(decision: dict[str, Any]) -> dict[str, str]:
    name = str(decision.get("confirmed_name") or decision.get("source_id") or "")
    return {
        "name": name,
        "source_id": str(decision.get("source_id") or ""),
        "decision": str(decision.get("decision") or ""),
        "summary": str(decision.get("rationale") or "Proto-confirmed axis addition."),
        "status": "preview_only",
    }


def _prompt_guards(target: str, decisions: list[dict[str, Any]]) -> list[str]:
    if target != "prompt_assets":
        return []
    guards = []
    for decision in decisions:
        name = decision.get("confirmed_name") or decision.get("source_id")
        guards.append(f"Respect proto-confirmed axis `{name}` when generating and explaining the item.")
    return guards


def _validator_candidates(target: str, decisions: list[dict[str, Any]]) -> list[str]:
    if target != "validator_contract":
        return []
    candidates = []
    for decision in decisions:
        name = str(decision.get("confirmed_name") or decision.get("source_id") or "axis")
        candidates.append(f"check_proto_{name}_evidence")
    return candidates


def _legacy_family_impact(writeback_items: list[dict[str, Any]]) -> dict[str, Any]:
    shared = any(item.get("shared_config_touch") for item in writeback_items)
    return {
        "sentence_fill": "requires_regression" if shared else "no_direct_file_touch_planned",
        "sentence_order": "requires_regression" if shared else "no_direct_file_touch_planned",
        "center_understanding": "requires_regression" if shared else "no_direct_file_touch_planned",
        "shared_config_touch": shared,
        "note": "Shared config targets require regression even though this preview does not write files.",
    }


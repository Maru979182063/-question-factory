from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ACTIVATION_ARTIFACT_NAMES = {
    "plan": "runtime_activation_plan.json",
    "report": "runtime_activation_plan_report.md",
}


RUNTIME_TARGET_NAMES = [
    "business_subtype_mapping",
    "question_card_binding",
    "business_feature_card_binding",
    "prompt_assets_binding",
    "validator_contract_binding",
    "material_bridge_mapping",
    "runtime_mapping",
]


def run_runtime_activation_plan(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path | None = None,
    formalization_packet_path: str | Path | None = None,
    formal_patch_draft_path: str | Path | None = None,
    material_bridge_mapping_draft_path: str | Path | None = None,
    system_alignment_findings_path: str | Path | None = None,
    question_runtime_path: str | Path | None = None,
) -> dict[str, str]:
    artifact_root = Path(artifact_dir)
    output_path = Path(output_dir) if output_dir is not None else artifact_root
    output_path.mkdir(parents=True, exist_ok=True)
    refs = resolve_activation_evidence_paths(
        artifact_dir=artifact_root,
        formalization_packet_path=formalization_packet_path,
        formal_patch_draft_path=formal_patch_draft_path,
        material_bridge_mapping_draft_path=material_bridge_mapping_draft_path,
        system_alignment_findings_path=system_alignment_findings_path,
        question_runtime_path=question_runtime_path,
    )
    plan = build_runtime_activation_plan(evidence_refs=refs)
    plan_path = output_path / ACTIVATION_ARTIFACT_NAMES["plan"]
    report_path = output_path / ACTIVATION_ARTIFACT_NAMES["report"]
    _write_json(plan_path, plan)
    report_path.write_text(render_runtime_activation_plan_report(plan), encoding="utf-8")
    return {"runtime_activation_plan": str(plan_path), "runtime_activation_plan_report": str(report_path)}


def resolve_activation_evidence_paths(*, artifact_dir: str | Path, **paths: str | Path | None) -> dict[str, str]:
    root = Path(artifact_dir)
    defaults = {
        "formalization_packet_path": "new_leaf_formalization_packet.json",
        "formal_patch_draft_path": "formal_patch_draft.json",
        "material_bridge_mapping_draft_path": "material_bridge_mapping_draft.json",
        "system_alignment_findings_path": "system_alignment_findings.json",
    }
    resolved: dict[str, str] = {}
    for key, default_name in defaults.items():
        candidate = Path(paths[key]) if paths.get(key) is not None else root / default_name
        if candidate.exists():
            resolved[key.removesuffix("_path")] = str(candidate)
    runtime_candidate = Path(paths["question_runtime_path"]) if paths.get("question_runtime_path") else Path("prompt_skeleton_service/configs/question_runtime.yaml")
    if runtime_candidate.exists():
        resolved["question_runtime"] = str(runtime_candidate)
    return resolved


def build_runtime_activation_plan(*, evidence_refs: dict[str, str]) -> dict[str, Any]:
    evidence = {key: _load_artifact(path) for key, path in evidence_refs.items()}
    packet = evidence.get("formalization_packet") or {}
    family_context = packet.get("family_context") or {}
    formal_targets = {item.get("target"): item for item in packet.get("formal_target_candidates") or []}
    bridge = evidence.get("material_bridge_mapping_draft") or {}
    alignment = evidence.get("system_alignment_findings") or {}

    runtime_targets = {
        "business_subtype_mapping": _target_entry(
            required=True,
            current_status="missing" if not family_context.get("business_subtype") else "draft_required",
            proposed_action="Add or confirm a guarded business_subtype mapping through a writeback plan before formal activation.",
            target_files=[],
            risk="Unknown subtype must not fall through to a broad fallback.",
        ),
        "question_card_binding": _target_from_packet(formal_targets, "question_card"),
        "business_feature_card_binding": _target_from_packet(formal_targets, "business_feature_card"),
        "prompt_assets_binding": _target_from_packet(formal_targets, "prompt_assets"),
        "validator_contract_binding": _target_from_packet(formal_targets, "validator_contract"),
        "material_bridge_mapping": _material_bridge_target(bridge=bridge, alignment=alignment),
        "runtime_mapping": _target_from_packet(formal_targets, "runtime_mapping"),
    }
    blockers = build_activation_blockers(runtime_targets=runtime_targets, family_context=family_context)
    plan = {
        "activation_plan_version": "v1",
        "status": "draft_only",
        "formalized": False,
        "writeback_allowed": False,
        "requires_human_review": True,
        "requires_regression": True,
        "family_context": family_context,
        "evidence_refs": evidence_refs,
        "runtime_targets": runtime_targets,
        "proto_vs_formal": {
            "can_run_proto_trial": bool(family_context.get("business_subtype")) and "business_subtype_missing" not in blockers,
            "can_run_formal_generation": False,
            "blocked_reasons": blockers,
        },
        "required_regressions_before_activation": [
            "new_leaf_proto_trial",
            "truth_gold_regression_eval_and_insurance",
            "legacy_family_regression",
            "material_bridge_smoke_when_material_mapping_changes",
        ],
        "activation_blockers": blockers,
        "limits": [
            "This plan does not modify runtime code or config.",
            "This plan does not write input_decoder, question_generation, validator, prompt assets, material mapping, or runtime mapping.",
            "Formal generation remains disabled until writeback plan, approval, and regression pass.",
        ],
    }
    assert_activation_boundaries(plan)
    return plan


def _target_entry(*, required: bool, current_status: str, proposed_action: str, target_files: list[str], risk: str) -> dict[str, Any]:
    return {
        "required": required,
        "current_status": current_status,
        "proposed_action": proposed_action,
        "target_files": target_files,
        "risk": risk,
    }


def _target_from_packet(formal_targets: dict[str, dict[str, Any]], target: str) -> dict[str, Any]:
    candidate = formal_targets.get(target) or {}
    status = "draft_candidate" if candidate else "missing"
    return _target_entry(
        required=True,
        current_status=status,
        proposed_action=f"Create or review {target} writeback plan before runtime activation.",
        target_files=[],
        risk="Runtime activation is unsafe without a reviewed mapping and regression." if not candidate else "Draft candidate still requires writeback plan.",
    )


def _material_bridge_target(*, bridge: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
    has_bridge = bool(bridge)
    confirmed = bridge.get("confirmed_repository_fields_used") or (alignment.get("confirmed_bridge_request_fields") if alignment else [])
    return _target_entry(
        required=True,
        current_status="draft_candidate" if has_bridge else "missing",
        proposed_action="Map draft material requirements to repository-confirmed material bridge/search fields, then smoke test without writeback.",
        target_files=[],
        risk="Material bridge fields must come from repository alignment, not invented draft fields.",
    ) | {"confirmed_repository_fields_used": confirmed or []}


def build_activation_blockers(*, runtime_targets: dict[str, Any], family_context: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not family_context.get("business_subtype"):
        blockers.append("business_subtype_missing")
    for name in RUNTIME_TARGET_NAMES:
        target = runtime_targets.get(name) or {}
        if target.get("required") and target.get("current_status") == "missing":
            blockers.append(f"{name}_missing")
    blockers.append("formal_generation_requires_writeback_plan_and_regression")
    return sorted(set(blockers))


def assert_activation_boundaries(plan: dict[str, Any]) -> None:
    text = json.dumps(plan, ensure_ascii=False).lower()
    forbidden = [
        '"formalized": true',
        '"writeback_allowed": true',
        '"verified": true',
        '"verified_original_source": true',
        '"card_specs_write": true',
        '"runtime_write": true',
    ]
    for token in forbidden:
        if token in text:
            raise ValueError(f"runtime activation plan violates boundary: {token}")


def render_runtime_activation_plan_report(plan: dict[str, Any]) -> str:
    lines = [
        "# Runtime Activation Plan",
        "",
        "> 这是只读接入计划，不修改 runtime、prompt、validator、generation 或配置文件。",
        "",
        f"- status: `{plan.get('status')}`",
        f"- family_context: `{plan.get('family_context')}`",
        f"- can_run_proto_trial: `{bool((plan.get('proto_vs_formal') or {}).get('can_run_proto_trial'))}`",
        f"- can_run_formal_generation: `{bool((plan.get('proto_vs_formal') or {}).get('can_run_formal_generation'))}`",
        f"- writeback_allowed: `{bool(plan.get('writeback_allowed'))}`",
        "",
        "## Runtime Targets",
        "",
        "| target | status | required | risk |",
        "|---|---|---|---|",
    ]
    for name, target in (plan.get("runtime_targets") or {}).items():
        lines.append(f"| `{name}` | `{target.get('current_status')}` | `{bool(target.get('required'))}` | {target.get('risk') or ''} |")
    lines.extend(["", "## Activation Blockers", ""])
    blockers = plan.get("activation_blockers") or []
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _load_artifact(path: str) -> Any:
    p = Path(path)
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    if p.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return p.read_text(encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a draft-only runtime activation plan.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--formalization-packet")
    parser.add_argument("--formal-patch-draft")
    parser.add_argument("--material-bridge-mapping-draft")
    parser.add_argument("--system-alignment-findings")
    parser.add_argument("--question-runtime")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    artifacts = run_runtime_activation_plan(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        formalization_packet_path=args.formalization_packet,
        formal_patch_draft_path=args.formal_patch_draft,
        material_bridge_mapping_draft_path=args.material_bridge_mapping_draft,
        system_alignment_findings_path=args.system_alignment_findings,
        question_runtime_path=args.question_runtime,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

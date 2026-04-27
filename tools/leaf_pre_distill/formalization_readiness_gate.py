from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


READINESS_ARTIFACT_NAMES = {
    "checklist": "formalization_readiness_checklist.json",
    "report": "formalization_readiness_report.md",
}


def run_formalization_readiness_gate(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path | None = None,
    formalization_packet_path: str | Path | None = None,
    runtime_activation_plan_path: str | Path | None = None,
    truth_gold_regression_results_path: str | Path | None = None,
    truth_gold_split_manifest_path: str | Path | None = None,
    agent_review_feedback_path: str | Path | None = None,
    material_card_draft_path: str | Path | None = None,
    material_quality_regression_draft_path: str | Path | None = None,
    source_text_evidence_manifest_path: str | Path | None = None,
    source_gold_alignment_summary_path: str | Path | None = None,
    material_quality_regression_results_path: str | Path | None = None,
    formal_writeback_plan_path: str | Path | None = None,
    formal_patch_draft_path: str | Path | None = None,
    approval_summary_path: str | Path | None = None,
    test_result_summary_path: str | Path | None = None,
) -> dict[str, str]:
    artifact_root = Path(artifact_dir)
    output_path = Path(output_dir) if output_dir is not None else artifact_root
    output_path.mkdir(parents=True, exist_ok=True)
    refs = resolve_readiness_evidence_paths(
        artifact_dir=artifact_root,
        formalization_packet_path=formalization_packet_path,
        runtime_activation_plan_path=runtime_activation_plan_path,
        truth_gold_regression_results_path=truth_gold_regression_results_path,
        truth_gold_split_manifest_path=truth_gold_split_manifest_path,
        agent_review_feedback_path=agent_review_feedback_path,
        material_card_draft_path=material_card_draft_path,
        material_quality_regression_draft_path=material_quality_regression_draft_path,
        source_text_evidence_manifest_path=source_text_evidence_manifest_path,
        source_gold_alignment_summary_path=source_gold_alignment_summary_path,
        material_quality_regression_results_path=material_quality_regression_results_path,
        formal_writeback_plan_path=formal_writeback_plan_path,
        formal_patch_draft_path=formal_patch_draft_path,
        approval_summary_path=approval_summary_path,
        test_result_summary_path=test_result_summary_path,
    )
    checklist = build_formalization_readiness_checklist(evidence_refs=refs)
    checklist_path = output_path / READINESS_ARTIFACT_NAMES["checklist"]
    report_path = output_path / READINESS_ARTIFACT_NAMES["report"]
    _write_json(checklist_path, checklist)
    report_path.write_text(render_formalization_readiness_report(checklist), encoding="utf-8")
    return {"formalization_readiness_checklist": str(checklist_path), "formalization_readiness_report": str(report_path)}


def resolve_readiness_evidence_paths(*, artifact_dir: str | Path, **paths: str | Path | None) -> dict[str, str]:
    root = Path(artifact_dir)
    defaults = {
        "formalization_packet_path": "new_leaf_formalization_packet.json",
        "runtime_activation_plan_path": "runtime_activation_plan.json",
        "truth_gold_regression_results_path": "truth_gold_regression_results.json",
        "truth_gold_split_manifest_path": "truth_gold_split_manifest.json",
        "agent_review_feedback_path": "agent_review_feedback_normalized.json",
        "material_card_draft_path": "material_card_draft.json",
        "material_quality_regression_draft_path": "material_quality_regression_draft.json",
        "source_text_evidence_manifest_path": "source_text_evidence_manifest.json",
        "source_gold_alignment_summary_path": "source_gold_alignment_summary.json",
        "material_quality_regression_results_path": "material_quality_regression_results.json",
        "formal_writeback_plan_path": "formal_writeback_plan.json",
        "formal_patch_draft_path": "formal_patch_draft.json",
        "approval_summary_path": "formalization_approval_summary.json",
        "test_result_summary_path": "formalization_test_result_summary.json",
    }
    resolved: dict[str, str] = {}
    for key, default_name in defaults.items():
        candidate = Path(paths[key]) if paths.get(key) is not None else root / default_name
        if candidate.exists():
            resolved[key.removesuffix("_path")] = str(candidate)
    return resolved


def build_formalization_readiness_checklist(*, evidence_refs: dict[str, str]) -> dict[str, Any]:
    evidence = {key: _load_artifact(path) for key, path in evidence_refs.items()}
    packet = evidence.get("formalization_packet") or {}
    activation = evidence.get("runtime_activation_plan") or {}
    feedback = evidence.get("agent_review_feedback") or {}
    material_card = evidence.get("material_card_draft") or {}
    source_text = evidence.get("source_text_evidence_manifest") or {}
    alignment = evidence.get("source_gold_alignment_summary") or {}
    material_quality = evidence.get("material_quality_regression_results") or {}
    regression = evidence.get("truth_gold_regression_results") or {}
    split = evidence.get("truth_gold_split_manifest") or {}
    approval = evidence.get("approval_summary") or {}

    checks = [
        _check("formalization_packet_available", bool(packet), evidence_refs.get("formalization_packet"), True, "Formalization packet must exist."),
        _check("runtime_activation_plan_available", bool(activation), evidence_refs.get("runtime_activation_plan"), True, "Runtime activation plan must exist before readiness gate can pass."),
        _check("agent_feedback_normalized", bool(feedback), evidence_refs.get("agent_review_feedback"), True, "User feedback must be normalized as evidence."),
        _check("truth_gold_regression_available", bool(regression), evidence_refs.get("truth_gold_regression_results"), True, "Truth-gold regression is required before formalization."),
        _check("insurance_holdout_available", bool((split.get("splits") or {}).get("insurance_holdout")), evidence_refs.get("truth_gold_split_manifest"), True, "Insurance holdout protects against overfit."),
        _check("material_card_is_draft_only", not material_card or _is_false(material_card.get("formalized")) and _is_false(material_card.get("writeback_allowed")), evidence_refs.get("material_card_draft"), True, "material_card_draft must remain draft-only."),
        _check("source_text_evidence_available", bool(source_text.get("available_count")), evidence_refs.get("source_text_evidence_manifest"), True, "Source text evidence must exist before material-card review."),
        _check("source_gold_alignment_available", bool(alignment.get("alignment_count")), evidence_refs.get("source_gold_alignment_summary"), True, "Source/gold alignment must exist before material-card review."),
        _check("material_quality_regression_available", bool(material_quality), evidence_refs.get("material_quality_regression_results"), True, "Material quality regression must exist before material-card review."),
        _check("material_quality_regression_not_blocked", bool(material_quality) and material_quality.get("status") != "blocked", evidence_refs.get("material_quality_regression_results"), True, "Blocked material quality regression prevents material-card review readiness."),
        _check("material_source_not_verified", True, evidence_refs.get("material_card_draft"), False, "Source seeds are not verified source; material_card formalization remains blocked."),
        _check("writeback_plan_available", bool(evidence.get("formal_writeback_plan")), evidence_refs.get("formal_writeback_plan"), False, "Writeback plan is required before executor readiness."),
        _check("explicit_approval_available", bool(approval.get("approved") is True), evidence_refs.get("approval_summary"), True, "Explicit approval is required before executor readiness."),
    ]
    high_feedback = [
        item.get("dimension")
        for item in feedback.get("normalized_feedback") or []
        if item.get("severity") == "high"
    ]
    if high_feedback:
        checks.append(
            {
                "check_id": "high_severity_feedback_resolved",
                "status": "fail",
                "evidence": evidence_refs.get("agent_review_feedback", ""),
                "blocking": True,
                "notes": f"Unresolved high severity feedback: {', '.join(str(item) for item in high_feedback)}",
            }
        )
    activation_blockers = activation.get("activation_blockers") or []
    if activation_blockers:
        checks.append(
            {
                "check_id": "runtime_activation_blockers_clear",
                "status": "fail",
                "evidence": evidence_refs.get("runtime_activation_plan", ""),
                "blocking": True,
                "notes": ", ".join(activation_blockers),
            }
        )
    blocking = [check for check in checks if check.get("blocking") and check.get("status") == "fail"]
    warnings = [check for check in checks if check.get("status") == "warning"]
    material_line_status = material_line_readiness_status(source_text=source_text, alignment=alignment, material_quality=material_quality)
    status = "blocked" if blocking else ("review_needed" if warnings else "proto_ready")
    if status == "proto_ready" and material_line_status == "review_needed":
        status = "review_needed"
    if status == "proto_ready" and material_line_status == "material_card_review_ready":
        status = "material_card_review_ready"
    if status == "proto_ready" and evidence.get("formal_writeback_plan"):
        status = "writeback_plan_ready"
    if status == "writeback_plan_ready" and approval.get("approved") is True and not blocking:
        status = "executor_ready"
    checklist = {
        "gate_version": "v1",
        "status": status,
        "formalized": False,
        "writeback_allowed": False,
        "requires_human_review": True,
        "requires_regression": True,
        "family_context": packet.get("family_context") or activation.get("family_context") or {},
        "evidence_refs": evidence_refs,
        "checks": checks,
        "categories": {
            "evidence_completeness": _status_counts(checks[:5]),
            "user_feedback_resolution": {"high_severity_unresolved": len(high_feedback)},
            "runtime_activation": {"blocker_count": len(activation_blockers), "can_run_formal_generation": bool((activation.get("proto_vs_formal") or {}).get("can_run_formal_generation"))},
            "material_line_readiness": {
                "status": material_line_status,
                "source_text_evidence_available": bool(source_text.get("available_count")),
                "source_gold_alignment_available": bool(alignment.get("alignment_count")),
                "material_quality_regression_status": material_quality.get("status"),
                "material_card_formalization_allowed": False,
                "source_verified": False,
            },
            "regression_readiness": {"truth_gold_regression_available": bool(regression), "insurance_holdout_available": bool((split.get("splits") or {}).get("insurance_holdout"))},
            "legacy_pollution_risk": {"legacy_regression_required": True},
            "writeback_safety": {"writeback_plan_available": bool(evidence.get("formal_writeback_plan")), "approval_available": bool(approval.get("approved") is True)},
        },
        "blocking_issues": [check["check_id"] for check in blocking],
        "recommended_next_action": recommend_next_action(blocking=blocking, activation=activation, evidence=evidence),
        "limits": [
            "This gate judges readiness only; it does not approve or write back.",
            "Warnings are not treated as pass.",
            "Material source seeds remain unverified and cannot formalize material_card in v1.",
        ],
    }
    assert_gate_boundaries(checklist)
    return checklist


def _check(check_id: str, condition: bool, evidence: str | None, blocking: bool, notes: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if condition else "fail",
        "evidence": evidence or "",
        "blocking": blocking,
        "notes": notes,
    }


def _is_false(value: Any) -> bool:
    return value is False or value is None


def _status_counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    return counts


def recommend_next_action(*, blocking: list[dict[str, Any]], activation: dict[str, Any], evidence: dict[str, Any]) -> str:
    if blocking:
        if any(check["check_id"] == "runtime_activation_plan_available" for check in blocking):
            return "fix_evidence"
        return "human_review"
    if not (activation.get("proto_vs_formal") or {}).get("can_run_proto_trial"):
        return "run_proto_trial"
    if not evidence.get("formal_writeback_plan"):
        return "writeback_plan"
    return "stop"


def material_line_readiness_status(
    *,
    source_text: dict[str, Any],
    alignment: dict[str, Any],
    material_quality: dict[str, Any],
) -> str:
    if not source_text.get("available_count"):
        return "blocked"
    if not alignment.get("alignment_count"):
        return "blocked"
    if not material_quality:
        return "blocked"
    if material_quality.get("status") == "blocked":
        return "blocked"
    if material_quality.get("requires_human_review", True):
        return "review_needed"
    return "material_card_review_ready"


def assert_gate_boundaries(checklist: dict[str, Any]) -> None:
    text = json.dumps(checklist, ensure_ascii=False).lower()
    for token in ['"formalized": true', '"writeback_allowed": true', '"verified": true', '"verified_original_source": true']:
        if token in text:
            raise ValueError(f"readiness gate violates boundary: {token}")


def render_formalization_readiness_report(checklist: dict[str, Any]) -> str:
    lines = [
        "# Formalization Readiness Gate",
        "",
        "> 这是正式化就绪判断，不是 approval、executor 或写回。",
        "",
        f"- status: `{checklist.get('status')}`",
        f"- family_context: `{checklist.get('family_context')}`",
        f"- writeback_allowed: `{bool(checklist.get('writeback_allowed'))}`",
        f"- recommended_next_action: `{checklist.get('recommended_next_action')}`",
        "",
        "## Checks",
        "",
        "| check | status | blocking | notes |",
        "|---|---|---|---|",
    ]
    for check in checklist.get("checks") or []:
        lines.append(f"| `{check.get('check_id')}` | `{check.get('status')}` | `{bool(check.get('blocking'))}` | {check.get('notes') or ''} |")
    lines.extend(["", "## Blocking Issues", ""])
    issues = checklist.get("blocking_issues") or []
    if issues:
        lines.extend(f"- {item}" for item in issues)
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
    parser = argparse.ArgumentParser(description="Evaluate new-leaf formalization readiness.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--formalization-packet")
    parser.add_argument("--runtime-activation-plan")
    parser.add_argument("--truth-gold-regression-results")
    parser.add_argument("--truth-gold-split-manifest")
    parser.add_argument("--agent-review-feedback")
    parser.add_argument("--material-card-draft")
    parser.add_argument("--material-quality-regression-draft")
    parser.add_argument("--source-text-evidence-manifest")
    parser.add_argument("--source-gold-alignment-summary")
    parser.add_argument("--material-quality-regression-results")
    parser.add_argument("--formal-writeback-plan")
    parser.add_argument("--formal-patch-draft")
    parser.add_argument("--approval-summary")
    parser.add_argument("--test-result-summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    artifacts = run_formalization_readiness_gate(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        formalization_packet_path=args.formalization_packet,
        runtime_activation_plan_path=args.runtime_activation_plan,
        truth_gold_regression_results_path=args.truth_gold_regression_results,
        truth_gold_split_manifest_path=args.truth_gold_split_manifest,
        agent_review_feedback_path=args.agent_review_feedback,
        material_card_draft_path=args.material_card_draft,
        material_quality_regression_draft_path=args.material_quality_regression_draft,
        source_text_evidence_manifest_path=args.source_text_evidence_manifest,
        source_gold_alignment_summary_path=args.source_gold_alignment_summary,
        material_quality_regression_results_path=args.material_quality_regression_results,
        formal_writeback_plan_path=args.formal_writeback_plan,
        formal_patch_draft_path=args.formal_patch_draft,
        approval_summary_path=args.approval_summary,
        test_result_summary_path=args.test_result_summary,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

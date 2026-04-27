from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PACKET_ARTIFACT_NAMES = {
    "packet": "new_leaf_formalization_packet.json",
    "report": "new_leaf_formalization_packet_report.md",
}

FORMAL_TARGETS = {
    "business_feature_card",
    "signal_layer",
    "material_card",
    "prompt_assets",
    "validator_contract",
    "runtime_mapping",
    "material_mapping",
    "question_card",
}


def run_new_leaf_formalization_packet(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    bootstrap_discovery_path: str | Path | None = None,
    axis_confirmation_path: str | Path | None = None,
    formal_patch_draft_path: str | Path | None = None,
    formal_writeback_plan_path: str | Path | None = None,
    material_card_draft_path: str | Path | None = None,
    material_bridge_mapping_draft_path: str | Path | None = None,
    material_quality_regression_draft_path: str | Path | None = None,
    source_candidate_review_path: str | Path | None = None,
    source_seed_registry_path: str | Path | None = None,
    crawl_seed_manifest_path: str | Path | None = None,
    source_text_evidence_manifest_path: str | Path | None = None,
    source_text_evidence_results_path: str | Path | None = None,
    source_gold_alignment_summary_path: str | Path | None = None,
    source_gold_alignment_results_path: str | Path | None = None,
    material_quality_regression_results_path: str | Path | None = None,
    truth_gold_regression_results_path: str | Path | None = None,
    truth_gold_split_manifest_path: str | Path | None = None,
    agent_review_feedback_path: str | Path | None = None,
    system_alignment_findings_path: str | Path | None = None,
) -> dict[str, str]:
    artifact_root = Path(artifact_dir)
    output_path = Path(output_dir) if output_dir is not None else artifact_root
    output_path.mkdir(parents=True, exist_ok=True)
    refs = resolve_formalization_evidence_paths(
        artifact_dir=artifact_root,
        manifest_path=manifest_path,
        bootstrap_discovery_path=bootstrap_discovery_path,
        axis_confirmation_path=axis_confirmation_path,
        formal_patch_draft_path=formal_patch_draft_path,
        formal_writeback_plan_path=formal_writeback_plan_path,
        material_card_draft_path=material_card_draft_path,
        material_bridge_mapping_draft_path=material_bridge_mapping_draft_path,
        material_quality_regression_draft_path=material_quality_regression_draft_path,
        source_candidate_review_path=source_candidate_review_path,
        source_seed_registry_path=source_seed_registry_path,
        crawl_seed_manifest_path=crawl_seed_manifest_path,
        source_text_evidence_manifest_path=source_text_evidence_manifest_path,
        source_text_evidence_results_path=source_text_evidence_results_path,
        source_gold_alignment_summary_path=source_gold_alignment_summary_path,
        source_gold_alignment_results_path=source_gold_alignment_results_path,
        material_quality_regression_results_path=material_quality_regression_results_path,
        truth_gold_regression_results_path=truth_gold_regression_results_path,
        truth_gold_split_manifest_path=truth_gold_split_manifest_path,
        agent_review_feedback_path=agent_review_feedback_path,
        system_alignment_findings_path=system_alignment_findings_path,
    )
    packet = build_new_leaf_formalization_packet(artifact_dir=artifact_root, evidence_refs=refs)
    packet_path = output_path / PACKET_ARTIFACT_NAMES["packet"]
    report_path = output_path / PACKET_ARTIFACT_NAMES["report"]
    _write_json(packet_path, packet)
    report_path.write_text(render_new_leaf_formalization_packet_report(packet), encoding="utf-8")
    return {
        "new_leaf_formalization_packet": str(packet_path),
        "new_leaf_formalization_packet_report": str(report_path),
    }


def resolve_formalization_evidence_paths(
    *,
    artifact_dir: str | Path,
    **paths: str | Path | None,
) -> dict[str, str]:
    root = Path(artifact_dir)
    defaults = {
        "manifest_path": "manifest.json",
        "bootstrap_discovery_path": "bootstrap_discovery.json",
        "axis_confirmation_path": "axis_confirmation.json",
        "formal_patch_draft_path": "formal_patch_draft.json",
        "formal_writeback_plan_path": "formal_writeback_plan.json",
        "material_card_draft_path": "material_card_draft.json",
        "material_bridge_mapping_draft_path": "material_bridge_mapping_draft.json",
        "material_quality_regression_draft_path": "material_quality_regression_draft.json",
        "source_candidate_review_path": "source_candidate_review.json",
        "source_seed_registry_path": "source_seed_registry.jsonl",
        "crawl_seed_manifest_path": "crawl_seed_manifest.json",
        "source_text_evidence_manifest_path": "source_text_evidence_manifest.json",
        "source_text_evidence_results_path": "source_text_evidence_results.jsonl",
        "source_gold_alignment_summary_path": "source_gold_alignment_summary.json",
        "source_gold_alignment_results_path": "source_gold_alignment_results.jsonl",
        "material_quality_regression_results_path": "material_quality_regression_results.json",
        "truth_gold_regression_results_path": "truth_gold_regression_results.json",
        "truth_gold_split_manifest_path": "truth_gold_split_manifest.json",
        "agent_review_feedback_path": "agent_review_feedback_normalized.json",
        "system_alignment_findings_path": "system_alignment_findings.json",
    }
    resolved: dict[str, str] = {}
    for key, default_name in defaults.items():
        raw = paths.get(key)
        candidate = Path(raw) if raw is not None else root / default_name
        if candidate.exists():
            resolved[key.removesuffix("_path")] = str(candidate)
    return resolved


def build_new_leaf_formalization_packet(*, artifact_dir: str | Path, evidence_refs: dict[str, str]) -> dict[str, Any]:
    evidence = {key: _load_artifact(path) for key, path in evidence_refs.items()}
    manifest = evidence.get("manifest") or {}
    family_context = infer_family_context(manifest=manifest, evidence=evidence)
    missing = [
        key
        for key in [
            "manifest",
            "axis_confirmation",
            "formal_patch_draft",
            "agent_review_feedback",
            "truth_gold_regression_results",
        ]
        if key not in evidence_refs
    ]
    formal_targets = build_formal_target_candidates(evidence=evidence, evidence_refs=evidence_refs)
    feedback_summary = summarize_agent_feedback(evidence.get("agent_review_feedback") or {})
    material_summary = summarize_material_protocol(evidence=evidence)
    material_evidence_summary = summarize_material_evidence(evidence=evidence, material_summary=material_summary)
    question_summary = summarize_question_protocol(evidence=evidence)
    regression_summary = summarize_regression(evidence=evidence)
    blocking = build_blocking_issues(
        missing_evidence=missing,
        formal_targets=formal_targets,
        feedback_summary=feedback_summary,
        material_summary=material_summary,
    )
    recommended = recommended_next_action(blocking_issues=blocking, formal_targets=formal_targets)
    packet = {
        "packet_version": "v1",
        "packet_type": "new_leaf_formalization_packet",
        "status": "draft_review_packet",
        "formalized": False,
        "writeback_allowed": False,
        "requires_human_review": True,
        "requires_regression": True,
        "family_context": family_context,
        "evidence_refs": evidence_refs,
        "confirmed_user_decisions": {
            "axis_confirmation": summarize_axis_confirmation(evidence.get("axis_confirmation") or {}),
            "source_review": summarize_source_review(evidence.get("source_candidate_review") or {}),
            "agent_review_feedback": feedback_summary,
        },
        "formal_target_candidates": formal_targets,
        "material_evidence_summary": material_evidence_summary,
        "material_protocol_summary": material_summary,
        "question_protocol_summary": question_summary,
        "runtime_activation_summary": {
            "required": True,
            "available": False,
            "reason": "runtime_activation_plan has not been generated for this packet yet.",
        },
        "regression_summary": regression_summary,
        "human_feedback_summary": feedback_summary,
        "missing_evidence": missing,
        "blocking_issues": blocking,
        "recommended_next_action": recommended,
        "limits": [
            "This packet is a formalization review packet, not writeback.",
            "It does not formalize material_card_draft or source seeds.",
            "It does not change card_specs, prompt assets, validator contracts, runtime mapping, or generation code.",
        ],
    }
    assert_packet_boundaries(packet)
    return packet


def infer_family_context(*, manifest: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    formal_patch = evidence.get("formal_patch_draft") or {}
    material_card = evidence.get("material_card_draft") or {}
    material_binding = material_card.get("family_binding") or {}
    return {
        "mother_family_id": manifest.get("mother_family_id") or material_binding.get("mother_family_id") or formal_patch.get("proto_family") or "unknown",
        "child_family_id": manifest.get("child_family_id") or material_binding.get("child_family_id") or formal_patch.get("proto_child_family"),
        "leaf_label": manifest.get("leaf_label") or material_binding.get("leaf_label") or formal_patch.get("leaf_label") or "unknown",
        "business_subtype": material_binding.get("business_subtype") or manifest.get("child_family_id"),
        "question_focus": material_binding.get("question_focus") or manifest.get("mother_family_id"),
        "question_card_reference": material_binding.get("question_card_reference"),
    }


def build_formal_target_candidates(*, evidence: dict[str, Any], evidence_refs: dict[str, str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    formal_patch = evidence.get("formal_patch_draft") or {}
    for patch in formal_patch.get("target_patches") or []:
        target = str(patch.get("target") or "")
        if target not in FORMAL_TARGETS:
            continue
        candidates.append(
            {
                "target": target,
                "status": "candidate",
                "source_artifact": evidence_refs.get("formal_patch_draft", ""),
                "evidence_summary": f"{target} draft generated from proto-confirmed axis decisions.",
                "requires_writeback_plan": True,
                "requires_regression": True,
                "blocking_gaps": [],
            }
        )
    material_summary = summarize_material_protocol(evidence=evidence)
    if evidence.get("material_card_draft"):
        material_gaps = material_summary.get("blocking_gaps") or []
        material_status = "candidate" if material_summary.get("ready_for_material_card_review") else "blocked"
        candidates.append(
            {
                "target": "material_card",
                "status": material_status,
                "source_artifact": evidence_refs.get("material_card_draft", ""),
                "evidence_summary": "material_card_draft exists and is evaluated against material-line evidence. It remains draft-only.",
                "requires_writeback_plan": True,
                "requires_regression": True,
                "blocking_gaps": material_gaps,
            }
        )
    if evidence.get("material_bridge_mapping_draft"):
        candidates.append(
            {
                "target": "material_mapping",
                "status": "deferred",
                "source_artifact": evidence_refs.get("material_bridge_mapping_draft", ""),
                "evidence_summary": "material bridge mapping draft can inform runtime activation but is not formal mapping.",
                "requires_writeback_plan": True,
                "requires_regression": True,
                "blocking_gaps": ["runtime_activation_plan_required"],
            }
        )
    return candidates


def summarize_agent_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    items = feedback.get("normalized_feedback") or []
    high = [item for item in items if item.get("severity") == "high"]
    return {
        "available": bool(feedback),
        "status": feedback.get("status"),
        "feedback_count": len(items),
        "high_severity_count": len(high),
        "dimensions": [item.get("dimension") for item in items],
        "unresolved_high_severity": [item.get("dimension") for item in high],
        "writeback_allowed": bool(feedback.get("writeback_allowed")),
        "formalized": bool(feedback.get("formalized")),
    }


def summarize_material_protocol(*, evidence: dict[str, Any]) -> dict[str, Any]:
    crawl = evidence.get("crawl_seed_manifest") or {}
    seed_rows = evidence.get("source_seed_registry") or []
    material_card = evidence.get("material_card_draft") or {}
    source_text = evidence.get("source_text_evidence_manifest") or {}
    alignment = evidence.get("source_gold_alignment_summary") or {}
    quality = evidence.get("material_quality_regression_results") or {}
    source_text_available = bool(source_text.get("available_count"))
    alignment_available = bool(alignment.get("alignment_count"))
    quality_available = bool(quality)
    quality_status = quality.get("status")
    blocking_gaps: list[str] = []
    if not source_text_available:
        blocking_gaps.append("source_text_evidence_required")
    if not alignment_available:
        blocking_gaps.append("source_gold_alignment_required")
    if not quality_available:
        blocking_gaps.append("material_quality_regression_required")
    if quality_status == "blocked":
        blocking_gaps.append("material_quality_regression_blocked")
    if not quality.get("ready_for_material_card_formalization", False):
        blocking_gaps.append("material_card_formalization_not_allowed")
    return {
        "material_card_draft_available": bool(material_card),
        "material_card_status": material_card.get("status") or material_card.get("draft_status"),
        "source_seed_count": len(seed_rows) if isinstance(seed_rows, list) else 0,
        "verified_source_available": False,
        "crawl_allowed": bool(crawl.get("crawl_allowed")),
        "source_text_evidence_available": source_text_available,
        "source_text_evidence_count": source_text.get("result_count", 0),
        "source_gold_alignment_available": alignment_available,
        "source_gold_alignment_count": alignment.get("alignment_count", 0),
        "material_quality_regression_available": quality_available,
        "material_quality_regression_status": quality_status,
        "ready_for_material_card_review": bool(source_text_available and alignment_available and quality_available and quality_status != "blocked"),
        "ready_for_material_card_formalization": False,
        "verified_original_source_count": 0,
        "blocking_gaps": sorted(set(blocking_gaps + ["verified_original_source_required_before_original_source_claim"])),
    }


def summarize_material_evidence(*, evidence: dict[str, Any], material_summary: dict[str, Any]) -> dict[str, Any]:
    source_text = evidence.get("source_text_evidence_manifest") or {}
    alignment = evidence.get("source_gold_alignment_summary") or {}
    quality = evidence.get("material_quality_regression_results") or {}
    alignment_needs_review = bool(alignment.get("needs_human_review_count"))
    quality_needs_review = bool(quality.get("requires_human_review", True))
    blocking_issues = list(material_summary.get("blocking_gaps") or [])
    if source_text.get("manual_required_count"):
        blocking_issues.append("source_text_manual_required")
    if alignment_needs_review:
        blocking_issues.append("source_gold_alignment_review_required")
    if quality_needs_review:
        blocking_issues.append("material_quality_review_required")
    return {
        "source_text_evidence_status": source_text.get("status") or ("missing" if not source_text else "unknown"),
        "source_text_evidence_count": source_text.get("result_count", 0),
        "source_text_available_count": source_text.get("available_count", 0),
        "source_text_manual_required_count": source_text.get("manual_required_count", 0),
        "source_gold_alignment_status": alignment.get("status") or ("missing" if not alignment else "unknown"),
        "source_gold_alignment_count": alignment.get("alignment_count", 0),
        "source_gold_alignment_needs_human_review_count": alignment.get("needs_human_review_count", 0),
        "material_quality_regression_status": quality.get("status") or ("missing" if not quality else "unknown"),
        "verified_original_source_count": 0,
        "requires_source_review": True,
        "requires_alignment_review": alignment_needs_review or not alignment,
        "requires_material_quality_review": quality_needs_review,
        "ready_for_material_card_review": bool(material_summary.get("ready_for_material_card_review")),
        "ready_for_material_card_formalization": False,
        "blocking_issues": sorted(set(blocking_issues)),
        "limits": [
            "Material evidence summary is evidence only; it is not material_card approval.",
            "Source candidates and similar materials remain unverified.",
            "Material-card formalization is not allowed from this packet.",
        ],
    }


def summarize_question_protocol(*, evidence: dict[str, Any]) -> dict[str, Any]:
    formal_patch = evidence.get("formal_patch_draft") or {}
    axis = evidence.get("axis_confirmation") or {}
    return {
        "axis_confirmation_available": bool(axis),
        "proto_confirmed_count": len([item for item in axis.get("axis_decisions") or [] if item.get("status") == "proto_confirmed"]),
        "formal_patch_draft_available": bool(formal_patch),
        "target_patch_count": len(formal_patch.get("target_patches") or []),
        "writeback_plan_available": bool(evidence.get("formal_writeback_plan")),
    }


def summarize_regression(*, evidence: dict[str, Any]) -> dict[str, Any]:
    regression = evidence.get("truth_gold_regression_results") or {}
    split = evidence.get("truth_gold_split_manifest") or {}
    return {
        "truth_gold_regression_available": bool(regression),
        "gold_source": regression.get("gold_source"),
        "fit_type": (regression.get("summary") or {}).get("fit_type"),
        "ready_for_formalization": bool((regression.get("summary") or {}).get("ready_for_formalization")),
        "split_manifest_available": bool(split),
        "insurance_holdout_available": bool((split.get("splits") or {}).get("insurance_holdout")),
    }


def summarize_axis_confirmation(axis: dict[str, Any]) -> dict[str, Any]:
    decisions = axis.get("axis_decisions") or []
    return {
        "available": bool(axis),
        "proto_confirmed_count": len([item for item in decisions if item.get("status") == "proto_confirmed"]),
        "decision_count": len(decisions),
    }


def summarize_source_review(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": bool(review),
        "accepted_count": review.get("accepted_count"),
        "rejected_count": review.get("rejected_count"),
        "verified_original_source_count": review.get("verified_original_source_count", 0),
    }


def build_blocking_issues(
    *,
    missing_evidence: list[str],
    formal_targets: list[dict[str, Any]],
    feedback_summary: dict[str, Any],
    material_summary: dict[str, Any],
) -> list[str]:
    issues = [f"missing_evidence:{item}" for item in missing_evidence]
    for target in formal_targets:
        if target.get("status") == "blocked":
            issues.extend(target.get("blocking_gaps") or [])
    if feedback_summary.get("high_severity_count"):
        issues.append("unresolved_high_severity_user_feedback")
    if material_summary.get("source_seed_count") and not material_summary.get("verified_source_available"):
        issues.append("source_seed_is_not_verified_source")
    return sorted(set(issues))


def recommended_next_action(*, blocking_issues: list[str], formal_targets: list[dict[str, Any]]) -> str:
    if any(issue.startswith("missing_evidence") for issue in blocking_issues):
        return "blocked"
    if blocking_issues:
        return "needs_human_review"
    if formal_targets:
        return "runtime_activation_plan"
    return "blocked"


def assert_packet_boundaries(packet: dict[str, Any]) -> None:
    if packet.get("writeback_allowed") is True:
        raise ValueError("formalization packet cannot allow writeback")
    if packet.get("formalized") is True:
        raise ValueError("formalization packet cannot be formalized")
    text = json.dumps(packet, ensure_ascii=False).lower()
    if '"verified": true' in text or '"verified_original_source": true' in text:
        raise ValueError("formalization packet cannot mark source seeds as verified")


def render_new_leaf_formalization_packet_report(packet: dict[str, Any]) -> str:
    lines = [
        "# New Leaf Formalization Packet",
        "",
        "> 正式化送审包是 draft/evidence，不是写回执行器。",
        "",
        f"- status: `{packet.get('status')}`",
        f"- family_context: `{packet.get('family_context')}`",
        f"- formalized: `{bool(packet.get('formalized'))}`",
        f"- writeback_allowed: `{bool(packet.get('writeback_allowed'))}`",
        f"- recommended_next_action: `{packet.get('recommended_next_action')}`",
        "",
        "## Formal Target Candidates",
        "",
    ]
    targets = packet.get("formal_target_candidates") or []
    if not targets:
        lines.append("- none")
    else:
        lines.append("| target | status | source | blocking_gaps |")
        lines.append("|---|---|---|---|")
        for target in targets:
            lines.append(
                f"| `{target.get('target')}` | `{target.get('status')}` | `{target.get('source_artifact')}` | {', '.join(target.get('blocking_gaps') or [])} |"
            )
    lines.extend(["", "## Blocking Issues", ""])
    issues = packet.get("blocking_issues") or []
    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(f"- {issue}")
    return "\n".join(lines) + "\n"


def _load_artifact(path: str) -> Any:
    p = Path(path)
    if p.suffix.lower() == ".jsonl":
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return p.read_text(encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a new-leaf formalization review packet.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--agent-review-feedback")
    parser.add_argument("--formal-patch-draft")
    parser.add_argument("--material-card-draft")
    parser.add_argument("--source-seed-registry")
    parser.add_argument("--axis-confirmation")
    parser.add_argument("--source-candidate-review")
    parser.add_argument("--crawl-seed-manifest")
    parser.add_argument("--source-text-evidence-manifest")
    parser.add_argument("--source-text-evidence-results")
    parser.add_argument("--source-gold-alignment-summary")
    parser.add_argument("--source-gold-alignment-results")
    parser.add_argument("--material-quality-regression-results")
    parser.add_argument("--truth-gold-regression-results")
    parser.add_argument("--truth-gold-split-manifest")
    parser.add_argument("--material-bridge-mapping-draft")
    parser.add_argument("--material-quality-regression-draft")
    parser.add_argument("--system-alignment-findings")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    artifacts = run_new_leaf_formalization_packet(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        agent_review_feedback_path=args.agent_review_feedback,
        formal_patch_draft_path=args.formal_patch_draft,
        material_card_draft_path=args.material_card_draft,
        source_seed_registry_path=args.source_seed_registry,
        axis_confirmation_path=args.axis_confirmation,
        source_candidate_review_path=args.source_candidate_review,
        crawl_seed_manifest_path=args.crawl_seed_manifest,
        source_text_evidence_manifest_path=args.source_text_evidence_manifest,
        source_text_evidence_results_path=args.source_text_evidence_results,
        source_gold_alignment_summary_path=args.source_gold_alignment_summary,
        source_gold_alignment_results_path=args.source_gold_alignment_results,
        material_quality_regression_results_path=args.material_quality_regression_results,
        truth_gold_regression_results_path=args.truth_gold_regression_results,
        truth_gold_split_manifest_path=args.truth_gold_split_manifest,
        material_bridge_mapping_draft_path=args.material_bridge_mapping_draft,
        material_quality_regression_draft_path=args.material_quality_regression_draft,
        system_alignment_findings_path=args.system_alignment_findings,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

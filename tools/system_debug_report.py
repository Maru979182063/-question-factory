from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.system_debug_artifact_index import artifacts_for_chain, latest_artifact_for_chain
from tools.system_debug_adapter_resolution import (
    adapter_coverage_summary,
    adapters_by_chain,
    resolve_adapters,
)


FEATURE_KEYS = [
    "has_contract",
    "has_checkpoint",
    "has_retry",
    "has_resume",
    "has_state_file",
    "has_stage_report",
    "has_diff_or_backtest",
    "has_patch_or_bundle",
    "has_human_review_gate",
]


def build_system_debug_report(
    *,
    manifest: dict[str, Any],
    artifact_index: dict[str, Any],
    chain_registry: list[dict[str, Any]],
    adapter_registry: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    chain_reports = []
    blocked_points: list[dict[str, Any]] = []
    missing_contracts: list[dict[str, Any]] = []
    for chain in chain_registry:
        chain_report = summarize_chain(chain=chain, artifact_index=artifact_index)
        chain_reports.append(chain_report)
        if chain_report["current_status"] == "blocked":
            blocked_points.append(
                {
                    "chain_name": chain_report["chain_name"],
                    "blocked_by": chain_report.get("blocked_by") or [],
                    "status_reason": chain_report.get("status_reason"),
                }
            )
        if chain_report["artifact_count"] == 0:
            missing_contracts.append(
                {
                    "chain_name": chain_report["chain_name"],
                    "missing": "no_artifact_discovered",
                    "expected_outputs": chain_report.get("output_artifacts") or [],
                }
            )
    adapter_resolutions = resolve_adapters(
        adapters=adapter_registry or [],
        artifact_index=artifact_index,
        chain_reports=chain_reports,
    )
    adapter_by_chain = adapters_by_chain(adapter_resolutions)
    for chain_report in chain_reports:
        attached = adapter_by_chain.get(chain_report["chain_name"]) or {"inbound": [], "outbound": []}
        inbound = attached.get("inbound") or []
        outbound = attached.get("outbound") or []
        chain_report["inbound_adapters"] = inbound
        chain_report["outbound_adapters"] = outbound
        chain_report["ready_to_connect"] = (
            chain_report["current_status"] != "registered_only"
            and any(adapter.get("ready_to_connect") for adapter in inbound + outbound)
        )
        chain_report["blocked_by_missing_fields"] = [
            {
                "adapter_name": adapter.get("adapter_name"),
                "missing_required_fields": adapter.get("missing_required_fields") or [],
                "degrade_path": adapter.get("degrade_path"),
            }
            for adapter in inbound + outbound
            if adapter.get("missing_required_fields")
        ]
        chain_report["manual_bridge_required"] = any(adapter.get("manual_bridge_required") for adapter in inbound + outbound)
    adapter_summary = adapter_coverage_summary(adapter_resolutions)
    return {
        "report_version": "v1",
        "system_debug_run_id": manifest.get("system_debug_run_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "auto_execute": False,
        "llm_calls_made": False,
        "writeback_allowed": False,
        "summary": {
            "registered_chain_count": len(chain_reports),
            "discovered_artifact_count": artifact_index.get("artifact_count") or 0,
            "available_chain_count": sum(1 for item in chain_reports if item["current_status"] in {"available", "complete"}),
            "blocked_chain_count": sum(1 for item in chain_reports if item["current_status"] == "blocked"),
            "registered_only_chain_count": sum(1 for item in chain_reports if item["current_status"] == "registered_only"),
        },
        "adapter_coverage": adapter_summary,
        "adapter_status_matrix": adapter_resolutions,
        "explicit_adapters": [item for item in adapter_resolutions if item.get("contract_status") == "explicit"],
        "inferred_adapters": [item for item in adapter_resolutions if item.get("contract_status") == "inferred"],
        "manual_only_adapters": [item for item in adapter_resolutions if item.get("contract_status") == "manual_only"],
        "manual_only_connection_list": [
            item.get("adapter_name")
            for item in adapter_resolutions
            if item.get("contract_status") == "manual_only"
        ],
        "missing_required_fields": [
            {
                "adapter_name": item.get("adapter_name"),
                "missing_required_fields": item.get("missing_required_fields") or [],
                "degrade_path": item.get("degrade_path"),
            }
            for item in adapter_resolutions
            if item.get("missing_required_fields")
        ],
        "chains": chain_reports,
        "dependency_edges": manifest.get("dependency_edges") or [],
        "blocked_points": blocked_points,
        "missing_adapters_or_contracts": missing_contracts,
        "next_minimal_patches": build_next_minimal_patches(chain_reports, adapter_resolutions),
        "limits": [
            "This report aggregates existing debug artifacts only.",
            "It does not claim manual chaining is automatic orchestration.",
            "It does not execute LLM calls, generation, distillation, crawling, promotion, or writeback.",
        ],
    }


def summarize_chain(*, chain: dict[str, Any], artifact_index: dict[str, Any]) -> dict[str, Any]:
    name = str(chain.get("chain_name"))
    artifacts = artifacts_for_chain(artifact_index, name)
    latest = latest_artifact_for_chain(artifact_index, name)
    status, reason = infer_chain_status(chain=chain, artifacts=artifacts)
    return {
        "chain_name": name,
        "category": chain.get("category"),
        "maturity_level": chain.get("maturity_level"),
        "current_status": status,
        "status_reason": reason,
        **{key: bool(chain.get(key)) for key in FEATURE_KEYS},
        "input_artifacts": list(chain.get("input_artifacts") or []),
        "output_artifacts": list(chain.get("output_artifacts") or []),
        "dependency_on": list(chain.get("dependency_on") or []),
        "blocked_by": list(chain.get("blocked_by") or []),
        "artifact_count": len(artifacts),
        "latest_artifact": latest,
        "artifacts": artifacts,
        "notes": chain.get("notes") or "",
    }


def infer_chain_status(*, chain: dict[str, Any], artifacts: list[dict[str, Any]]) -> tuple[str, str]:
    if not artifacts:
        return "registered_only", "chain_registered_but_no_artifact_discovered"
    for artifact in artifacts:
        hint = artifact.get("status_hint") or {}
        if hint.get("blocked") is True:
            return "blocked", f"blocked artifact: {artifact.get('relative_path')}"
        status = str(hint.get("status") or "").lower()
        if status in {"blocked", "failed", "provider_error", "validation_error"}:
            return "blocked", f"{status} artifact: {artifact.get('relative_path')}"
        counts = hint.get("stage_status_counts") or hint.get("status_counts") or {}
        if any(key in counts for key in ("provider_error", "validation_error", "blocked", "failed")):
            return "blocked", f"stage error in artifact: {artifact.get('relative_path')}"
    if any((artifact.get("status_hint") or {}).get("pipeline_complete") is True for artifact in artifacts):
        return "complete", "pipeline_complete artifact discovered"
    return "available", "one_or_more_artifacts_discovered"


def build_next_minimal_patches(
    chain_reports: list[dict[str, Any]],
    adapter_resolutions: list[dict[str, Any]] | None = None,
) -> list[str]:
    suggestions: list[str] = []
    adapter_resolutions = adapter_resolutions or []
    if any(item.get("contract_status") == "manual_only" for item in adapter_resolutions):
        suggestions.append("Formalize the highest-value manual-only adapter before attempting any master execution plane.")
    if any(item.get("missing_required_fields") for item in adapter_resolutions):
        suggestions.append("Add adapter field drilldown for missing required fields and manual-fill fallback guidance.")
    if any(item["current_status"] == "blocked" for item in chain_reports):
        suggestions.append("Add a read-only blocked-chain drilldown that links each blocked chain to its latest error artifact.")
    if any(item["current_status"] == "registered_only" for item in chain_reports):
        suggestions.append("Add chain adapter documentation for registered-only chains so their artifacts can be discovered consistently.")
    if not suggestions:
        suggestions.append("Add a correlation-id convention so independently generated chain artifacts can be grouped into the same system debug run.")
    suggestions.append("Keep this control plane read-only until chain adapters and human review gates are stable.")
    return suggestions[:3]


def render_system_debug_report_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    adapter_coverage = report.get("adapter_coverage") or {}
    lines = [
        "# System Debug Control Plane Report",
        "",
        f"- system_debug_run_id: `{report.get('system_debug_run_id')}`",
        f"- read_only: `{bool(report.get('read_only'))}`",
        f"- auto_execute: `{bool(report.get('auto_execute'))}`",
        f"- llm_calls_made: `{bool(report.get('llm_calls_made'))}`",
        f"- writeback_allowed: `{bool(report.get('writeback_allowed'))}`",
        f"- registered_chain_count: `{summary.get('registered_chain_count')}`",
        f"- discovered_artifact_count: `{summary.get('discovered_artifact_count')}`",
        f"- blocked_chain_count: `{summary.get('blocked_chain_count')}`",
        f"- adapter_count: `{adapter_coverage.get('adapter_count', 0)}`",
        f"- ready_to_connect_adapters: `{adapter_coverage.get('ready_to_connect_count', 0)}`",
        f"- manual_bridge_required_adapters: `{adapter_coverage.get('manual_bridge_required_count', 0)}`",
        "",
        "## Chains",
        "",
        "| chain | category | maturity | status | artifacts | ready_to_connect | manual bridge | checkpoint | retry | resume | diff/report | patch/bundle | human gate |",
        "|---|---|---|---|---:|---|---|---|---|---|---|---|---|",
    ]
    for chain in report.get("chains") or []:
        lines.append(
            "| {chain} | {category} | {maturity} | {status} | {count} | {ready} | {manual} | {checkpoint} | {retry} | {resume} | {diff} | {bundle} | {human} |".format(
                chain=chain.get("chain_name"),
                category=chain.get("category"),
                maturity=chain.get("maturity_level"),
                status=chain.get("current_status"),
                count=chain.get("artifact_count"),
                ready=_yesno(chain.get("ready_to_connect")),
                manual=_yesno(chain.get("manual_bridge_required")),
                checkpoint=_yesno(chain.get("has_checkpoint")),
                retry=_yesno(chain.get("has_retry")),
                resume=_yesno(chain.get("has_resume")),
                diff=_yesno(chain.get("has_diff_or_backtest")),
                bundle=_yesno(chain.get("has_patch_or_bundle")),
                human=_yesno(chain.get("has_human_review_gate")),
            )
        )
    lines.extend(["", "## Adapter Coverage", ""])
    lines.append(f"- contract_status_counts: `{adapter_coverage.get('contract_status_counts') or {}}`")
    lines.append(f"- resolution_status_counts: `{adapter_coverage.get('resolution_status_counts') or {}}`")
    lines.extend(["", "## Adapter Status Matrix", ""])
    lines.append("| adapter | source -> target | contract | status | ready | manual | missing fields | degrade path |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for adapter in report.get("adapter_status_matrix") or []:
        missing = ", ".join(adapter.get("missing_required_fields") or [])
        lines.append(
            "| {name} | {source} -> {target} | {contract} | {status} | {ready} | {manual} | {missing} | {degrade} |".format(
                name=adapter.get("adapter_name"),
                source=adapter.get("source_chain"),
                target=adapter.get("target_chain"),
                contract=adapter.get("contract_status"),
                status=adapter.get("resolution_status"),
                ready=_yesno(adapter.get("ready_to_connect")),
                manual=_yesno(adapter.get("manual_bridge_required")),
                missing=missing or "none",
                degrade=adapter.get("degrade_path") or "",
            )
        )
    lines.extend(["", "## Manual-Only Connections", ""])
    manual_only = report.get("manual_only_connection_list") or []
    if not manual_only:
        lines.append("- none")
    else:
        for name in manual_only:
            lines.append(f"- `{name}`")
    lines.extend(["", "## Missing Required Fields", ""])
    missing_required = report.get("missing_required_fields") or []
    if not missing_required:
        lines.append("- none detected")
    else:
        for item in missing_required:
            fields = ", ".join(item.get("missing_required_fields") or [])
            lines.append(f"- `{item.get('adapter_name')}`: {fields}; degrade_path={item.get('degrade_path')}")
    lines.extend(["", "## Dependency Edges", ""])
    for edge in report.get("dependency_edges") or []:
        lines.append(f"- `{edge.get('from')}` -> `{edge.get('to')}` ({edge.get('dependency_type')})")
    lines.extend(["", "## Blocked Points", ""])
    blocked = report.get("blocked_points") or []
    if not blocked:
        lines.append("- none detected from indexed artifacts")
    else:
        for item in blocked:
            lines.append(f"- `{item.get('chain_name')}`: {item.get('status_reason')}")
    lines.extend(["", "## Missing Adapters Or Contracts", ""])
    missing = report.get("missing_adapters_or_contracts") or []
    if not missing:
        lines.append("- none detected")
    else:
        for item in missing:
            lines.append(f"- `{item.get('chain_name')}`: {item.get('missing')}")
    lines.extend(["", "## Next Minimal Patches", ""])
    for item in report.get("next_minimal_patches") or []:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is a read-only control plane report.",
            "- It does not execute LLM calls, generation, distillation, crawling, promotion, or writeback.",
            "- It does not claim manually connected chains are automatic orchestration.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_system_debug_report_files(*, output_dir: str | Path, report: dict[str, Any]) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "system_debug_report.json"
    md_path = output_path / "system_debug_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_system_debug_report_markdown(report), encoding="utf-8")
    return {"system_debug_report": str(json_path), "system_debug_report_md": str(md_path)}


def _yesno(value: Any) -> str:
    return "yes" if bool(value) else "no"

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.material_protocol_split_state import STAGE_ORDER


def build_pipeline_stage_report(*, state: dict[str, Any]) -> dict[str, Any]:
    stages = state.get("stages") or {}
    rows = []
    for key, _ in STAGE_ORDER:
        item = stages.get(key) or {}
        rows.append(
            {
                "stage": key,
                "status": item.get("status") or "pending",
                "output_path": item.get("output_path"),
                "error_summary": item.get("error_summary") or "",
                "retry_count": int(item.get("retry_count") or 0),
                "duration_seconds": float(item.get("duration_seconds") or 0.0),
            }
        )
    counts = Counter(row["status"] for row in rows)
    return {
        "report_version": "v1",
        "mode": state.get("mode"),
        "status_counts": dict(counts),
        "stages": rows,
        "pipeline_complete": all(row["status"] in {"success", "skipped"} for row in rows),
        "blocked": any(row["status"] in {"blocked", "provider_error", "validation_error"} for row in rows),
    }


def render_pipeline_stage_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Material Protocol Split Pipeline Stage Report",
        "",
        f"- mode: `{report.get('mode')}`",
        f"- pipeline_complete: `{bool(report.get('pipeline_complete'))}`",
        f"- blocked: `{bool(report.get('blocked'))}`",
        f"- status_counts: `{report.get('status_counts') or {}}`",
        "",
        "| stage | status | retry_count | duration_seconds | output_path | error |",
        "|---|---|---:|---:|---|---|",
    ]
    for stage in report.get("stages") or []:
        lines.append(
            "| {stage} | {status} | {retry} | {duration:.3f} | {path} | {error} |".format(
                stage=stage.get("stage") or "",
                status=stage.get("status") or "",
                retry=int(stage.get("retry_count") or 0),
                duration=float(stage.get("duration_seconds") or 0.0),
                path=stage.get("output_path") or "",
                error=(stage.get("error_summary") or "").replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This report only tracks draft-stage execution.",
            "- It does not approve source verification, crawling, material ingestion, material promotion, card_specs writeback, runtime mapping writeback, prompt writeback, validator writeback, or generation-chain changes.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_pipeline_stage_reports(*, output_dir: str | Path, state: dict[str, Any]) -> dict[str, str]:
    output_path = Path(output_dir)
    report = build_pipeline_stage_report(state=state)
    json_path = output_path / "pipeline_stage_report.json"
    md_path = output_path / "pipeline_stage_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_pipeline_stage_report_markdown(report), encoding="utf-8")
    return {"pipeline_stage_report": str(json_path), "pipeline_stage_report_md": str(md_path)}

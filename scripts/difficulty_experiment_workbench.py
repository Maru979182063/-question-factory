from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE_ORDER = ["prepare", "validate", "fit", "analyze", "report"]


def main() -> None:
    args = _parse_args()
    config_path = _resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))

    if args.stage == "all":
        stages = DEFAULT_STAGE_ORDER
    else:
        stages = [args.stage]

    results = []
    for stage in stages:
        if stage == "status":
            results.append(_status(config))
        elif stage == "validate":
            results.append(_validate(config, fix_sample_ids=args.fix_sample_ids))
        elif stage == "new-experiment":
            results.append(_new_experiment(config, args))
        elif stage == "candidate-diff":
            results.append(_candidate_diff(config, dry_run=args.dry_run))
        else:
            results.append(_run_stage(config, stage, dry_run=args.dry_run))

    print(json.dumps({"experiment_id": config.get("experiment_id"), "results": results}, ensure_ascii=False, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or validate a config-driven leaf difficulty experiment.")
    parser.add_argument("--config", required=True, help="Path to difficulty experiment JSON config or template.")
    parser.add_argument(
        "--stage",
        default="status",
        choices=["status", "prepare", "validate", "fit", "analyze", "report", "candidate-diff", "new-experiment", "all"],
        help="Experiment stage to run.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing.")
    parser.add_argument(
        "--fix-sample-ids",
        action="store_true",
        help="During validate, canonicalize output sample_id values from matching input rows.",
    )
    parser.add_argument("--new-config", help="Output path for --stage new-experiment.")
    parser.add_argument("--experiment-id", help="Experiment id for --stage new-experiment.")
    parser.add_argument("--family", help="Family for --stage new-experiment.")
    parser.add_argument("--leaf", help="Leaf id for --stage new-experiment.")
    parser.add_argument("--leaf-display-name", help="Human-readable leaf name for --stage new-experiment.")
    return parser.parse_args()


def _status(config: dict[str, Any]) -> dict[str, Any]:
    expected = [_path_status(path) for path in config.get("expected_outputs", [])]
    labels = []
    for item in config.get("label_outputs", []):
        labels.append(
            {
                "input": _path_status(item["input"]),
                "output": _path_status(item["output"]),
            }
        )
    return {
        "stage": "status",
        "family": config.get("family"),
        "leaf": config.get("leaf"),
        "status": config.get("status"),
        "expected_outputs": expected,
        "label_files": labels,
    }


def _validate(config: dict[str, Any], *, fix_sample_ids: bool) -> dict[str, Any]:
    problems = []
    summaries = []
    for item in config.get("label_outputs", []):
        input_path = _resolve_path(item["input"])
        output_path = _resolve_path(item["output"])
        required_keys = item.get("required_keys", [])

        if not input_path.exists():
            problems.append({"type": "missing_input", "path": str(input_path)})
            continue
        if not output_path.exists():
            problems.append({"type": "missing_output", "path": str(output_path)})
            continue

        input_rows = _read_jsonl(input_path)
        output_rows = _read_jsonl(output_path)
        if len(input_rows) != len(output_rows):
            problems.append(
                {
                    "type": "row_count_mismatch",
                    "input": str(input_path),
                    "output": str(output_path),
                    "input_rows": len(input_rows),
                    "output_rows": len(output_rows),
                }
            )
            continue

        fixed = 0
        row_errors = []
        for idx, (input_row, output_row) in enumerate(zip(input_rows, output_rows, strict=True), start=1):
            if fix_sample_ids and output_row.get("sample_id") != input_row.get("sample_id"):
                output_row["sample_id"] = input_row.get("sample_id")
                fixed += 1
            for key in required_keys:
                if key not in output_row:
                    row_errors.append({"row": idx, "sample_id": output_row.get("sample_id"), "missing_key": key})
        if fixed:
            _write_jsonl(output_path, output_rows)
        if row_errors:
            problems.append({"type": "schema_errors", "output": str(output_path), "errors": row_errors[:20], "count": len(row_errors)})
        summaries.append(
            {
                "output": str(output_path.relative_to(ROOT) if output_path.is_relative_to(ROOT) else output_path),
                "rows": len(output_rows),
                "fixed_sample_ids": fixed,
                "schema_errors": len(row_errors),
            }
        )

    return {"stage": "validate", "ok": not problems, "summaries": summaries, "problems": problems}


def _new_experiment(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not args.new_config:
        return {"stage": "new-experiment", "ok": False, "error": "--new-config is required"}
    experiment_id = args.experiment_id or config.get("experiment_id")
    if not experiment_id:
        return {"stage": "new-experiment", "ok": False, "error": "--experiment-id is required"}

    new_config = dict(config)
    new_config["experiment_id"] = experiment_id
    if args.family:
        new_config["family"] = args.family
    if args.leaf:
        new_config["leaf"] = args.leaf
    if args.leaf_display_name:
        new_config["leaf_display_name"] = args.leaf_display_name
    new_config["status"] = "candidate_only"

    replacements = {
        "<experiment_id>": experiment_id,
        "family_leaf_experiment_id": experiment_id,
    }
    if args.family:
        replacements["family_name"] = args.family
    if args.leaf:
        replacements["leaf_name"] = args.leaf
    if args.leaf_display_name:
        replacements["叶族中文名"] = args.leaf_display_name

    new_config = _replace_placeholders(new_config, replacements)
    out_path = _resolve_path(args.new_config)
    if out_path.exists():
        return {"stage": "new-experiment", "ok": False, "error": f"Refusing to overwrite existing file: {out_path}"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(new_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"stage": "new-experiment", "ok": True, "output": str(out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path)}


def _candidate_diff(config: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    out_dir = ROOT / "reports" / "difficulty_control" / "candidate_diffs"
    out_path = out_dir / f"{config.get('experiment_id', 'unknown_experiment')}_candidate_diff.md"
    candidate_outputs = config.get("candidate_outputs") or []
    lines = [
        f"# Candidate Difficulty Patch: {config.get('experiment_id')}",
        "",
        "This packet is intentionally non-mutating. It summarizes candidate assets and intended consumption points, but does not write to master config.",
        "",
        "## Status",
        "",
        f"- family: `{config.get('family')}`",
        f"- leaf: `{config.get('leaf')}`",
        f"- status: `{config.get('status')}`",
        "",
        "## Candidate Outputs",
        "",
        "| type | path | exists |",
        "|---|---|---:|",
    ]
    for item in candidate_outputs:
        path = _resolve_path(item.get("path", ""))
        lines.append(f"| `{item.get('type', '')}` | `{item.get('path', '')}` | `{str(path.exists()).lower()}` |")
    lines.extend(
        [
            "",
            "## Consumption Targets",
            "",
        ]
    )
    for target in config.get("consumption_targets") or []:
        lines.append(f"- `{target}`")
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            "```json",
            json.dumps(config.get("promotion_gate") or {}, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Guardrails",
            "",
            "- Do not auto-write this candidate into master configs.",
            "- Do not promote unless the promotion gate is met.",
            "- Do not mechanically copy this leaf axis to other leaves.",
            "- Human review is required before any production-facing merge.",
            "",
        ]
    )
    if dry_run:
        return {"stage": "candidate-diff", "ok": True, "dry_run": True, "would_write": str(out_path.relative_to(ROOT))}
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {"stage": "candidate-diff", "ok": True, "output": str(out_path.relative_to(ROOT))}


def _run_stage(config: dict[str, Any], stage: str, *, dry_run: bool) -> dict[str, Any]:
    stage_config = (config.get("stages") or {}).get(stage)
    if not stage_config:
        return {"stage": stage, "ok": False, "error": f"Stage not configured: {stage}"}
    command = list(stage_config.get("command") or [])
    if not command:
        return {"stage": stage, "ok": False, "error": "Empty command"}
    if dry_run:
        return {"stage": stage, "ok": True, "dry_run": True, "command": command}
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "stage": stage,
        "ok": completed.returncode == 0,
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
    }


def _path_status(path_value: str) -> dict[str, Any]:
    path = _resolve_path(path_value)
    return {
        "path": str(path.relative_to(ROOT) if path.exists() and path.is_relative_to(ROOT) else path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
    }


def _resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT / path


def _replace_placeholders(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        out = value
        for source, target in replacements.items():
            out = out.replace(source, target)
        return out
    if isinstance(value, list):
        return [_replace_placeholders(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_placeholders(item, replacements) for key, item in value.items()}
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _tail(value: str, *, max_chars: int = 1400) -> str:
    value = value.strip()
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}, ensure_ascii=False, indent=2))
        sys.exit(1)

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _render_axis_diff(axis_diff: dict) -> list[str]:
    lines: list[str] = []
    for axis_name, payload in sorted(axis_diff.items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    axis_name,
                    str(payload.get("target")),
                    str(payload.get("projection")),
                    str(payload.get("actual")),
                    str(payload.get("gold")),
                    str(payload.get("actual_minus_target")),
                    str(payload.get("actual_minus_gold")),
                ]
            )
            + " |"
        )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Render difficulty diff report as markdown.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "reports" / "difficulty_control" / "sentence_fill_backtest.json"),
        help="Backtest JSON path.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "difficulty_control" / "sentence_fill_backtest.md"),
        help="Markdown output path.",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    lines = [
        "# sentence_fill difficulty diff report",
        "",
        f"- case_count: {payload.get('case_count', 0)}",
        "",
    ]

    for result in payload.get("results", []):
        row = result.get("report_row") or {}
        lines.extend(
            [
                f"## {result.get('case_id', 'unknown')}",
                "",
                f"- target_difficulty: {row.get('target_difficulty')}",
                f"- actual_difficulty: {row.get('actual_difficulty')}",
                f"- gold_difficulty: {row.get('gold_difficulty')}",
                f"- fit_result: {row.get('fit_result')}",
                f"- validator_status: {row.get('validator_status')}",
                f"- promotion_recommendation: {row.get('promotion_recommendation')}",
                "",
                "### axis diff",
                "",
                "| axis | target | projection | actual | gold | actual-target | actual-gold |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                *_render_axis_diff(row.get("axis_diff") or {}),
                "",
                "### patch candidates",
                "",
            ]
        )
        patch_candidates = row.get("patch_candidates") or []
        if not patch_candidates:
            lines.append("- none")
        else:
            for patch in patch_candidates:
                lines.append(
                    f"- `{patch.get('patch_target')}` / `{patch.get('patch_scope')}`: {patch.get('title')}"
                )
        lines.append("")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"difficulty markdown report written to: {output_path}")


if __name__ == "__main__":
    main()

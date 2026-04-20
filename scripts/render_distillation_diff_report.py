from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPT_SERVICE_ROOT = ROOT / "prompt_skeleton_service"
if str(PROMPT_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMPT_SERVICE_ROOT))

from app.schemas.distillation import DistillationDiffReport  # noqa: E402
from app.services.distillation_diff_service import DistillationDiffService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a sentence_fill distillation diff report as markdown.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "reports" / "distillation_runtime" / "round1" / "distillation_diff_report.json"),
        help="Diff report JSON path.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "distillation_runtime" / "round1" / "distillation_diff_report.md"),
        help="Markdown output path.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    report = DistillationDiffReport.model_validate_json(input_path.read_text(encoding="utf-8"))
    markdown = DistillationDiffService().render_markdown(report)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"markdown diff report written to: {output_path}")


if __name__ == "__main__":
    main()

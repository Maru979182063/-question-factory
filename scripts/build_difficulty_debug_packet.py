from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_sentence_fill_difficulty_backtest import _default_case_payload, evaluate_case

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a single difficulty debug packet.")
    parser.add_argument(
        "--input",
        default="",
        help="Optional JSON file containing a single case payload.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output path. Defaults to reports/difficulty_control/debug/<case_id>.json.",
    )
    args = parser.parse_args()

    if args.input:
        case = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        case = _default_case_payload()[0]

    packet = evaluate_case(case)
    output_path = (
        Path(args.output)
        if args.output
        else ROOT / "reports" / "difficulty_control" / "debug" / f"{packet['case_id']}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"difficulty debug packet written to: {output_path}")


if __name__ == "__main__":
    main()

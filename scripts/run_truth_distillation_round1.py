from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPT_SERVICE_ROOT = ROOT / "prompt_skeleton_service"
if str(PROMPT_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMPT_SERVICE_ROOT))

from app.schemas.distillation import DistillationInputPacket  # noqa: E402
from app.services.distillation_diff_service import DistillationDiffService  # noqa: E402
from app.services.distillation_promotion_service import DistillationPromotionService  # noqa: E402
from app.services.distillation_runtime_service import DistillationRuntimeService  # noqa: E402
from build_distillation_debug_packet import build_demo_packet  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the minimal offline truth distillation round1 loop.")
    parser.add_argument("--input", default="", help="Optional input packet JSON path.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports" / "distillation_runtime" / "round1"),
        help="Directory for result artifacts.",
    )
    args = parser.parse_args()

    if args.input:
        input_path = Path(args.input)
        packet = DistillationInputPacket.model_validate_json(input_path.read_text(encoding="utf-8"))
    else:
        packet = build_demo_packet()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime_service = DistillationRuntimeService()
    promotion_service = DistillationPromotionService()
    diff_service = DistillationDiffService()

    result = runtime_service.build_result_packet(packet)
    promotion_bundle = promotion_service.build_candidate_bundle(result)
    diff_report = diff_service.build_report(packet, result)

    packet_path = output_dir / "distillation_input_packet.json"
    result_path = output_dir / "distillation_result_packet.json"
    promotion_path = output_dir / "distillation_promotion_bundle.json"
    diff_path = output_dir / "distillation_diff_report.json"

    packet_path.write_text(json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    result_path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    promotion_path.write_text(
        json.dumps(promotion_bundle.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    diff_path.write_text(json.dumps(diff_report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"packet: {packet_path}")
    print(f"result: {result_path}")
    print(f"promotion: {promotion_path}")
    print(f"diff: {diff_path}")
    print(f"overall_fit_status: {result.overall_fit_status}")
    print(f"candidate_patch_count: {len(result.candidate_patches)}")


if __name__ == "__main__":
    main()

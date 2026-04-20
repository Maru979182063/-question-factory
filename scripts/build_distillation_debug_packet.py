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


def build_demo_packet() -> DistillationInputPacket:
    return DistillationInputPacket.model_validate(
        {
            "round_id": "round1_demo",
            "family_id": "sentence_fill",
            "truth_sample": {
                "sample_id": "truth.sentence_fill.demo_001",
                "question_card_id": "sentence_fill_middle_bridge",
                "source_question": {
                    "passage": "Community projects often begin with enthusiasm, but many lose momentum once the novelty fades. ____ When local volunteers can see short-term progress, they are more willing to stay involved for the long haul.",
                    "stem": "Fill in the blank with the most suitable sentence.",
                    "options": {
                        "A": "This is why organizers should break a large plan into visible, manageable stages.",
                        "B": "In fact, every successful project must avoid any public evaluation.",
                        "C": "As a result, most communities no longer care about cooperation.",
                        "D": "For this reason, long-term planning is always less important than passion.",
                    },
                    "answer": "A",
                    "analysis": "The blank bridges the problem of fading enthusiasm and the following explanation about visible short-term progress.",
                },
                "canonical_constraints": {
                    "blank_position": "middle",
                    "function_type": "bridge",
                    "logic_relation": "continuation",
                    "context_dependency": "medium",
                    "bidirectional_validation": "high",
                    "reference_dependency": "medium",
                    "semantic_scope": "paragraph_level",
                    "distractor_strength": "high",
                },
            },
            "historical_thread_summary": {
                "summary": "Earlier tuning rounds produced options that looked fluent but only matched one side of the blank.",
                "recurring_issues": [
                    "正确项常常只承前不启后",
                    "错误项太假，缺少近误竞争",
                ],
                "working_hypotheses": [
                    "需要更强的 bridge 守卫语句",
                    "需要 validator 检查双向衔接",
                ],
            },
            "test_result_snapshot": {
                "verdict": "mixed",
                "observed_constraints": {
                    "blank_position": "middle",
                    "function_type": "carry_previous",
                    "logic_relation": "continuation",
                    "context_dependency": "medium",
                    "bidirectional_validation": "medium",
                    "reference_dependency": "low",
                    "semantic_scope": "sentence_level",
                    "distractor_strength": "medium",
                },
                "generated_question": {
                    "stem": "Fill in the blank with the most suitable sentence.",
                    "options": {
                        "A": "This is why organizers should divide a large plan into visible stages.",
                        "B": "Local residents usually dislike any repeated community task.",
                        "C": "Short-term progress can be helpful, but the passage mainly celebrates excitement.",
                        "D": "This means communities should keep projects as simple as possible.",
                    },
                    "answer": "A",
                    "analysis": "The sentence explains the problem and is generally connected to the next sentence.",
                },
                "fit_signals": [
                    "answer matched truth",
                    "stem remained stable",
                ],
                "failure_modes": [
                    "bridge 感不足，更像承前解释",
                    "干扰项竞争度偏低",
                ],
                "metrics": [
                    {"metric_id": "distractor_quality", "value": 0.38, "note": "manual quick score"},
                ],
                "summary": "The generated item is usable, but it feels easier than the target truth sample.",
            },
            "runtime_state": {
                "question_card_id": "sentence_fill_middle_bridge",
                "question_card_snapshot": {
                    "default_slots": {
                        "blank_position": "middle",
                        "function_type": "bridge",
                        "logic_relation": "continuation",
                        "bidirectional_validation": "medium",
                    }
                },
                "prompt_asset_snapshot": {
                    "asset_keys": ["sentence_fill.base_guard", "sentence_fill.distractor_guard"],
                },
                "validator_contract_snapshot": {
                    "required_checks": ["answer_alignment", "single_correct_answer_guard"],
                },
                "material_mapping_snapshot": {
                    "preferred_material_cards": ["sentence_fill.middle_transition"],
                },
            },
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a minimal sentence_fill distillation debug packet.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "distillation_runtime" / "debug_packet.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    packet = build_demo_packet()
    output_path.write_text(
        json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"distillation debug packet written to: {output_path}")


if __name__ == "__main__":
    main()

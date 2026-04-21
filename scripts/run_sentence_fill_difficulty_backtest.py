from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROMPT_SERVICE_ROOT = ROOT / "prompt_skeleton_service"
if str(PROMPT_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMPT_SERVICE_ROOT))

from app.schemas.config import QuestionTypeConfig  # noqa: E402
from app.schemas.item import GeneratedQuestion  # noqa: E402
from app.services.difficulty_assessment_service import DifficultyAssessmentService  # noqa: E402
from app.services.difficulty_calibration_service import DifficultyCalibrationService  # noqa: E402
from app.services.difficulty_diff_service import DifficultyDiffService  # noqa: E402
from app.services.difficulty_projection_service import DifficultyProjectionService  # noqa: E402


def _default_question_type_config() -> QuestionTypeConfig:
    return QuestionTypeConfig.model_validate(
        {
            "type_id": "sentence_fill",
            "display_name": "Sentence Fill",
            "task_definition": "Fill the missing sentence.",
            "skeleton": {"anchor_type": "blank", "operation_type": "fill", "target_type": "sentence"},
            "slot_schema": {
                "blank_position": {"type": "string", "required": False},
                "function_type": {"type": "string", "required": False},
                "logic_relation": {"type": "string", "required": False},
                "context_dependency": {"type": "string", "required": False},
                "reference_dependency": {"type": "string", "required": False},
                "bidirectional_validation": {"type": "string", "required": False},
                "distractor_strength": {"type": "string", "required": False},
            },
            "default_slots": {},
            "patterns": [
                {
                    "pattern_id": "sentence_fill.default_backtest",
                    "pattern_name": "sentence_fill default backtest",
                    "enabled": True,
                    "match_rules": {},
                    "control_logic": {
                        "difficulty_source": "card",
                        "option_confusion": "configured",
                        "control_levers": {
                            "passage": "from_config",
                            "correct_option": "from_config",
                            "wrong_options": "from_config",
                        },
                    },
                    "generation_logic": {
                        "generation_core": "sentence_fill.default_backtest",
                        "processing_type": "literal",
                        "correct_logic": "keep_source_sentence",
                        "high_freq_traps": [],
                        "distractor_pattern": "semantic_close",
                        "analysis_steps": "check_bidirectional_fit",
                    },
                    "difficulty_rules": {
                        "complexity": {"base": 0.52},
                        "ambiguity": {"base": 0.5},
                        "reasoning_depth": {"base": 0.54},
                        "distractor_similarity": {"base": 0.52},
                    },
                }
            ],
            "default_pattern_id": "sentence_fill.default_backtest",
            "difficulty_target_profiles": {
                "easy": {
                    "complexity": {"min": 0.2, "max": 0.45},
                    "ambiguity": {"min": 0.18, "max": 0.44},
                    "reasoning_depth": {"min": 0.2, "max": 0.46},
                    "distractor_similarity": {"min": 0.2, "max": 0.46},
                },
                "medium": {
                    "complexity": {"min": 0.45, "max": 0.7},
                    "ambiguity": {"min": 0.4, "max": 0.68},
                    "reasoning_depth": {"min": 0.42, "max": 0.72},
                    "distractor_similarity": {"min": 0.42, "max": 0.72},
                },
                "hard": {
                    "complexity": {"min": 0.68, "max": 0.95},
                    "ambiguity": {"min": 0.65, "max": 0.92},
                    "reasoning_depth": {"min": 0.68, "max": 0.95},
                    "distractor_similarity": {"min": 0.66, "max": 0.94},
                },
            },
        }
    )


def _default_case_payload() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "sf-medium-bridge",
            "difficulty_target": "medium",
            "resolved_slots": {
                "blank_position": "middle",
                "function_type": "bridge",
                "logic_relation": "transition",
                "context_dependency": "medium",
                "reference_dependency": "medium",
                "bidirectional_validation": "high",
                "distractor_strength": "medium",
            },
            "material_text": "前文指出社区治理存在碎片化协同难题。____。后文随即展开制度协同、资源整合和人才支持三条路径。",
            "generated_question": {
                "question_type": "sentence_fill",
                "stem": "下列句子填入文中横线处，最恰当的一项是：",
                "options": {
                    "A": "这意味着问题的破解不能停留在单点补丁，而要转入更系统的协同设计。",
                    "B": "总之，这类问题并不值得继续讨论。",
                    "C": "这种现象在很多地区都曾经出现过。",
                    "D": "因此，只要增加投入就能彻底解决。",
                },
                "answer": "A",
                "analysis": "A项既回收前文问题，也自然引出后文路径展开。",
            },
            "gold_question": {
                "question_type": "sentence_fill",
                "stem": "下列句子填入文中横线处，最恰当的一项是：",
                "options": {
                    "A": "要真正打通治理堵点，还需要把原本分散的治理动作重新编织成协同链条。",
                    "B": "总之，问题已经说明清楚。",
                    "C": "这一现象只是局部案例。",
                    "D": "因此，不宜继续推进。",
                },
                "answer": "A",
                "analysis": "真题更强调协同链条与后文路径的双向衔接。",
            },
            "validator_result": {"validation_status": "passed", "errors": [], "warnings": []},
        }
    ]


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    question_type_config = _default_question_type_config()
    pattern = question_type_config.patterns[0]
    difficulty_target = str(case.get("difficulty_target") or "medium")
    resolved_slots = dict(case.get("resolved_slots") or {})
    projection_service = DifficultyProjectionService()
    assessment_service = DifficultyAssessmentService()
    diff_service = DifficultyDiffService()
    calibration_service = DifficultyCalibrationService()

    projection, target_profile, _ = projection_service.project(
        question_type_config=question_type_config,
        pattern=pattern,
        resolved_slots=resolved_slots,
        difficulty_target=difficulty_target,
    )
    generated_question = GeneratedQuestion.model_validate(case["generated_question"])
    actual_assessment = assessment_service.assess(
        question_type="sentence_fill",
        target_difficulty=difficulty_target,
        generated_question=generated_question,
        material_text=str(case.get("material_text") or ""),
        projection=projection,
        resolved_slots=resolved_slots,
        validator_status=str(((case.get("validator_result") or {}).get("validation_status")) or ""),
    )

    gold_assessment = None
    if case.get("gold_question"):
        gold_assessment = assessment_service.assess(
            question_type="sentence_fill",
            target_difficulty=difficulty_target,
            generated_question=GeneratedQuestion.model_validate(case["gold_question"]),
            material_text=str(case.get("gold_material_text") or case.get("material_text") or ""),
            projection=projection,
            resolved_slots=resolved_slots,
            validator_status="truth_reference",
        )

    fit_result = diff_service.build_fit_result(
        target_difficulty=difficulty_target,
        target_profile=target_profile,
        projection=projection,
        actual_assessment=actual_assessment,
        gold_assessment=gold_assessment,
        validator_result=dict(case.get("validator_result") or {}),
        structural_changes=list(actual_assessment.structural_changes),
    )
    patch_candidates = calibration_service.build_patch_candidates(
        question_type="sentence_fill",
        fit_result=fit_result,
    )
    report_row = diff_service.build_report_row(
        fit_result=fit_result,
        patch_candidates=patch_candidates,
    )
    return {
        "case_id": case.get("case_id") or "unknown",
        "difficulty_target": difficulty_target,
        "resolved_slots": resolved_slots,
        "difficulty_projection": projection.model_dump(),
        "actual_difficulty_assessment": actual_assessment.model_dump(),
        "gold_difficulty_assessment": gold_assessment.model_dump() if gold_assessment else None,
        "difficulty_fit": fit_result.model_dump(),
        "difficulty_calibration_patches": [patch.model_dump() for patch in patch_candidates],
        "report_row": report_row,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run sentence_fill difficulty backtest.")
    parser.add_argument(
        "--input",
        default="",
        help="Optional JSON file containing a list of backtest cases.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "reports" / "difficulty_control" / "sentence_fill_backtest.json"),
        help="JSON output path.",
    )
    args = parser.parse_args()

    if args.input:
        cases = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        cases = _default_case_payload()

    results = [evaluate_case(case) for case in cases]
    payload = {
        "family": "sentence_fill",
        "case_count": len(results),
        "results": results,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"sentence_fill difficulty backtest written to: {output_path}")


if __name__ == "__main__":
    main()

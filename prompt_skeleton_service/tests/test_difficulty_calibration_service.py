from __future__ import annotations

from unittest import TestCase

from app.schemas.difficulty import DifficultyFitResult
from app.services.difficulty_calibration_service import DifficultyCalibrationService


class DifficultyCalibrationServiceTest(TestCase):
    def setUp(self) -> None:
        self.service = DifficultyCalibrationService()

    def test_build_patch_candidates_returns_prompt_and_validator_candidates(self) -> None:
        fit_result = DifficultyFitResult(
            target_difficulty="hard",
            actual_difficulty="medium",
            gold_difficulty="hard",
            fit_result="under_target",
            axis_diff={
                "global_context_dependency": {
                    "target": 0.8,
                    "actual": 0.58,
                    "actual_minus_target": -0.22,
                }
            },
            structural_changes=["blank_position=middle"],
            validator_status="failed",
            review_delta={"error_count": 1, "warning_count": 0, "deviation_count": 2},
            promotion_recommendation="hold_and_patch_validator",
            in_range=False,
        )

        candidates = self.service.build_patch_candidates(question_type="sentence_fill", fit_result=fit_result)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].patch_target, "prompt_assets")
        self.assertEqual(candidates[1].patch_target, "validator")

    def test_gold_mismatch_returns_question_card_candidate(self) -> None:
        fit_result = DifficultyFitResult(
            target_difficulty="medium",
            actual_difficulty="medium",
            gold_difficulty="hard",
            fit_result="gold_mismatch",
            axis_diff={},
            structural_changes=[],
            validator_status="passed",
            review_delta={"error_count": 0, "warning_count": 0, "deviation_count": 0},
            promotion_recommendation="patch_prompt_assets_and_card",
            in_range=False,
        )

        candidates = self.service.build_patch_candidates(question_type="sentence_fill", fit_result=fit_result)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].patch_target, "question_card")

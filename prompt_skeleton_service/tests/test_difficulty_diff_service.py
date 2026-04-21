from __future__ import annotations

from unittest import TestCase

from app.schemas.difficulty import ActualDifficultyAssessment, DifficultyProjection, DifficultyTargetProfile
from app.services.difficulty_diff_service import DifficultyDiffService


class DifficultyDiffServiceTest(TestCase):
    def setUp(self) -> None:
        self.service = DifficultyDiffService()
        self.target_profile = DifficultyTargetProfile.model_validate(
            {
                "complexity": {"min": 0.45, "max": 0.7},
                "ambiguity": {"min": 0.4, "max": 0.68},
                "reasoning_depth": {"min": 0.42, "max": 0.72},
                "distractor_similarity": {"min": 0.42, "max": 0.72},
            }
        )

    def test_build_fit_result_marks_gold_mismatch_and_includes_axis_diff(self) -> None:
        fit = self.service.build_fit_result(
            target_difficulty="medium",
            target_profile=self.target_profile,
            projection=DifficultyProjection(
                target_difficulty="medium",
                projected_difficulty="medium",
                complexity=0.56,
                ambiguity=0.52,
                reasoning_depth=0.58,
                distractor_similarity=0.54,
                axis_projection={
                    "local_binding_complexity": 0.56,
                    "global_context_dependency": 0.54,
                },
                prompt_contract={},
                validator_contract={
                    "difficulty_control": {
                        "axis_targets": {
                            "local_binding_complexity": 0.56,
                            "global_context_dependency": 0.54,
                        },
                        "projection_axes": {
                            "local_binding_complexity": 0.61,
                            "global_context_dependency": 0.63,
                        },
                    }
                },
                structural_changes=[],
                notes=[],
            ),
            actual_assessment=ActualDifficultyAssessment(
                target_difficulty="medium",
                actual_difficulty="medium",
                axis_scores={
                    "local_binding_complexity": 0.68,
                    "global_context_dependency": 0.62,
                },
                metric_scores={
                    "complexity": 0.6,
                    "ambiguity": 0.58,
                    "reasoning_depth": 0.61,
                    "distractor_similarity": 0.57,
                },
                evidence={},
                structural_changes=["blank_position=middle"],
                validator_status="passed",
            ),
            gold_assessment=ActualDifficultyAssessment(
                target_difficulty="medium",
                actual_difficulty="hard",
                axis_scores={
                    "local_binding_complexity": 0.82,
                    "global_context_dependency": 0.79,
                },
                metric_scores={
                    "complexity": 0.72,
                    "ambiguity": 0.7,
                    "reasoning_depth": 0.74,
                    "distractor_similarity": 0.69,
                },
                evidence={},
                structural_changes=[],
                validator_status="truth_reference",
            ),
            validator_result={"validation_status": "passed", "errors": [], "warnings": []},
            structural_changes=["blank_position=middle"],
        )

        self.assertEqual(fit.fit_result, "gold_mismatch")
        self.assertEqual(fit.axis_diff["local_binding_complexity"]["target"], 0.56)
        self.assertEqual(fit.axis_diff["local_binding_complexity"]["projection"], 0.61)
        self.assertEqual(fit.axis_diff["local_binding_complexity"]["actual"], 0.68)
        self.assertEqual(fit.axis_diff["local_binding_complexity"]["gold"], 0.82)

    def test_build_report_row_uses_unified_fields(self) -> None:
        fit = self.service.build_fit_result(
            target_difficulty="medium",
            target_profile=self.target_profile,
            projection={
                "projected_difficulty": "medium",
                "complexity": 0.55,
                "ambiguity": 0.5,
                "reasoning_depth": 0.56,
                "distractor_similarity": 0.54,
            },
            actual_assessment={
                "actual_difficulty": "medium",
                "metric_scores": {
                    "complexity": 0.55,
                    "ambiguity": 0.5,
                    "reasoning_depth": 0.56,
                    "distractor_similarity": 0.54,
                },
            },
            validator_result={"validation_status": "passed", "errors": [], "warnings": []},
            structural_changes=[],
        )

        row = self.service.build_report_row(fit_result=fit)

        self.assertEqual(
            set(row.keys()),
            {
                "target_difficulty",
                "actual_difficulty",
                "gold_difficulty",
                "fit_result",
                "axis_diff",
                "structural_changes",
                "validator_status",
                "review_delta",
                "promotion_recommendation",
                "patch_candidates",
            },
        )

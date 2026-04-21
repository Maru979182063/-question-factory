from __future__ import annotations

from unittest import TestCase

from app.schemas.item import GeneratedQuestion
from app.services.difficulty_assessment_service import DifficultyAssessmentService


class DifficultyAssessmentServiceTest(TestCase):
    def setUp(self) -> None:
        self.service = DifficultyAssessmentService()

    def test_sentence_fill_assessment_scores_all_axes(self) -> None:
        assessment = self.service.assess(
            question_type="sentence_fill",
            target_difficulty="hard",
            generated_question=GeneratedQuestion(
                question_type="sentence_fill",
                stem="下列句子填入文中横线处，最恰当的一项是：",
                options={
                    "A": "这一转变既回应了前文的问题，也为后文的治理路径展开搭起了桥梁。",
                    "B": "总之，这一问题已经得到解决。",
                    "C": "这说明现象并不复杂。",
                    "D": "因此，只要增加投入就能彻底解决。",
                },
                answer="A",
                analysis="A项既承接前文问题，也引出后文路径展开。",
            ),
            material_text="前文指出基层治理长期受制于协同不足。____。后文转入制度协同、资金支持和人才培养三方面的路径设计。",
            resolved_slots={
                "blank_position": "middle",
                "function_type": "bridge",
                "reference_dependency": "high",
                "bidirectional_validation": "high",
            },
            validator_status="passed",
        )

        self.assertEqual(assessment.actual_difficulty, "medium")
        self.assertEqual(
            set(assessment.axis_scores.keys()),
            {
                "local_binding_complexity",
                "global_context_dependency",
                "distractor_similarity",
                "blank_function_ambiguity",
            },
        )
        self.assertIn("function_type=bridge", assessment.structural_changes)

    def test_assessment_falls_back_to_projection_for_other_families(self) -> None:
        assessment = self.service.assess(
            question_type="main_idea",
            target_difficulty="medium",
            generated_question=None,
            material_text="材料",
            projection={
                "complexity": 0.6,
                "ambiguity": 0.55,
                "reasoning_depth": 0.58,
                "distractor_similarity": 0.57,
            },
            validator_status="projection_only",
        )

        self.assertEqual(assessment.actual_difficulty, "medium")
        self.assertEqual(assessment.evidence["mode"], "projection_fallback")
        self.assertTrue(assessment.metric_scores["complexity"] > 0.5)

from __future__ import annotations

from unittest import TestCase

from app.schemas.distillation import DistillationInputPacket
from app.services.distillation_diff_service import DistillationDiffService
from app.services.distillation_runtime_service import DistillationRuntimeService


def _packet() -> DistillationInputPacket:
    return DistillationInputPacket.model_validate(
        {
            "family_id": "sentence_fill",
            "truth_sample": {
                "source_question": {
                    "passage": "People stay committed to shared goals when they can recognize visible progress. ____ That is why small milestones often matter more than loud promises.",
                    "stem": "Fill in the blank with the most suitable sentence.",
                    "options": {
                        "A": "Short-term wins give a large project a rhythm that volunteers can actually follow.",
                        "B": "Therefore public work should avoid any measurable target.",
                        "C": "In this way, all communities naturally dislike planning.",
                        "D": "As a result, passion is always enough for long-term work.",
                    },
                    "answer": "A",
                    "analysis": "The correct option bridges the need for visible progress and the concluding point about milestones.",
                },
                "canonical_constraints": {
                    "blank_position": "middle",
                    "function_type": "bridge",
                    "logic_relation": "continuation",
                    "context_dependency": "high",
                    "bidirectional_validation": "high",
                    "reference_dependency": "medium",
                    "semantic_scope": "paragraph_level",
                },
            },
            "historical_thread_summary": {
                "summary": "Bridge items tend to collapse into plain explanation.",
                "recurring_issues": ["功能位偏成承前解释"],
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
                },
                "generated_question": {
                    "stem": "Fill in the blank with the most suitable sentence.",
                    "options": {
                        "A": "Short-term wins give a project a rhythm that volunteers can follow.",
                        "B": "Most communities do not care about visible progress.",
                        "C": "This only repeats that passion is important.",
                        "D": "Public work should become simpler than any plan.",
                    },
                    "answer": "A",
                    "analysis": "The sentence fits the previous sentence.",
                },
                "failure_modes": ["更像承前解释", "干扰项竞争度一般"],
            },
            "runtime_state": {
                "question_card_snapshot": {"default_slots": {"function_type": "bridge"}},
                "prompt_asset_snapshot": {"asset_keys": ["sentence_fill.base_guard"]},
                "validator_contract_snapshot": {"required_checks": ["answer_alignment"]},
                "material_mapping_snapshot": {"preferred_material_cards": ["sentence_fill.middle_transition"]},
            },
        }
    )


class DistillationDiffServiceTest(TestCase):
    def test_build_report_contains_difficulty_and_patch_diffs(self) -> None:
        packet = _packet()
        result = DistillationRuntimeService().build_result_packet(packet)

        report = DistillationDiffService().build_report(packet, result)

        self.assertEqual(report.family_id, "sentence_fill")
        self.assertEqual(len(report.difficulty_diffs), 4)
        self.assertTrue(report.patch_diffs)
        self.assertIn(report.overall_fit_status, {"adjust", "poor", "good"})

    def test_render_markdown_surfaces_fit_table(self) -> None:
        packet = _packet()
        result = DistillationRuntimeService().build_result_packet(packet)
        report = DistillationDiffService().build_report(packet, result)

        markdown = DistillationDiffService().render_markdown(report)

        self.assertIn("sentence_fill 蒸馏 diff report", markdown)
        self.assertIn("| 维度 | target | actual | delta | fit_status |", markdown)

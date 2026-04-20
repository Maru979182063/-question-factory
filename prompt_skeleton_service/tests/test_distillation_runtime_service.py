from __future__ import annotations

from unittest import TestCase

from app.schemas.distillation import DistillationInputPacket
from app.services.distillation_runtime_service import DistillationRuntimeService


def _build_packet() -> DistillationInputPacket:
    return DistillationInputPacket.model_validate(
        {
            "family_id": "sentence_fill",
            "truth_sample": {
                "sample_id": "truth.sentence_fill.case1",
                "source_question": {
                    "passage": "Many readers are attracted by inspiring plans, but they remain committed only when they can observe concrete progress. ____ In that way, the community keeps both enthusiasm and patience.",
                    "stem": "Fill in the blank with the most suitable sentence.",
                    "options": {
                        "A": "So organizers should divide an ambitious goal into visible and manageable stages.",
                        "B": "That is why public projects should avoid any long-term plan.",
                        "C": "As a result, most readers dislike cooperation with others.",
                        "D": "Therefore inspiration is usually less valuable than any detailed plan.",
                    },
                    "answer": "A",
                    "analysis": "The correct option bridges the problem in the first sentence and the following explanation about visible progress.",
                },
                "canonical_constraints": {
                    "blank_position": "middle",
                    "function_type": "bridge",
                    "logic_relation": "continuation",
                    "context_dependency": "high",
                    "bidirectional_validation": "high",
                    "reference_dependency": "medium",
                    "semantic_scope": "paragraph_level",
                    "distractor_strength": "high",
                },
            },
            "historical_thread_summary": {
                "summary": "Earlier rounds produced items that only explained the first sentence.",
                "recurring_issues": ["正确项只承前不启后", "干扰项太假"],
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
                        "A": "So organizers should divide an ambitious goal into visible stages.",
                        "B": "Projects usually fail because readers dislike patience.",
                        "C": "Enthusiasm alone can solve every public problem.",
                        "D": "This sentence only repeats that plans are important.",
                    },
                    "answer": "A",
                    "analysis": "The sentence generally fits the passage.",
                },
                "failure_modes": ["bridge 感不足", "干扰项太弱"],
                "fit_signals": ["answer matched"],
                "metrics": [{"metric_id": "distractor_quality", "value": 0.3}],
            },
            "runtime_state": {
                "question_card_id": "sentence_fill_middle_bridge",
                "question_card_snapshot": {
                    "default_slots": {
                        "blank_position": "middle",
                        "function_type": "bridge",
                    }
                },
                "prompt_asset_snapshot": {"asset_keys": ["sentence_fill.base_guard"]},
                "validator_contract_snapshot": {"required_checks": ["answer_alignment"]},
                "material_mapping_snapshot": {"preferred_material_cards": ["sentence_fill.middle_transition"]},
            },
        }
    )


class DistillationRuntimeServiceTest(TestCase):
    def test_build_result_packet_returns_structured_sentence_fill_output(self) -> None:
        service = DistillationRuntimeService()
        packet = _build_packet()

        result = service.build_result_packet(packet)

        self.assertEqual(result.family_id, "sentence_fill")
        self.assertEqual(result.normalized_view.truth_constraints.function_type, "bridge")
        self.assertEqual(result.normalized_view.observed_constraints.function_type, "carry_previous")
        self.assertEqual(len(result.difficulty_fit), 4)
        self.assertTrue(result.candidate_patches)
        self.assertTrue(result.selected_agent_adjustment.selected_patch_ids)

    def test_build_result_packet_detects_under_target_dimensions(self) -> None:
        service = DistillationRuntimeService()
        packet = _build_packet()

        result = service.build_result_packet(packet)

        fit_map = {entry.dimension: entry.fit_status for entry in result.difficulty_fit}
        self.assertEqual(fit_map["local_binding_complexity"], "under_target")
        self.assertEqual(fit_map["global_context_dependency"], "under_target")
        self.assertIn("question_card.local_binding_complexity.under_target", {patch.patch_id for patch in result.candidate_patches})

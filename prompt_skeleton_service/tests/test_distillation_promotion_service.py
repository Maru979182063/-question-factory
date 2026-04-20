from __future__ import annotations

from unittest import TestCase

from app.schemas.distillation import (
    AgentAdjustmentPlan,
    CandidatePatch,
    DistillationEvidence,
    DistillationNormalizedView,
    DistillationResultPacket,
    DifficultyFitEntry,
    SentenceFillConstraintSnapshot,
    SentenceFillDifficultyObservation,
)
from app.services.distillation_promotion_service import DistillationPromotionService


def _result_packet() -> DistillationResultPacket:
    return DistillationResultPacket(
        packet_id="distill_input_test",
        family_id="sentence_fill",
        normalized_view=DistillationNormalizedView(
            truth_constraints=SentenceFillConstraintSnapshot(blank_position="middle", function_type="bridge", logic_relation="continuation"),
            observed_constraints=SentenceFillConstraintSnapshot(blank_position="middle", function_type="carry_previous", logic_relation="continuation"),
        ),
        target_difficulty=SentenceFillDifficultyObservation(
            local_binding_complexity=0.7,
            global_context_dependency=0.68,
            distractor_similarity=0.72,
            blank_function_ambiguity=0.62,
        ),
        actual_difficulty=SentenceFillDifficultyObservation(
            local_binding_complexity=0.48,
            global_context_dependency=0.4,
            distractor_similarity=0.44,
            blank_function_ambiguity=0.37,
        ),
        difficulty_fit=[
            DifficultyFitEntry(
                dimension="local_binding_complexity",
                target=0.7,
                actual=0.48,
                delta=-0.22,
                fit_status="under_target",
            )
        ],
        overall_fit_status="poor",
        candidate_patches=[
            CandidatePatch(
                patch_id="question_card.local_binding_complexity.under_target",
                target="question_card",
                dimension="local_binding_complexity",
                direction="raise",
                priority="high",
                summary="收紧局部绑定约束",
                rationale="需要提高局部绑定复杂度。",
                proposed_change={"change": {"bidirectional_validation": "high"}},
                expected_effect="提高承前启后强度。",
                evidence=[DistillationEvidence(source="truth_sample", summary="truth says bridge", payload={})],
            ),
            CandidatePatch(
                patch_id="validator_contract.local_binding_complexity.under_target",
                target="validator_contract",
                dimension="local_binding_complexity",
                direction="raise",
                priority="high",
                summary="增加局部绑定校验",
                rationale="validator 需要补充双向检查。",
                proposed_change={"require_checks": ["forward_anchor_alignment"]},
                expected_effect="拦截只满足单向衔接的题。",
            ),
        ],
        selected_agent_adjustment=AgentAdjustmentPlan(
            round_label="round1",
            selected_patch_ids=["question_card.local_binding_complexity.under_target"],
            instruction_summary="apply top patch then replay",
        ),
        structured_summary={},
    )


class DistillationPromotionServiceTest(TestCase):
    def test_build_candidate_bundle_groups_patches_by_target(self) -> None:
        service = DistillationPromotionService()

        bundle = service.build_candidate_bundle(_result_packet())

        self.assertEqual(bundle.bundle_mode, "candidate_only")
        self.assertEqual(bundle.family_id, "sentence_fill")
        self.assertEqual({item.target for item in bundle.patch_bundles}, {"question_card", "validator_contract"})
        self.assertEqual(bundle.selected_agent_adjustment.round_label, "round1")

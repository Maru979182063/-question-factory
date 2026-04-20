from __future__ import annotations

from collections import defaultdict

from app.core.exceptions import DomainError
from app.schemas.distillation import DistillationPromotionBundle, DistillationResultPacket, PromotionPatchBundle


class DistillationPromotionService:
    def build_candidate_bundle(self, result: DistillationResultPacket) -> DistillationPromotionBundle:
        if not result.candidate_patches:
            raise DomainError(
                "Cannot build distillation promotion bundle without candidate patches.",
                status_code=422,
                details={"result_id": result.result_id},
            )

        grouped = defaultdict(list)
        for patch in result.candidate_patches:
            grouped[patch.target].append(patch)

        patch_bundles = [
            PromotionPatchBundle(target=target, patches=patches)
            for target, patches in grouped.items()
        ]

        return DistillationPromotionBundle(
            packet_id=result.packet_id,
            result_id=result.result_id,
            family_id=result.family_id,
            patch_bundles=patch_bundles,
            selected_agent_adjustment=result.selected_agent_adjustment,
            handoff_notes=[
                "candidate_only bundle: do not auto-write main configs",
                "review question_card and validator_contract patches before any promotion",
                "rerun offline sentence_fill diff after applying the selected adjustment",
            ],
            artifacts={
                "overall_fit_status": result.overall_fit_status,
                "candidate_patch_count": len(result.candidate_patches),
            },
        )

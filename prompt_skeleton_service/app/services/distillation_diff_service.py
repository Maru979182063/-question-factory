from __future__ import annotations

from typing import Any

from app.schemas.distillation import (
    DistillationDiffReport,
    DistillationInputPacket,
    DistillationResultPacket,
    PatchDiffEntry,
)


class DistillationDiffService:
    def build_report(
        self,
        packet: DistillationInputPacket,
        result: DistillationResultPacket,
    ) -> DistillationDiffReport:
        patch_diffs = [
            PatchDiffEntry(
                patch_id=patch.patch_id,
                target=patch.target,
                current_excerpt=self._current_excerpt(packet, patch.target),
                proposed_excerpt=dict(patch.proposed_change),
                semantic_change=patch.summary,
                risk_note=self._risk_note(patch.target, patch.direction),
            )
            for patch in result.candidate_patches
        ]
        recommended_next_step = self._recommended_next_step(result.overall_fit_status, len(result.candidate_patches))
        return DistillationDiffReport(
            packet_id=packet.packet_id,
            result_id=result.result_id,
            family_id=result.family_id,
            overall_fit_status=result.overall_fit_status,
            difficulty_diffs=list(result.difficulty_fit),
            patch_diffs=patch_diffs,
            test_report={
                "verdict": packet.test_result_snapshot.verdict,
                "failure_modes": list(packet.test_result_snapshot.failure_modes),
                "fit_signals": list(packet.test_result_snapshot.fit_signals),
                "candidate_patch_count": len(result.candidate_patches),
            },
            recommended_next_step=recommended_next_step,
        )

    def render_markdown(self, report: DistillationDiffReport) -> str:
        lines = [
            "# sentence_fill 蒸馏 diff report",
            "",
            f"- report_id: `{report.report_id}`",
            f"- overall_fit_status: `{report.overall_fit_status}`",
            f"- recommended_next_step: {report.recommended_next_step}",
            "",
            "## 难度拟合",
            "",
            "| 维度 | target | actual | delta | fit_status |",
            "| --- | --- | --- | --- | --- |",
        ]
        for entry in report.difficulty_diffs:
            lines.append(
                f"| {entry.dimension} | {entry.target:.2f} | {entry.actual:.2f} | {entry.delta:+.2f} | {entry.fit_status} |"
            )
        lines.extend(["", "## candidate patches", ""])
        if not report.patch_diffs:
            lines.append("- no candidate patch generated")
        else:
            for patch in report.patch_diffs:
                lines.append(
                    f"- `{patch.patch_id}` -> `{patch.target}`: {patch.semantic_change}"
                )
        lines.extend(["", "## test snapshot", ""])
        lines.append(f"- verdict: `{report.test_report.get('verdict')}`")
        failure_modes = report.test_report.get("failure_modes") or []
        fit_signals = report.test_report.get("fit_signals") or []
        lines.append(f"- failure_modes: {', '.join(failure_modes) if failure_modes else 'none'}")
        lines.append(f"- fit_signals: {', '.join(fit_signals) if fit_signals else 'none'}")
        return "\n".join(lines)

    @staticmethod
    def _current_excerpt(packet: DistillationInputPacket, target: str) -> dict[str, Any]:
        runtime_state = packet.runtime_state
        if target == "question_card":
            return dict(runtime_state.question_card_snapshot)
        if target == "prompt_assets":
            return dict(runtime_state.prompt_asset_snapshot)
        if target == "validator_contract":
            return dict(runtime_state.validator_contract_snapshot)
        if target == "material_mapping":
            return dict(runtime_state.material_mapping_snapshot)
        return {}

    @staticmethod
    def _risk_note(target: str, direction: str) -> str | None:
        if target == "question_card":
            return "check whether the patch changes canonical family defaults beyond sentence_fill minimum scope"
        if target == "validator_contract":
            return "avoid adding validator obligations that were not declared by contract"
        if direction == "lower":
            return "verify that lowering difficulty does not collapse distractor competition"
        return None

    @staticmethod
    def _recommended_next_step(overall_fit_status: str, patch_count: int) -> str:
        if overall_fit_status == "good":
            return "keep the current baseline and only replay the selected patch subset if a reviewer asks for stricter fit"
        if patch_count == 0:
            return "inspect the packet because no patch target was available for the detected gap"
        return "apply the selected candidate patches offline, rerun sentence_fill tests, then compare the new diff report"

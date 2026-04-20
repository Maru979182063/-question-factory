from __future__ import annotations

from typing import Any

from app.schemas.difficulty import DifficultyCalibrationPatch, DifficultyFitResult


class DifficultyCalibrationService:
    def build_patch_candidates(
        self,
        *,
        question_type: str,
        fit_result: DifficultyFitResult | dict[str, Any],
    ) -> list[DifficultyCalibrationPatch]:
        payload = fit_result.model_dump() if hasattr(fit_result, "model_dump") else dict(fit_result)
        target_difficulty = str(payload.get("target_difficulty") or "medium")
        actual_difficulty = payload.get("actual_difficulty")
        gold_difficulty = payload.get("gold_difficulty")
        fit_label = str(payload.get("fit_result") or "unknown")
        axis_diff = dict(payload.get("axis_diff") or {})
        structural_changes = list(payload.get("structural_changes") or [])
        validator_status = payload.get("validator_status")
        review_delta = dict(payload.get("review_delta") or {})
        promotion_recommendation = payload.get("promotion_recommendation")

        candidates: list[DifficultyCalibrationPatch] = []
        if fit_label in {"under_target", "over_target"}:
            candidates.append(
                DifficultyCalibrationPatch(
                    patch_target="prompt_assets",
                    patch_scope=f"{question_type}.difficulty_prompt",
                    title="Adjust prompt-side difficulty emphasis",
                    summary="Tighten or relax prompt emphasis on the axis that drifted furthest from target.",
                    patch_candidate={
                        "action": "axis_emphasis_rebalance",
                        "axis_diff": axis_diff,
                    },
                    target_difficulty=target_difficulty,
                    actual_difficulty=actual_difficulty,
                    gold_difficulty=gold_difficulty,
                    fit_result=fit_label,
                    axis_diff=axis_diff,
                    structural_changes=structural_changes,
                    validator_status=validator_status,
                    review_delta=review_delta,
                    promotion_recommendation=promotion_recommendation,
                )
            )
        if fit_label == "gold_mismatch":
            candidates.append(
                DifficultyCalibrationPatch(
                    patch_target="question_card",
                    patch_scope=f"{question_type}.difficulty_card_defaults",
                    title="Align card-side axis defaults with gold feel",
                    summary="Keep the target band but shift default axis center toward the gold profile.",
                    patch_candidate={
                        "action": "adjust_default_axis_center",
                        "axis_diff": axis_diff,
                    },
                    target_difficulty=target_difficulty,
                    actual_difficulty=actual_difficulty,
                    gold_difficulty=gold_difficulty,
                    fit_result=fit_label,
                    axis_diff=axis_diff,
                    structural_changes=structural_changes,
                    validator_status=validator_status,
                    review_delta=review_delta,
                    promotion_recommendation=promotion_recommendation,
                )
            )
        if validator_status == "failed":
            candidates.append(
                DifficultyCalibrationPatch(
                    patch_target="validator",
                    patch_scope=f"{question_type}.difficulty_validator_thresholds",
                    title="Review validator threshold alignment",
                    summary="Generated difficulty drift co-occurred with validator failure; inspect threshold coupling before promotion.",
                    patch_candidate={
                        "action": "review_thresholds",
                        "review_delta": review_delta,
                    },
                    target_difficulty=target_difficulty,
                    actual_difficulty=actual_difficulty,
                    gold_difficulty=gold_difficulty,
                    fit_result=fit_label,
                    axis_diff=axis_diff,
                    structural_changes=structural_changes,
                    validator_status=validator_status,
                    review_delta=review_delta,
                    promotion_recommendation=promotion_recommendation,
                )
            )
        return candidates

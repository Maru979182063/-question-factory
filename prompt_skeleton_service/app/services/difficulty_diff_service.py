from __future__ import annotations

from typing import Any

from app.schemas.difficulty import (
    ActualDifficultyAssessment,
    DifficultyCalibrationPatch,
    DifficultyDeviation,
    DifficultyFitLabel,
    DifficultyFitResult,
    DifficultyProjection,
    DifficultyTargetProfile,
)


class DifficultyDiffService:
    def build_fit_result(
        self,
        *,
        target_difficulty: str,
        target_profile: DifficultyTargetProfile | None,
        projection: DifficultyProjection | dict[str, Any] | None = None,
        actual_assessment: ActualDifficultyAssessment | dict[str, Any] | None = None,
        gold_assessment: ActualDifficultyAssessment | dict[str, Any] | None = None,
        validator_result: dict[str, Any] | None = None,
        structural_changes: list[str] | None = None,
    ) -> DifficultyFitResult:
        actual_payload = self._as_payload(actual_assessment)
        gold_payload = self._as_payload(gold_assessment)
        projection_payload = self._as_payload(projection)

        actual_band = actual_payload.get("actual_difficulty") or projection_payload.get("projected_difficulty")
        gold_band = gold_payload.get("actual_difficulty")
        axis_scores = dict(actual_payload.get("axis_scores") or {})
        gold_axis_scores = dict(gold_payload.get("axis_scores") or {})
        difficulty_control = dict((projection_payload.get("validator_contract") or {}).get("difficulty_control") or {})
        axis_diff = self._build_axis_diff(
            target_axis_scores=dict(difficulty_control.get("axis_targets") or {}),
            projection_axis_scores=dict(difficulty_control.get("projection_axes") or {}),
            axis_scores=axis_scores,
            gold_axis_scores=gold_axis_scores,
        )
        deviations = self._build_deviations(
            target_profile=target_profile,
            actual_payload=actual_payload,
            projection_payload=projection_payload,
        )
        fit_result = self._fit_result_label(
            target_difficulty=target_difficulty,
            actual_difficulty=str(actual_band or ""),
            gold_difficulty=str(gold_band or ""),
            deviations=deviations,
        )
        validator_status = str((validator_result or {}).get("validation_status") or actual_payload.get("validator_status") or "")
        review_delta = {
            "error_count": len((validator_result or {}).get("errors") or []),
            "warning_count": len((validator_result or {}).get("warnings") or []),
            "deviation_count": len(deviations),
        }
        promotion_recommendation = self._promotion_recommendation(
            fit_result=fit_result,
            validator_status=validator_status,
            deviations=deviations,
        )
        return DifficultyFitResult(
            target_difficulty=target_difficulty,
            actual_difficulty=actual_band if actual_band in {"easy", "medium", "hard"} else None,
            gold_difficulty=gold_band if gold_band in {"easy", "medium", "hard"} else None,
            fit_result=fit_result,
            axis_diff=axis_diff,
            structural_changes=list(structural_changes or actual_payload.get("structural_changes") or []),
            validator_status=validator_status or None,
            review_delta=review_delta,
            promotion_recommendation=promotion_recommendation,
            in_range=not deviations and fit_result in {"on_target", "unknown"},
            deviations=deviations,
            notes=[],
        )

    def build_report_row(
        self,
        *,
        fit_result: DifficultyFitResult,
        patch_candidates: list[DifficultyCalibrationPatch] | None = None,
    ) -> dict[str, Any]:
        return {
            "target_difficulty": fit_result.target_difficulty,
            "actual_difficulty": fit_result.actual_difficulty,
            "gold_difficulty": fit_result.gold_difficulty,
            "fit_result": fit_result.fit_result,
            "axis_diff": fit_result.axis_diff,
            "structural_changes": fit_result.structural_changes,
            "validator_status": fit_result.validator_status,
            "review_delta": fit_result.review_delta,
            "promotion_recommendation": fit_result.promotion_recommendation,
            "patch_candidates": [patch.model_dump() for patch in (patch_candidates or [])],
        }

    def _build_axis_diff(
        self,
        *,
        target_axis_scores: dict[str, Any],
        projection_axis_scores: dict[str, Any],
        axis_scores: dict[str, Any],
        gold_axis_scores: dict[str, Any],
    ) -> dict[str, Any]:
        diff: dict[str, Any] = {}
        axis_names = (
            set(target_axis_scores.keys())
            | set(projection_axis_scores.keys())
            | set(axis_scores.keys())
            | set(gold_axis_scores.keys())
        )
        for axis_name in sorted(axis_names):
            target = self._coerce_float(target_axis_scores.get(axis_name))
            projection = self._coerce_float(projection_axis_scores.get(axis_name))
            actual = self._coerce_float(axis_scores.get(axis_name))
            gold = self._coerce_float(gold_axis_scores.get(axis_name))
            diff[axis_name] = {
                "target": target,
                "projection": projection,
                "actual": actual,
                "gold": gold,
                "projection_minus_target": round(projection - target, 4)
                if projection is not None and target is not None
                else None,
                "actual_minus_target": round(actual - target, 4) if actual is not None and target is not None else None,
                "actual_minus_gold": round(actual - gold, 4) if actual is not None and gold is not None else None,
            }
        return diff

    def _build_deviations(
        self,
        *,
        target_profile: DifficultyTargetProfile | None,
        actual_payload: dict[str, Any],
        projection_payload: dict[str, Any],
    ) -> list[DifficultyDeviation]:
        if target_profile is None:
            return []
        actual_metrics = dict(actual_payload.get("metric_scores") or {})
        if not actual_metrics:
            actual_metrics = {
                key: projection_payload.get(key)
                for key in ("complexity", "ambiguity", "reasoning_depth", "distractor_similarity")
            }
        deviations: list[DifficultyDeviation] = []
        for metric_name in ("complexity", "ambiguity", "reasoning_depth", "distractor_similarity"):
            actual = self._coerce_float(actual_metrics.get(metric_name))
            if actual is None:
                continue
            target_range = getattr(target_profile, metric_name)
            if actual < target_range.min or actual > target_range.max:
                deviations.append(
                    DifficultyDeviation(
                        metric=metric_name,
                        target_min=round(target_range.min, 4),
                        target_max=round(target_range.max, 4),
                        actual=round(actual, 4),
                    )
                )
        return deviations

    def _fit_result_label(
        self,
        *,
        target_difficulty: str,
        actual_difficulty: str,
        gold_difficulty: str,
        deviations: list[DifficultyDeviation],
    ) -> DifficultyFitLabel:
        if actual_difficulty not in {"easy", "medium", "hard"}:
            return "unknown"
        if gold_difficulty in {"easy", "medium", "hard"} and gold_difficulty != actual_difficulty:
            return "gold_mismatch"
        if actual_difficulty == target_difficulty and not deviations:
            return "on_target"
        order = {"easy": 0, "medium": 1, "hard": 2}
        if order[actual_difficulty] < order[str(target_difficulty)]:
            return "under_target"
        if order[actual_difficulty] > order[str(target_difficulty)]:
            return "over_target"
        return "on_target"

    @staticmethod
    def _promotion_recommendation(
        *,
        fit_result: DifficultyFitLabel,
        validator_status: str,
        deviations: list[DifficultyDeviation],
    ) -> str:
        if validator_status == "failed":
            return "hold_and_patch_validator"
        if fit_result == "gold_mismatch":
            return "patch_prompt_assets_and_card"
        if deviations:
            return "patch_prompt_assets"
        return "promote_candidate_patch_bundle"

    @staticmethod
    def _as_payload(value: Any | None) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
        if isinstance(value, dict):
            return dict(value)
        return {}

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        try:
            return round(float(value), 4)
        except (TypeError, ValueError):
            return None

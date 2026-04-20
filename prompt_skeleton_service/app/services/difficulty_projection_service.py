from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.schemas.config import PatternConfig, QuestionTypeConfig
from app.schemas.difficulty import (
    DifficultyBand,
    DifficultyDeviation,
    DifficultyFitLabel,
    DifficultyFitResult,
    DifficultyProjection,
    DifficultyTarget,
    DifficultyTargetProfile,
)


_PROMPT_ASSET_PATH = Path(__file__).resolve().parents[2] / "configs" / "prompt_assets" / "difficulty_control_prompt_assets.yaml"


class DifficultyProjectionService:
    def project(
        self,
        *,
        question_type_config: QuestionTypeConfig,
        pattern: PatternConfig,
        resolved_slots: dict[str, Any],
        difficulty_target: DifficultyBand,
        business_subtype: str | None = None,
    ) -> tuple[DifficultyProjection, DifficultyTargetProfile, DifficultyFitResult]:
        target = DifficultyTarget(
            question_type=question_type_config.type_id,
            business_subtype=business_subtype,
            family=self._family_id(question_type_config.type_id, business_subtype),
            target_difficulty=difficulty_target,
            axis_targets=self._axis_targets_for(
                question_type=question_type_config.type_id,
                difficulty_target=difficulty_target,
            ),
        )
        target_profile = self._get_target_profile(
            question_type_config=question_type_config,
            difficulty_target=difficulty_target,
        )
        projection = self._build_projection(
            target=target,
            pattern=pattern,
            resolved_slots=resolved_slots,
            target_profile=target_profile,
        )
        fit_result = self.build_projection_fit_result(
            target_profile=target_profile,
            projection=projection,
        )
        return projection, target_profile, fit_result

    def build_projection_fit_result(
        self,
        *,
        target_profile: DifficultyTargetProfile,
        projection: DifficultyProjection,
    ) -> DifficultyFitResult:
        deviations: list[DifficultyDeviation] = []
        axis_diff: dict[str, dict[str, float | None]] = {}
        for metric_name in ("complexity", "ambiguity", "reasoning_depth", "distractor_similarity"):
            actual = float(getattr(projection, metric_name))
            target_range = getattr(target_profile, metric_name)
            axis_diff[metric_name] = {
                "actual": round(actual, 4),
                "target_midpoint": target_range.midpoint(),
                "target_min": round(target_range.min, 4),
                "target_max": round(target_range.max, 4),
                "delta_to_target_midpoint": round(actual - target_range.midpoint(), 4),
            }
            if actual < target_range.min or actual > target_range.max:
                deviations.append(
                    DifficultyDeviation(
                        metric=metric_name,
                        target_min=round(target_range.min, 4),
                        target_max=round(target_range.max, 4),
                        actual=round(actual, 4),
                    )
                )
        fit_result = "on_target" if not deviations else self._fit_label_from_projection(target_profile=target_profile, projection=projection)
        return DifficultyFitResult(
            target_difficulty=projection.target_difficulty,
            actual_difficulty=projection.projected_difficulty,
            gold_difficulty=None,
            fit_result=fit_result,
            axis_diff=axis_diff,
            structural_changes=list(projection.structural_changes or []),
            validator_status="projection_only",
            review_delta={"deviation_count": len(deviations)},
            promotion_recommendation="hold_projection" if deviations else "keep_projection",
            in_range=not deviations,
            deviations=deviations,
            notes=list(projection.notes or []),
        )

    def build_prompt_sections(self, *, projection: DifficultyProjection) -> list[str]:
        assets = _difficulty_assets()
        shared_lines = [str(item).strip() for item in (assets.get("shared_prompt_lines") or []) if str(item).strip()]
        family_lines = [
            str(item).strip()
            for item in (((assets.get("families") or {}).get("sentence_fill") or {}).get("prompt_lines") or [])
            if str(item).strip()
        ]
        axis_lines = [
            f"{axis}={round(value, 2)}"
            for axis, value in sorted((projection.axis_projection or {}).items())
        ]
        metric_lines = [
            f"complexity={projection.complexity}",
            f"ambiguity={projection.ambiguity}",
            f"reasoning_depth={projection.reasoning_depth}",
            f"distractor_similarity={projection.distractor_similarity}",
        ]
        sections = [*shared_lines, *family_lines]
        if axis_lines:
            sections.append("axis_projection: " + "; ".join(axis_lines))
        sections.append("metric_projection: " + "; ".join(metric_lines))
        return sections

    def _build_projection(
        self,
        *,
        target: DifficultyTarget,
        pattern: PatternConfig,
        resolved_slots: dict[str, Any],
        target_profile: DifficultyTargetProfile,
    ) -> DifficultyProjection:
        text_lookup = self._build_text_lookup(pattern=pattern, resolved_slots=resolved_slots)
        metric_scores: dict[str, float] = {}
        for metric_name in ("complexity", "ambiguity", "reasoning_depth", "distractor_similarity"):
            metric_rule = getattr(pattern.difficulty_rules, metric_name)
            score = metric_rule.base if metric_rule.base is not None else 0.3
            for slot_name, mapping in metric_rule.by_slot.items():
                slot_value = resolved_slots.get(slot_name)
                if slot_value is not None and str(slot_value) in mapping:
                    score = mapping[str(slot_value)]
            for text_key, mapping in metric_rule.by_text.items():
                text_value = text_lookup.get(text_key)
                if text_value is not None and str(text_value) in mapping:
                    score = mapping[str(text_value)]
            metric_scores[metric_name] = self._clamp(score)

        axis_projection = self._sentence_fill_axis_projection(
            difficulty_target=target.target_difficulty,
            resolved_slots=resolved_slots,
        )
        prompt_contract = {
            "difficulty_target": target.target_difficulty,
            "projection_method": "pattern_rules_plus_sentence_fill_axis_projection",
            "prompt_sections": self.build_prompt_sections(
                projection=DifficultyProjection(
                    target_difficulty=target.target_difficulty,
                    projected_difficulty=self._band_from_metric_scores(metric_scores, target_profile=target_profile),
                    axis_projection=axis_projection,
                    prompt_contract={},
                    validator_contract={},
                    structural_changes=[],
                    notes=[],
                    **metric_scores,
                )
            ),
        }
        validator_contract = {
            "difficulty_control": {
                "target_difficulty": target.target_difficulty,
                "axis_targets": dict(target.axis_targets),
                "projection_axes": dict(axis_projection),
                "projection_metrics": dict(metric_scores),
            }
        }
        projected_difficulty = self._band_from_metric_scores(metric_scores, target_profile=target_profile)
        return DifficultyProjection(
            target_difficulty=target.target_difficulty,
            projected_difficulty=projected_difficulty,
            axis_projection=axis_projection,
            prompt_contract=prompt_contract,
            validator_contract=validator_contract,
            structural_changes=[],
            notes=[f"family={target.family or target.question_type}", f"pattern={pattern.pattern_id}"],
            **metric_scores,
        )

    def _sentence_fill_axis_projection(
        self,
        *,
        difficulty_target: DifficultyBand,
        resolved_slots: dict[str, Any],
    ) -> dict[str, float]:
        base_targets = self._axis_targets_for(question_type="sentence_fill", difficulty_target=difficulty_target)
        if not base_targets:
            return {}

        projection = dict(base_targets)
        blank_position = str(resolved_slots.get("blank_position") or "").strip()
        function_type = str(resolved_slots.get("function_type") or "").strip()
        logic_relation = str(resolved_slots.get("logic_relation") or "").strip()
        context_dependency = str(resolved_slots.get("context_dependency") or "").strip()
        reference_dependency = str(resolved_slots.get("reference_dependency") or "").strip()
        bidirectional_validation = str(resolved_slots.get("bidirectional_validation") or "").strip()
        distractor_strength = str(resolved_slots.get("distractor_strength") or "").strip()

        if blank_position in {"middle", "inserted", "mixed"}:
            projection["local_binding_complexity"] += 0.08
        if function_type in {"bridge", "reference_summary", "lead_next"}:
            projection["local_binding_complexity"] += 0.08
            projection["global_context_dependency"] += 0.08
        if function_type in {"summary", "conclusion"}:
            projection["blank_function_ambiguity"] += 0.04
        if logic_relation in {"transition", "focus_shift", "reference_match", "multi_constraint"}:
            projection["blank_function_ambiguity"] += 0.08
        if context_dependency == "high":
            projection["global_context_dependency"] += 0.08
        elif context_dependency == "low":
            projection["global_context_dependency"] -= 0.05
        if reference_dependency == "high":
            projection["global_context_dependency"] += 0.06
            projection["blank_function_ambiguity"] += 0.06
        if bidirectional_validation == "high":
            projection["local_binding_complexity"] += 0.06
        if distractor_strength == "high":
            projection["distractor_similarity"] += 0.08
        elif distractor_strength == "low":
            projection["distractor_similarity"] -= 0.08

        return {key: self._clamp(value) for key, value in projection.items()}

    def _axis_targets_for(self, *, question_type: str, difficulty_target: DifficultyBand) -> dict[str, float]:
        assets = _difficulty_assets()
        family_assets = ((assets.get("families") or {}).get(question_type) or {})
        targets = ((family_assets.get("axis_targets") or {}).get(difficulty_target) or {})
        return {
            str(key): self._clamp(float(value))
            for key, value in targets.items()
        }

    def _get_target_profile(
        self,
        *,
        question_type_config: QuestionTypeConfig,
        difficulty_target: DifficultyBand,
    ) -> DifficultyTargetProfile:
        profile = question_type_config.difficulty_target_profiles[difficulty_target]
        return DifficultyTargetProfile.model_validate(profile.model_dump())

    def _build_text_lookup(self, *, pattern: PatternConfig, resolved_slots: dict[str, Any]) -> dict[str, Any]:
        lookup = dict(resolved_slots)
        lookup.update(pattern.control_logic.model_dump())
        lookup.update(pattern.generation_logic.model_dump())
        return lookup

    def _band_from_metric_scores(
        self,
        metric_scores: dict[str, float],
        *,
        target_profile: DifficultyTargetProfile,
    ) -> DifficultyBand:
        average = sum(metric_scores.values()) / max(len(metric_scores), 1)
        easy_mid = 0.3
        medium_mid = self._profile_midpoint(target_profile)
        hard_mid = 0.78
        if average < (easy_mid + medium_mid) / 2:
            return "easy"
        if average < (medium_mid + hard_mid) / 2:
            return "medium"
        return "hard"

    def _fit_label_from_projection(
        self,
        *,
        target_profile: DifficultyTargetProfile,
        projection: DifficultyProjection,
    ) -> DifficultyFitLabel:
        target_mid = self._profile_midpoint(target_profile)
        actual_mid = (
            projection.complexity
            + projection.ambiguity
            + projection.reasoning_depth
            + projection.distractor_similarity
        ) / 4.0
        if abs(actual_mid - target_mid) <= 0.06:
            return "on_target"
        if actual_mid < target_mid:
            return "under_target"
        return "over_target"

    @staticmethod
    def _profile_midpoint(profile: DifficultyTargetProfile) -> float:
        return round(
            (
                profile.complexity.midpoint()
                + profile.ambiguity.midpoint()
                + profile.reasoning_depth.midpoint()
                + profile.distractor_similarity.midpoint()
            )
            / 4.0,
            4,
        )

    @staticmethod
    def _family_id(question_type: str, business_subtype: str | None) -> str:
        if question_type == "main_idea" and business_subtype:
            return business_subtype
        return question_type

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 4)


@lru_cache(maxsize=1)
def _difficulty_assets() -> dict[str, Any]:
    raw = yaml.safe_load(_PROMPT_ASSET_PATH.read_text(encoding="utf-8")) or {}
    return dict(raw.get("difficulty_control") or {})

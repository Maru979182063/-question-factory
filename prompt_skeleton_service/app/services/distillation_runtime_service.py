from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from difflib import SequenceMatcher

from app.core.exceptions import DomainError
from app.schemas.distillation import (
    AgentAdjustmentPlan,
    CandidatePatch,
    DifficultyDimension,
    DifficultyFitEntry,
    DistillationEvidence,
    DistillationInputPacket,
    DistillationNormalizedView,
    DistillationResultPacket,
    SentenceFillConstraintSnapshot,
    SentenceFillDifficultyObservation,
)
from app.services.sentence_fill_protocol import (
    normalize_sentence_fill_blank_position,
    normalize_sentence_fill_constraints,
    normalize_sentence_fill_function_type,
    normalize_sentence_fill_logic_relation,
    sentence_fill_default_slot,
)


_PROMPT_ASSET_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "prompt_assets" / "truth_distillation_prompt_assets.yaml"
)

_DIMENSIONS: tuple[DifficultyDimension, ...] = (
    "local_binding_complexity",
    "global_context_dependency",
    "distractor_similarity",
    "blank_function_ambiguity",
)


@lru_cache(maxsize=1)
def load_truth_distillation_prompt_assets() -> dict[str, Any]:
    if not _PROMPT_ASSET_PATH.exists():
        raise DomainError(
            "Truth distillation prompt assets config does not exist.",
            status_code=500,
            details={"config_path": str(_PROMPT_ASSET_PATH)},
        )
    raw = yaml.safe_load(_PROMPT_ASSET_PATH.read_text(encoding="utf-8")) or {}
    assets = raw.get("truth_distillation")
    if not isinstance(assets, dict):
        raise DomainError(
            "Truth distillation prompt assets config is invalid.",
            status_code=500,
            details={"config_path": str(_PROMPT_ASSET_PATH)},
        )
    return assets


class DistillationRuntimeService:
    def __init__(self) -> None:
        self.assets = load_truth_distillation_prompt_assets()

    def build_result_packet(self, packet: DistillationInputPacket) -> DistillationResultPacket:
        if packet.family_id != "sentence_fill":
            raise DomainError(
                "Distillation runtime currently only supports sentence_fill.",
                status_code=422,
                details={"family_id": packet.family_id},
            )

        truth_constraints = self._normalize_constraints(packet.truth_sample.canonical_constraints.model_dump())
        observed_constraints = self._normalize_constraints(packet.test_result_snapshot.observed_constraints.model_dump())

        normalized_view = DistillationNormalizedView(
            truth_constraints=truth_constraints,
            observed_constraints=observed_constraints,
            thread_focus=self._normalize_focus_list(packet.historical_thread_summary.recurring_issues),
            failure_focus=self._normalize_focus_list(packet.test_result_snapshot.failure_modes),
            runtime_focus=self._runtime_focus(packet),
        )

        target_difficulty = packet.truth_sample.target_difficulty or self._infer_target_difficulty(packet, truth_constraints)
        actual_difficulty = packet.test_result_snapshot.actual_difficulty or self._infer_actual_difficulty(
            packet,
            observed_constraints,
        )
        difficulty_fit = self._build_difficulty_fit(target_difficulty, actual_difficulty)
        candidate_patches = self._build_candidate_patches(packet, difficulty_fit)
        selected_agent_adjustment = self._select_agent_adjustment(candidate_patches)

        return DistillationResultPacket(
            packet_id=packet.packet_id,
            family_id=packet.family_id,
            normalized_view=normalized_view,
            target_difficulty=target_difficulty,
            actual_difficulty=actual_difficulty,
            difficulty_fit=difficulty_fit,
            overall_fit_status=self._overall_fit_status(difficulty_fit),
            candidate_patches=candidate_patches,
            selected_agent_adjustment=selected_agent_adjustment,
            structured_summary={
                "requested_patch_targets": list(packet.requested_patch_targets),
                "normalization_guardrails": list(self.assets.get("prompts", {}).get("normalization_guardrails") or []),
                "candidate_patch_count": len(candidate_patches),
                "largest_gap_dimension": self._largest_gap_dimension(difficulty_fit),
            },
        )

    def _normalize_constraints(self, payload: dict[str, Any]) -> SentenceFillConstraintSnapshot:
        normalized = normalize_sentence_fill_constraints(payload)
        normalized["blank_position"] = normalize_sentence_fill_blank_position(
            normalized.get("blank_position") or sentence_fill_default_slot("blank_position", "middle")
        )
        normalized["function_type"] = normalize_sentence_fill_function_type(
            normalized.get("function_type") or sentence_fill_default_slot("function_type", "bridge")
        )
        normalized["logic_relation"] = normalize_sentence_fill_logic_relation(
            normalized.get("logic_relation") or sentence_fill_default_slot("logic_relation", "continuation")
        )
        for field_name, fallback in (
            ("context_dependency", sentence_fill_default_slot("context_dependency", "medium")),
            ("bidirectional_validation", sentence_fill_default_slot("bidirectional_validation", "medium")),
            ("reference_dependency", sentence_fill_default_slot("reference_dependency", "low")),
            ("semantic_scope", sentence_fill_default_slot("semantic_scope", "sentence_level")),
            ("distractor_strength", sentence_fill_default_slot("distractor_strength", "high")),
            ("reference_anchor", sentence_fill_default_slot("reference_anchor", "none")),
        ):
            normalized[field_name] = str(normalized.get(field_name) or fallback).strip()
        return SentenceFillConstraintSnapshot.model_validate(normalized)

    def _infer_target_difficulty(
        self,
        packet: DistillationInputPacket,
        constraints: SentenceFillConstraintSnapshot,
    ) -> SentenceFillDifficultyObservation:
        passage = packet.truth_sample.source_question.passage or ""
        base_local = 0.36
        base_global = 0.34
        base_distractor = 0.46
        base_ambiguity = 0.31

        base_local += self._weighted_lookup(constraints.blank_position, {"opening": -0.05, "middle": 0.14, "ending": 0.03, "inserted": 0.18, "mixed": 0.16})
        base_local += self._weighted_lookup(constraints.bidirectional_validation, {"low": -0.08, "medium": 0.0, "high": 0.14})
        base_local += self._weighted_lookup(constraints.reference_dependency, {"low": -0.04, "medium": 0.06, "high": 0.12})

        base_global += self._weighted_lookup(constraints.semantic_scope, {"local": -0.12, "sentence_level": 0.0, "paragraph_level": 0.2})
        base_global += self._weighted_lookup(constraints.context_dependency, {"low": -0.08, "medium": 0.0, "high": 0.18})
        base_global += min(len(passage) / 1200.0, 0.12)

        base_distractor += self._answer_option_similarity(packet)
        base_distractor += self._weighted_lookup(constraints.distractor_strength, {"low": -0.12, "medium": -0.02, "high": 0.1})

        base_ambiguity += self._weighted_lookup(
            constraints.function_type,
            {
                "summary": 0.08,
                "topic_intro": 0.04,
                "carry_previous": 0.1,
                "lead_next": 0.12,
                "bridge": 0.18,
                "reference_summary": 0.14,
                "countermeasure": 0.11,
                "conclusion": 0.06,
            },
        )
        base_ambiguity += self._weighted_lookup(
            constraints.logic_relation,
            {
                "continuation": 0.05,
                "transition": 0.08,
                "explanation": 0.06,
                "focus_shift": 0.12,
                "summary": 0.04,
                "action": 0.05,
                "elevation": 0.09,
                "reference_match": 0.1,
                "multi_constraint": 0.16,
            },
        )
        base_ambiguity += min(len(packet.historical_thread_summary.recurring_issues) * 0.025, 0.12)

        return SentenceFillDifficultyObservation(
            local_binding_complexity=self._clamp(base_local),
            global_context_dependency=self._clamp(base_global),
            distractor_similarity=self._clamp(base_distractor),
            blank_function_ambiguity=self._clamp(base_ambiguity),
            notes=[
                "target difficulty inferred from truth sample and canonical sentence_fill constraints",
            ],
        )

    def _infer_actual_difficulty(
        self,
        packet: DistillationInputPacket,
        constraints: SentenceFillConstraintSnapshot,
    ) -> SentenceFillDifficultyObservation:
        generated = packet.test_result_snapshot.generated_question
        passage = packet.truth_sample.source_question.passage or ""
        fit_penalty = 0.06 if packet.test_result_snapshot.verdict == "fail" else 0.03 if packet.test_result_snapshot.verdict == "mixed" else 0.0

        local_value = 0.28
        local_value += self._weighted_lookup(constraints.bidirectional_validation, {"low": -0.05, "medium": 0.0, "high": 0.11})
        local_value += self._weighted_lookup(constraints.reference_dependency, {"low": -0.03, "medium": 0.04, "high": 0.08})
        local_value -= fit_penalty

        global_value = 0.26
        global_value += self._weighted_lookup(constraints.semantic_scope, {"local": -0.08, "sentence_level": 0.0, "paragraph_level": 0.14})
        global_value += self._weighted_lookup(constraints.context_dependency, {"low": -0.06, "medium": 0.0, "high": 0.12})
        global_value += min(len(passage) / 1400.0, 0.08)
        global_value -= fit_penalty

        distractor_value = 0.3
        distractor_value += self._generated_option_similarity(generated)
        distractor_value += self._metric_bonus(packet, "distractor_quality", 0.18)
        distractor_value -= fit_penalty

        ambiguity_value = 0.24
        ambiguity_value += min(len(packet.test_result_snapshot.failure_modes) * 0.05, 0.18)
        ambiguity_value += min(len(packet.historical_thread_summary.recurring_issues) * 0.02, 0.1)
        ambiguity_value += self._weighted_lookup(constraints.function_type, {"bridge": 0.12, "lead_next": 0.08, "carry_previous": 0.08, "reference_summary": 0.09})
        ambiguity_value -= 0.04 if packet.test_result_snapshot.verdict == "pass" else 0.0

        return SentenceFillDifficultyObservation(
            local_binding_complexity=self._clamp(local_value),
            global_context_dependency=self._clamp(global_value),
            distractor_similarity=self._clamp(distractor_value),
            blank_function_ambiguity=self._clamp(ambiguity_value),
            notes=[
                "actual difficulty inferred from test result snapshot and generated candidate behaviour",
            ],
        )

    def _build_difficulty_fit(
        self,
        target: SentenceFillDifficultyObservation,
        actual: SentenceFillDifficultyObservation,
    ) -> list[DifficultyFitEntry]:
        entries: list[DifficultyFitEntry] = []
        for dimension in _DIMENSIONS:
            target_value = float(getattr(target, dimension))
            actual_value = float(getattr(actual, dimension))
            delta = round(actual_value - target_value, 4)
            if abs(delta) <= 0.08:
                fit_status = "matched"
            elif delta < 0:
                fit_status = "under_target"
            else:
                fit_status = "over_target"
            entries.append(
                DifficultyFitEntry(
                    dimension=dimension,
                    target=round(target_value, 4),
                    actual=round(actual_value, 4),
                    delta=delta,
                    fit_status=fit_status,
                    note=self._dimension_note(dimension, fit_status),
                )
            )
        return entries

    def _build_candidate_patches(
        self,
        packet: DistillationInputPacket,
        difficulty_fit: list[DifficultyFitEntry],
    ) -> list[CandidatePatch]:
        sentence_fill_assets = self.assets.get("sentence_fill") or {}
        patch_blueprints = sentence_fill_assets.get("patch_blueprints") or {}
        dimension_assets = sentence_fill_assets.get("difficulty_dimensions") or {}
        patches: list[CandidatePatch] = []

        for entry in sorted(difficulty_fit, key=lambda item: abs(item.delta), reverse=True):
            if entry.fit_status == "matched":
                continue
            direction_key = "under_target" if entry.fit_status == "under_target" else "over_target"
            blueprint = ((patch_blueprints.get(entry.dimension) or {}).get(direction_key) or {})
            dimension_asset = dimension_assets.get(entry.dimension) or {}
            for target in packet.requested_patch_targets:
                target_blueprint = blueprint.get(target)
                if not isinstance(target_blueprint, dict):
                    continue
                patch_id = f"{target}.{entry.dimension}.{direction_key}"
                patches.append(
                    CandidatePatch(
                        patch_id=patch_id,
                        target=target,
                        dimension=entry.dimension,
                        direction="raise" if entry.fit_status == "under_target" else "lower",
                        priority=self._priority_from_gap(abs(entry.delta)),
                        summary=str(target_blueprint.get("summary") or "").format(dimension=entry.dimension),
                        rationale=str(target_blueprint.get("rationale") or "").format(
                            dimension_label=dimension_asset.get("label") or entry.dimension,
                            target=entry.target,
                            actual=entry.actual,
                        ),
                        proposed_change=dict(target_blueprint.get("payload") or {}),
                        expected_effect=str(target_blueprint.get("expected_effect") or ""),
                        evidence=self._build_patch_evidence(packet, entry, dimension_asset),
                    )
                )
        return patches

    def _select_agent_adjustment(self, patches: list[CandidatePatch]) -> AgentAdjustmentPlan:
        selected = patches[: min(len(patches), 3)]
        evaluation_focus = [patch.dimension for patch in selected]
        return AgentAdjustmentPlan(
            round_label="round1_minimal_adjustment",
            selected_patch_ids=[patch.patch_id for patch in selected],
            instruction_summary="Apply the top gap-oriented candidate patches as a single offline adjustment round, then rerun sentence_fill diff and test snapshot comparison.",
            evaluation_focus=evaluation_focus,
            stop_conditions=[
                "difficulty fit remains outside tolerance on two or more dimensions",
                "candidate patch changes drift away from sentence_fill canonical constraints",
            ],
        )

    def _runtime_focus(self, packet: DistillationInputPacket) -> list[str]:
        focuses: list[str] = []
        if packet.runtime_state.question_card_id:
            focuses.append(f"question_card_id={packet.runtime_state.question_card_id}")
        if packet.runtime_state.prompt_asset_snapshot:
            focuses.append("prompt_asset_snapshot_present")
        if packet.runtime_state.validator_contract_snapshot:
            focuses.append("validator_contract_snapshot_present")
        if packet.runtime_state.material_mapping_snapshot:
            focuses.append("material_mapping_snapshot_present")
        return focuses

    @staticmethod
    def _normalize_focus_list(values: list[str]) -> list[str]:
        ordered: list[str] = []
        for item in values:
            text = str(item or "").strip()
            if text and text not in ordered:
                ordered.append(text)
        return ordered

    def _metric_bonus(self, packet: DistillationInputPacket, metric_id: str, scale: float) -> float:
        for metric in packet.test_result_snapshot.metrics:
            if metric.metric_id != metric_id:
                continue
            try:
                value = float(metric.value)
            except (TypeError, ValueError):
                return 0.0
            return max(min(value, 1.0), 0.0) * scale
        return 0.0

    def _answer_option_similarity(self, packet: DistillationInputPacket) -> float:
        options = packet.truth_sample.source_question.options or {}
        answer_key = str(packet.truth_sample.source_question.answer or "").strip()
        answer_text = str(options.get(answer_key) or "").strip()
        if not answer_text:
            return 0.0
        similarities = [
            self._text_similarity(answer_text, text)
            for key, text in options.items()
            if key != answer_key and str(text or "").strip()
        ]
        if not similarities:
            return 0.0
        return round(sum(similarities) / len(similarities) * 0.18, 4)

    def _generated_option_similarity(self, generated: Any) -> float:
        if generated is None:
            return 0.0
        options = dict(getattr(generated, "options", {}) or {})
        answer_key = str(getattr(generated, "answer", "") or "").strip()
        answer_text = str(options.get(answer_key) or "").strip()
        if not answer_text:
            return 0.0
        similarities = [
            self._text_similarity(answer_text, text)
            for key, text in options.items()
            if key != answer_key and str(text or "").strip()
        ]
        if not similarities:
            return 0.0
        return round(sum(similarities) / len(similarities) * 0.22, 4)

    @staticmethod
    def _text_similarity(left: str, right: str) -> float:
        normalized_left = " ".join(str(left or "").strip().lower().split())
        normalized_right = " ".join(str(right or "").strip().lower().split())
        if not normalized_left or not normalized_right:
            return 0.0
        return round(SequenceMatcher(a=normalized_left, b=normalized_right).ratio(), 4)

    @staticmethod
    def _weighted_lookup(key: str | None, mapping: dict[str, float]) -> float:
        return float(mapping.get(str(key or "").strip(), 0.0))

    @staticmethod
    def _clamp(value: float) -> float:
        return round(min(max(value, 0.0), 1.0), 4)

    @staticmethod
    def _priority_from_gap(gap: float) -> str:
        if gap >= 0.22:
            return "high"
        if gap >= 0.12:
            return "medium"
        return "low"

    def _build_patch_evidence(
        self,
        packet: DistillationInputPacket,
        entry: DifficultyFitEntry,
        dimension_asset: dict[str, Any],
    ) -> list[DistillationEvidence]:
        return [
            DistillationEvidence(
                source="truth_sample",
                summary=f"target constraint for {entry.dimension}",
                payload=packet.truth_sample.canonical_constraints.model_dump(exclude_none=True),
            ),
            DistillationEvidence(
                source="test_result_snapshot",
                summary=f"actual test signal for {entry.dimension}",
                payload={
                    "failure_modes": list(packet.test_result_snapshot.failure_modes),
                    "fit_signals": list(packet.test_result_snapshot.fit_signals),
                    "verdict": packet.test_result_snapshot.verdict,
                },
            ),
            DistillationEvidence(
                source="prompt_assets",
                summary=str(dimension_asset.get("description") or entry.dimension),
                payload={"asset_dimension": entry.dimension},
            ),
        ]

    @staticmethod
    def _dimension_note(dimension: DifficultyDimension, fit_status: str) -> str:
        if fit_status == "matched":
            return f"{dimension} is within the minimal sentence_fill tolerance window"
        if fit_status == "under_target":
            return f"{dimension} is weaker than the target sentence_fill feel"
        return f"{dimension} is stronger than the target sentence_fill feel"

    @staticmethod
    def _overall_fit_status(entries: list[DifficultyFitEntry]) -> str:
        matched = sum(1 for entry in entries if entry.fit_status == "matched")
        if matched == len(entries):
            return "good"
        if matched >= 2:
            return "adjust"
        return "poor"

    @staticmethod
    def _largest_gap_dimension(entries: list[DifficultyFitEntry]) -> str | None:
        if not entries:
            return None
        return max(entries, key=lambda item: abs(item.delta)).dimension

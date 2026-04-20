from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from app.schemas.difficulty import ActualDifficultyAssessment, DifficultyBand, DifficultyProjection
from app.schemas.item import GeneratedQuestion


class DifficultyAssessmentService:
    def assess(
        self,
        *,
        question_type: str,
        target_difficulty: DifficultyBand,
        generated_question: GeneratedQuestion | None,
        material_text: str,
        projection: DifficultyProjection | dict[str, Any] | None = None,
        resolved_slots: dict[str, Any] | None = None,
        validator_status: str | None = None,
    ) -> ActualDifficultyAssessment:
        if question_type != "sentence_fill" or generated_question is None:
            metric_scores = self._projection_metrics(projection)
            actual_band = self._band_from_score(self._avg(metric_scores.values()))
            return ActualDifficultyAssessment(
                target_difficulty=target_difficulty,
                actual_difficulty=actual_band,
                axis_scores={},
                metric_scores=metric_scores,
                evidence={"mode": "projection_fallback"},
                structural_changes=[],
                validator_status=validator_status,
                notes=["assessment_fallback_used"],
            )

        resolved_slots = dict(resolved_slots or {})
        correct_text = self._correct_option_text(generated_question)
        previous_text, next_text = self._extract_blank_context(material_text)
        axis_scores = self._sentence_fill_axis_scores(
            generated_question=generated_question,
            correct_text=correct_text,
            previous_text=previous_text,
            next_text=next_text,
            resolved_slots=resolved_slots,
        )
        actual_band = self._band_from_score(self._avg(axis_scores.values()))
        metric_scores = self._projection_metrics(projection)
        if not metric_scores:
            metric_scores = {
                "complexity": axis_scores.get("local_binding_complexity", 0.0),
                "ambiguity": axis_scores.get("blank_function_ambiguity", 0.0),
                "reasoning_depth": axis_scores.get("global_context_dependency", 0.0),
                "distractor_similarity": axis_scores.get("distractor_similarity", 0.0),
            }

        structural_changes: list[str] = []
        function_type = str(resolved_slots.get("function_type") or "").strip()
        if function_type in {"bridge", "reference_summary", "lead_next"}:
            structural_changes.append(f"function_type={function_type}")
        blank_position = str(resolved_slots.get("blank_position") or "").strip()
        if blank_position:
            structural_changes.append(f"blank_position={blank_position}")

        return ActualDifficultyAssessment(
            target_difficulty=target_difficulty,
            actual_difficulty=actual_band,
            axis_scores=axis_scores,
            metric_scores=metric_scores,
            evidence={
                "previous_text": previous_text,
                "next_text": next_text,
                "correct_option": correct_text,
            },
            structural_changes=structural_changes,
            validator_status=validator_status,
            notes=[],
        )

    def _sentence_fill_axis_scores(
        self,
        *,
        generated_question: GeneratedQuestion,
        correct_text: str,
        previous_text: str,
        next_text: str,
        resolved_slots: dict[str, Any],
    ) -> dict[str, float]:
        options = {key: str(value or "").strip() for key, value in (generated_question.options or {}).items()}
        answer = str(generated_question.answer or "").strip().upper()
        distractors = [text for key, text in options.items() if key != answer and text]
        prev_overlap = self._text_similarity(correct_text, previous_text)
        next_overlap = self._text_similarity(correct_text, next_text)
        avg_distractor_similarity = self._avg(self._text_similarity(correct_text, item) for item in distractors)
        max_distractor_similarity = max([self._text_similarity(correct_text, item) for item in distractors] or [0.0])

        function_type = str(resolved_slots.get("function_type") or "").strip()
        blank_position = str(resolved_slots.get("blank_position") or "").strip()
        reference_dependency = str(resolved_slots.get("reference_dependency") or "").strip()
        bidirectional_validation = str(resolved_slots.get("bidirectional_validation") or "").strip()
        pronoun_density = self._pronoun_density(correct_text)

        local_binding_complexity = 0.34
        if blank_position in {"middle", "inserted", "mixed"}:
            local_binding_complexity += 0.12
        if function_type in {"bridge", "lead_next", "reference_summary"}:
            local_binding_complexity += 0.14
        if bidirectional_validation == "high":
            local_binding_complexity += 0.08
        local_binding_complexity += 0.18 * min(prev_overlap, next_overlap)

        global_context_dependency = 0.28 + 0.24 * max(prev_overlap, next_overlap) + 0.20 * pronoun_density
        if function_type in {"summary", "conclusion"}:
            global_context_dependency += 0.10
        if reference_dependency == "high":
            global_context_dependency += 0.12

        distractor_similarity = 0.45 * avg_distractor_similarity + 0.55 * max_distractor_similarity

        blank_function_ambiguity = 0.20 + 0.20 * avg_distractor_similarity + 0.18 * abs(prev_overlap - next_overlap)
        if function_type in {"summary", "conclusion", "reference_summary"}:
            blank_function_ambiguity += 0.12
        if len(distractors) >= 3:
            blank_function_ambiguity += 0.05

        return {
            "local_binding_complexity": self._clamp(local_binding_complexity),
            "global_context_dependency": self._clamp(global_context_dependency),
            "distractor_similarity": self._clamp(distractor_similarity),
            "blank_function_ambiguity": self._clamp(blank_function_ambiguity),
        }

    def _projection_metrics(self, projection: DifficultyProjection | dict[str, Any] | None) -> dict[str, float]:
        if projection is None:
            return {}
        payload = projection.model_dump() if hasattr(projection, "model_dump") else dict(projection)
        scores: dict[str, float] = {}
        for key in ("complexity", "ambiguity", "reasoning_depth", "distractor_similarity"):
            try:
                scores[key] = self._clamp(float(payload.get(key)))
            except (TypeError, ValueError):
                continue
        return scores

    @staticmethod
    def _correct_option_text(generated_question: GeneratedQuestion) -> str:
        answer = str(generated_question.answer or "").strip().upper()
        return str((generated_question.options or {}).get(answer) or "").strip()

    @staticmethod
    def _extract_blank_context(material_text: str) -> tuple[str, str]:
        text = str(material_text or "").strip()
        markers = ("____", "___", "[BLANK]", "( )", "（ ）", "（）")
        marker_index = -1
        marker = ""
        for candidate in markers:
            marker_index = text.find(candidate)
            if marker_index >= 0:
                marker = candidate
                break
        if marker_index < 0:
            return text[:120], text[-120:]
        previous_text = text[max(0, marker_index - 120) : marker_index].strip()
        next_start = marker_index + len(marker)
        next_text = text[next_start : next_start + 120].strip()
        return previous_text, next_text

    @staticmethod
    def _text_similarity(left: str, right: str) -> float:
        normalized_left = "".join(str(left or "").split())
        normalized_right = "".join(str(right or "").split())
        if not normalized_left or not normalized_right:
            return 0.0
        return round(SequenceMatcher(None, normalized_left, normalized_right).ratio(), 4)

    @staticmethod
    def _pronoun_density(text: str) -> float:
        if not text:
            return 0.0
        pronouns = ("这", "此", "其", "该", "这些", "这种", "这一", "上述")
        hit_count = sum(text.count(token) for token in pronouns)
        return round(min(1.0, hit_count / 4.0), 4)

    @staticmethod
    def _band_from_score(score: float) -> DifficultyBand:
        if score < 0.42:
            return "easy"
        if score < 0.69:
            return "medium"
        return "hard"

    @staticmethod
    def _avg(values) -> float:
        valid = [float(value) for value in values if value is not None]
        if not valid:
            return 0.0
        return round(sum(valid) / len(valid), 4)

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 4)

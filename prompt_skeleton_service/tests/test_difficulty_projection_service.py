from __future__ import annotations

from unittest import TestCase

from app.schemas.config import QuestionTypeConfig
from app.services.difficulty_projection_service import DifficultyProjectionService


def _build_sentence_fill_config() -> QuestionTypeConfig:
    return QuestionTypeConfig.model_validate(
        {
            "type_id": "sentence_fill",
            "display_name": "Sentence Fill",
            "task_definition": "Fill the missing sentence.",
            "skeleton": {
                "anchor_type": "blank",
                "operation_type": "fill",
                "target_type": "sentence",
            },
            "slot_schema": {
                "blank_position": {"type": "string", "required": False},
                "function_type": {"type": "string", "required": False},
                "logic_relation": {"type": "string", "required": False},
                "context_dependency": {"type": "string", "required": False},
                "reference_dependency": {"type": "string", "required": False},
                "bidirectional_validation": {"type": "string", "required": False},
                "distractor_strength": {"type": "string", "required": False},
            },
            "default_slots": {},
            "patterns": [
                {
                    "pattern_id": "bridge_transition",
                    "pattern_name": "Bridge Transition",
                    "enabled": True,
                    "match_rules": {},
                    "control_logic": {
                        "difficulty_source": "card",
                        "option_confusion": "configured",
                        "control_levers": {
                            "passage": "from_config",
                            "correct_option": "from_config",
                            "wrong_options": "from_config",
                        },
                    },
                    "generation_logic": {
                        "generation_core": "core.bridge",
                        "processing_type": "literal",
                        "correct_logic": "keep_source_sentence",
                        "high_freq_traps": [],
                        "distractor_pattern": "semantic_close",
                        "analysis_steps": "check_bidirectional_fit",
                    },
                    "difficulty_rules": {
                        "complexity": {"base": 0.5},
                        "ambiguity": {"base": 0.46},
                        "reasoning_depth": {"base": 0.52},
                        "distractor_similarity": {"base": 0.5},
                    },
                }
            ],
            "default_pattern_id": "bridge_transition",
            "difficulty_target_profiles": {
                "easy": {
                    "complexity": {"min": 0.2, "max": 0.45},
                    "ambiguity": {"min": 0.2, "max": 0.45},
                    "reasoning_depth": {"min": 0.2, "max": 0.45},
                    "distractor_similarity": {"min": 0.2, "max": 0.45},
                },
                "medium": {
                    "complexity": {"min": 0.45, "max": 0.7},
                    "ambiguity": {"min": 0.4, "max": 0.68},
                    "reasoning_depth": {"min": 0.42, "max": 0.72},
                    "distractor_similarity": {"min": 0.42, "max": 0.72},
                },
                "hard": {
                    "complexity": {"min": 0.68, "max": 0.95},
                    "ambiguity": {"min": 0.65, "max": 0.92},
                    "reasoning_depth": {"min": 0.68, "max": 0.95},
                    "distractor_similarity": {"min": 0.66, "max": 0.94},
                },
            },
        }
    )


class DifficultyProjectionServiceTest(TestCase):
    def setUp(self) -> None:
        self.service = DifficultyProjectionService()
        self.config = _build_sentence_fill_config()
        self.pattern = self.config.patterns[0]

    def test_sentence_fill_projection_builds_axis_projection_and_contracts(self) -> None:
        projection, target_profile, fit = self.service.project(
            question_type_config=self.config,
            pattern=self.pattern,
            resolved_slots={
                "blank_position": "middle",
                "function_type": "bridge",
                "logic_relation": "multi_constraint",
                "context_dependency": "high",
                "reference_dependency": "high",
                "bidirectional_validation": "high",
                "distractor_strength": "high",
            },
            difficulty_target="hard",
        )

        self.assertEqual(projection.target_difficulty, "hard")
        self.assertEqual(
            set(projection.axis_projection.keys()),
            {
                "local_binding_complexity",
                "global_context_dependency",
                "distractor_similarity",
                "blank_function_ambiguity",
            },
        )
        self.assertEqual(
            projection.validator_contract["difficulty_control"]["axis_targets"]["local_binding_complexity"],
            0.78,
        )
        self.assertEqual(target_profile.complexity.min, 0.68)
        self.assertEqual(fit.target_difficulty, "hard")

    def test_build_prompt_sections_reads_yaml_prompt_assets(self) -> None:
        projection, _, _ = self.service.project(
            question_type_config=self.config,
            pattern=self.pattern,
            resolved_slots={"blank_position": "opening", "function_type": "summary"},
            difficulty_target="easy",
        )

        sections = self.service.build_prompt_sections(projection=projection)

        self.assertTrue(any("Difficulty control is a first-class contract" in line for line in sections))
        self.assertTrue(any("sentence_fill" in line for line in sections))
        self.assertTrue(any(line.startswith("axis_projection:") for line in sections))

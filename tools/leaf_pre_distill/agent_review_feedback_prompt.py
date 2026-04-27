from __future__ import annotations

import json
from typing import Any


def build_agent_review_feedback_messages(feedback_input: dict[str, Any]) -> list[dict[str, str]]:
    output_schema = {
        "normalized_feedback": [
            {
                "dimension": "one allowed dimension",
                "severity": "low|medium|high",
                "target_line": "question_card|material_line|prompt_assets|validator|runtime|unknown",
                "evidence_hint": "short evidence clue from user feedback",
                "suggested_next_action": "short next action",
                "requires_regression": True,
                "requires_human_review": True,
            }
        ],
        "warnings": ["string"],
    }
    user_prompt = (
        "TASK:\n"
        "Normalize the human natural-language review feedback into structured evidence. "
        "User feedback is evidence only. Do not create config patches, do not write card specs, "
        "do not decide promotion, and do not formalize anything.\n\n"
        "FEEDBACK_INPUT:\n"
        f"{json.dumps(feedback_input, ensure_ascii=False, sort_keys=True)}\n\n"
        "ALLOWED_DIMENSIONS:\n"
        "difficulty_too_low, difficulty_too_high, exam_style_mismatch, distractor_weakness, "
        "answer_too_obvious, explanation_weak, family_fit_mismatch, reasoning_depth_insufficient, "
        "material_too_short, material_too_long, context_dependency_insufficient, source_like_material_weak, "
        "question_bank_style_contamination, material_noise_high, material_information_density_low, "
        "prompt_instruction_weak, validator_too_loose, validator_too_strict, runtime_binding_unclear, "
        "material_bridge_mismatch\n\n"
        "OUTPUT_SCHEMA:\n"
        f"{json.dumps(output_schema, ensure_ascii=False, sort_keys=True)}\n\n"
        "Return JSON only."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a cautious review-feedback normalizer for a question-card distillation lab. "
                "You convert user comments into structured evidence. You never modify formal configs."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]


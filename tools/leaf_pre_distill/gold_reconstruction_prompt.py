from __future__ import annotations

import json
from typing import Any


def gold_reconstruction_output_schema() -> dict[str, Any]:
    return {
        "sample_id": "string",
        "reconstruction_version": "v1",
        "question_family_guess": "string",
        "leaf_label_guess": "string",
        "reconstruction_summary": {
            "what_was_reconstructed": "string",
            "why_this_reconstruction_is_needed": "string",
            "confidence": "high | medium | low",
            "needs_human_review": "boolean",
            "warnings": ["string"],
        },
        "gold_material": {
            "restored_text": "string",
            "context_window": "string",
            "material_units": ["string"],
            "evidence_units": ["string"],
            "material_boundary_note": "string",
        },
        "gold_question": {
            "stem": "string",
            "options": "object",
            "answer": "string",
            "correct_option_text": "string",
        },
        "answer_mechanism": {
            "core_reasoning": "string",
            "uniqueness_source": "string",
            "evidence_mapping": ["object"],
        },
        "distractor_mechanism": {
            "distractor_modes": ["string"],
            "easy_wrong_reason": "string",
            "option_diagnostics": "object",
        },
        "gold_quality_flags": {
            "is_reconstructable": "boolean",
            "missing_information": ["string"],
            "ambiguous_points": ["string"],
            "requires_source_article": "boolean",
            "question_wrapper_leakage_risk": "low | medium | high",
            "overfit_risk_note": "string",
        },
    }


def build_gold_reconstruction_messages(input_row: dict[str, Any]) -> list[dict[str, str]]:
    input_json = json.dumps(input_row, ensure_ascii=False, sort_keys=True)
    schema_json = json.dumps(gold_reconstruction_output_schema(), ensure_ascii=False, sort_keys=True)
    return [
        {
            "role": "system",
            "content": (
                "You are a truth-gold reconstruction parser. "
                "You do not create new questions. "
                "You reconstruct a standard gold schema from the provided true question. "
                "You decide what needs to be reconstructed based on the true question itself. "
                "If uncertain, mark needs_human_review=true. Return JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                "TASK:\n"
                "Read the true question package. Determine what must be reconstructed for this sample to become "
                "a reliable gold reference. Fill the unified schema. Do not invent missing material. Do not rewrite "
                "the question as a new question. Do not convert hypotheses into formal fields. Do not generate prompt "
                "guards, validator rules, or card specs. If a field is not applicable, leave it empty and explain in "
                "warnings or missing_information. If the source article is required but not present, set "
                "requires_source_article=true. If evidence is unclear, set needs_human_review=true.\n\n"
                "Examples of reconstruction may include restoring a coherent material text, identifying context "
                "windows, preserving option/answer structure, or explaining why no reconstruction is possible.\n\n"
                "SOURCE-LIKE MATERIAL RULES:\n"
                "- gold_material.restored_text is only for natural source-like material: article sentences, context, "
                "or passage fragments that could plausibly appear in the original source.\n"
                "- Do not put question wrappers, exam wording, option text, answer explanations, or training-site "
                "boilerplate into gold_material.restored_text.\n"
                "- Forbidden in gold_material.restored_text: question stem wording, option labels, answer/explanation "
                "boilerplate, exam meta language, 下列, 正确的是, 不正确的是, 本题考查, 答案解析, 加点词, 选项, "
                "结合上下文选择, 文中 as part of an exam question wrapper.\n"
                "- If only question wording is available, do not fabricate article sentences. Leave restored_text "
                "empty or keep only reliable source-like fragments, set gold_quality_flags.requires_source_article=true, "
                "set reconstruction_summary.needs_human_review=true, lower confidence, and add a warning such as "
                "source-like material insufficient.\n"
                "- answer_mechanism and distractor_mechanism may preserve question or explanation information, but "
                "gold_material.restored_text must remain source-like material only.\n"
                "- Always set gold_quality_flags.question_wrapper_leakage_risk to low, medium, or high.\n\n"
                "TRUE_QUESTION_PACKAGE:\n"
                f"{input_json}\n\n"
                "OUTPUT_SCHEMA:\n"
                f"{schema_json}\n\n"
                "Return exactly one JSON object matching the unified schema. "
                "Only use TRUE_QUESTION_PACKAGE as source material. "
                "Do not treat TASK or OUTPUT_SCHEMA as source material."
            ),
        },
    ]

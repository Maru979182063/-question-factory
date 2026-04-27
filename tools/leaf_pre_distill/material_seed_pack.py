from __future__ import annotations

from typing import Any


NEGATIVE_SOURCE_PATTERNS = [
    "question_bank_page",
    "answer_explanation_page",
    "training_homework_page",
]


def build_initial_material_seed_pack(
    *,
    manifest: dict[str, Any],
    query_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seeds: list[dict[str, Any]] = []
    for index, row in enumerate(query_rows):
        if row.get("status") == "blocked":
            continue
        searches = row.get("search_queries") or []
        seed_type = "original_source_query" if row.get("requires_source_article") else "similar_material_query"
        if not searches:
            seed_type = "context_pattern_seed"
        seeds.append(
            {
                "seed_id": f"{row.get('sample_id') or index}:material_seed:v1",
                "sample_id": row.get("sample_id") or f"sample-{index}",
                "seed_version": "v1",
                "source": row.get("gold_source") or "gold_reconstruction",
                "material_seed_type": seed_type,
                "restored_human_material": row.get("restored_human_material") or "",
                "material_requirements": {
                    "text_type": row.get("likely_source_type") or "unknown",
                    "length_hint": _length_hint(row.get("restored_human_material") or ""),
                    "context_dependency": _context_dependency(row),
                    "must_contain": _must_contain(searches),
                    "must_avoid": list(row.get("anti_question_bank_terms") or []),
                    "usable_for_question_family": manifest.get("mother_family_id") or "",
                    "usable_for_leaf": manifest.get("child_family_id") or manifest.get("leaf_label") or "",
                },
                "search_queries": searches,
                "negative_source_patterns": list(NEGATIVE_SOURCE_PATTERNS),
                "status": "seed_only",
                "formalized": False,
                "needs_human_review": bool(row.get("needs_human_review")),
                "warnings": list(row.get("warnings") or []),
            }
        )
    return seeds


def _length_hint(text: str) -> str:
    length = len(text)
    if length >= 800:
        return "long_source_or_article"
    if length >= 240:
        return "medium_context_window"
    if length >= 80:
        return "short_context_window"
    return "insufficient_material"


def _context_dependency(row: dict[str, Any]) -> str:
    if row.get("requires_source_article"):
        return "requires_original_source_article"
    if row.get("restored_human_material"):
        return "context_window_available_but_source_unverified"
    return "insufficient_context"


def _must_contain(searches: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for item in searches[:3]:
        query = str(item.get("query") or "").strip()
        if query and query not in terms:
            terms.append(query)
    return terms

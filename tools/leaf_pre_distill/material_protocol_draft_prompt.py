from __future__ import annotations

import json
from typing import Any


def build_material_protocol_draft_messages(digest: dict[str, Any]) -> list[dict[str, str]]:
    schema = {
        "bundle_version": "v1",
        "status": "draft_only",
        "formalized": False,
        "writeback_allowed": False,
        "requires_human_review": True,
        "requires_regression": True,
        "material_card_draft": {},
        "material_line_prompt_assets_draft": {},
        "material_quality_regression_draft": {},
        "material_review_prompts_markdown": "",
        "material_bridge_mapping_draft": {},
        "evidence_gaps": [],
        "next_required_evidence": [],
        "limits": [],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a material-line protocol draft assistant.\n"
                "You generate draft-only protocol assets from evidence digest and repository alignment findings.\n"
                "You must not confirm original sources, write formal material cards, modify card_specs, modify runtime mappings, "
                "modify prompt assets, modify validator contracts, modify question cards, promote materials, call material ingest, "
                "or treat a sample family as a universal rule.\n"
                "All outputs must be JSON only. All assets must remain status=draft_only, formalized=false, "
                "writeback_allowed=false, requires_human_review=true, requires_regression=true.\n"
                "If evidence is missing, write evidence_gaps. Use repository-confirmed fields when available; mark other fields as proposed/draft."
            ),
        },
        {
            "role": "user",
            "content": (
                "TASK:\n"
                "Generate a reusable material-line protocol draft bundle for the current family_context.\n"
                "Do not hard-code any specific family. Use the family_context from the digest.\n"
                "CRITICAL: Copy EVIDENCE_DIGEST.family_context into material_card_draft.family_binding exactly, byte-for-byte for every key and value. "
                "Do not translate, rename, infer, normalize, shorten, or replace any family_context value.\n"
                "Use system_alignment_findings to decide which fields are repository-confirmed.\n"
                "CRITICAL: material_bridge_mapping_draft must include system_alignment_findings_ref=\"system_alignment_findings.json\" "
                "and mapping_rationale.source=\"system_alignment_findings\".\n"
                "Explain which outputs are evidence-backed, which are hypothesis-only, and which future evidence is required.\n"
                "Do not formalize anything.\n\n"
                "EVIDENCE_DIGEST:\n"
                f"{json.dumps(digest, ensure_ascii=False, indent=2)}\n\n"
                "OUTPUT_SCHEMA:\n"
                f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
                "Return exactly one JSON object. Do not wrap it in markdown."
            ),
        },
    ]

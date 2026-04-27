from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.llm_field_probe import (
    ChatClient,
    OpenAICompatibleChatClient,
    _parse_json_output,
)
from tools.leaf_pre_distill.source_candidate_search import (
    classify_source_risk,
    domain_from_url,
    lexical_overlap,
    truncate_text,
)


SOURCE_TEXT_ARTIFACTS = {
    "source_text_evidence_approval": "source_text_evidence_approval.json",
    "source_text_evidence_manifest": "source_text_evidence_manifest.json",
    "source_text_evidence_results": "source_text_evidence_results.jsonl",
    "source_text_evidence_report": "source_text_evidence_report.md",
    "source_gold_alignment_results": "source_gold_alignment_results.jsonl",
    "source_gold_alignment_summary": "source_gold_alignment_summary.json",
    "source_gold_alignment_report": "source_gold_alignment_report.md",
    "source_gold_alignment_review": "source_gold_alignment_review.json",
    "material_quality_regression_results": "material_quality_regression_results.json",
    "material_quality_regression_report": "material_quality_regression_report.md",
    "material_quality_review": "material_quality_review.json",
}


def run_material_evidence_alignment_regression(
    *,
    output_dir: str | Path,
    source_seed_registry_path: str | Path,
    crawl_seed_manifest_path: str | Path | None = None,
    source_text_evidence_approval_path: str | Path | None = None,
    source_text_evidence_approval: dict[str, Any] | None = None,
    source_text_manual_results_path: str | Path | None = None,
    gold_reconstruction_results_path: str | Path | None = None,
    material_card_draft_path: str | Path | None = None,
    material_quality_regression_draft_path: str | Path | None = None,
    agent_review_feedback_normalized_path: str | Path | None = None,
    source_text_mode: str = "mock",
    alignment_mode: str = "mock",
    alignment_model: str = "chat",
    alignment_base_url: str | None = None,
    alignment_api_key_env: str = "LEAF_PRE_DISTILL_LLM_API_KEY",
    alignment_timeout_seconds: int = 30,
    alignment_max_output_tokens: int = 900,
    alignment_client: ChatClient | None = None,
) -> dict[str, str]:
    if source_text_mode not in {"manual", "mock"}:
        raise ValueError("source text evidence mode must be manual or mock.")
    if alignment_mode not in {"dry-run", "mock", "llm"}:
        raise ValueError("source/gold alignment mode must be dry-run, mock, or llm.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    seeds_path = Path(source_seed_registry_path)
    approval = load_approval(
        approval_path=source_text_evidence_approval_path,
        approval_payload=source_text_evidence_approval,
        source_seed_registry_path=seeds_path,
    )
    seeds = load_jsonl(seeds_path)
    manual_texts = load_manual_source_texts(source_text_manual_results_path)
    crawl_manifest = load_json(crawl_seed_manifest_path) if crawl_seed_manifest_path else {}

    source_manifest, source_rows = build_source_text_evidence(
        seeds=seeds,
        approval=approval,
        source_seed_registry_path=seeds_path,
        crawl_seed_manifest_path=Path(crawl_seed_manifest_path) if crawl_seed_manifest_path else None,
        manual_texts=manual_texts,
        mode=source_text_mode,
    )
    source_report = render_source_text_evidence_report(source_manifest, source_rows, crawl_manifest)

    gold_rows = load_jsonl(gold_reconstruction_results_path) if gold_reconstruction_results_path else []
    alignment_rows, alignment_summary = build_source_gold_alignment(
        source_rows=source_rows,
        gold_rows=gold_rows,
        mode=alignment_mode,
        model=alignment_model,
        base_url=alignment_base_url,
        api_key_env=alignment_api_key_env,
        timeout_seconds=alignment_timeout_seconds,
        max_output_tokens=alignment_max_output_tokens,
        client=alignment_client,
    )
    alignment_report = render_source_gold_alignment_report(alignment_summary, alignment_rows)
    alignment_review = build_source_gold_alignment_review(alignment_summary, alignment_rows)

    material_quality = build_material_quality_regression(
        gold_rows=gold_rows,
        source_rows=source_rows,
        alignment_rows=alignment_rows,
        material_card_draft=load_json(material_card_draft_path) if material_card_draft_path else {},
        material_quality_regression_draft=load_json(material_quality_regression_draft_path) if material_quality_regression_draft_path else {},
        agent_review_feedback=load_json(agent_review_feedback_normalized_path) if agent_review_feedback_normalized_path else {},
    )
    material_quality_report = render_material_quality_regression_report(material_quality)
    material_quality_review = build_material_quality_review(material_quality)

    artifacts: dict[str, str] = {}
    approval_path = output_path / SOURCE_TEXT_ARTIFACTS["source_text_evidence_approval"]
    manifest_path = output_path / SOURCE_TEXT_ARTIFACTS["source_text_evidence_manifest"]
    source_rows_path = output_path / SOURCE_TEXT_ARTIFACTS["source_text_evidence_results"]
    source_report_path = output_path / SOURCE_TEXT_ARTIFACTS["source_text_evidence_report"]
    alignment_rows_path = output_path / SOURCE_TEXT_ARTIFACTS["source_gold_alignment_results"]
    alignment_summary_path = output_path / SOURCE_TEXT_ARTIFACTS["source_gold_alignment_summary"]
    alignment_report_path = output_path / SOURCE_TEXT_ARTIFACTS["source_gold_alignment_report"]
    alignment_review_path = output_path / SOURCE_TEXT_ARTIFACTS["source_gold_alignment_review"]
    quality_path = output_path / SOURCE_TEXT_ARTIFACTS["material_quality_regression_results"]
    quality_report_path = output_path / SOURCE_TEXT_ARTIFACTS["material_quality_regression_report"]
    quality_review_path = output_path / SOURCE_TEXT_ARTIFACTS["material_quality_review"]

    write_json(approval_path, approval)
    write_json(manifest_path, source_manifest)
    write_jsonl(source_rows_path, source_rows)
    source_report_path.write_text(source_report, encoding="utf-8")
    write_jsonl(alignment_rows_path, alignment_rows)
    write_json(alignment_summary_path, alignment_summary)
    alignment_report_path.write_text(alignment_report, encoding="utf-8")
    write_json(alignment_review_path, alignment_review)
    write_json(quality_path, material_quality)
    quality_report_path.write_text(material_quality_report, encoding="utf-8")
    write_json(quality_review_path, material_quality_review)

    for key, filename in SOURCE_TEXT_ARTIFACTS.items():
        artifacts[key] = str(output_path / filename)
    return artifacts


def load_approval(
    *,
    approval_path: str | Path | None,
    approval_payload: dict[str, Any] | None,
    source_seed_registry_path: Path,
) -> dict[str, Any]:
    if approval_payload is not None:
        approval = dict(approval_payload)
    elif approval_path is not None:
        approval = load_json(approval_path)
    else:
        approval = {
            "approval_version": "v1",
            "reviewer": "human",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "source_seed_registry_path": str(source_seed_registry_path),
            "approved_seed_ids": [],
            "limits": {"max_urls": 0, "allowed_domains": [], "blocked_domains": [], "allow_risky_seed": False},
            "approval_scope": "prepare_source_text_evidence_only",
            "does_not_confirm_original_source": True,
            "does_not_allow_material_library_write": True,
            "does_not_allow_material_card_write": True,
        }
    approval.setdefault("approval_version", "v1")
    approval.setdefault("reviewer", "human")
    approval.setdefault("approved_at", datetime.now(timezone.utc).isoformat())
    approval.setdefault("source_seed_registry_path", str(source_seed_registry_path))
    approval.setdefault("approved_seed_ids", [])
    approval.setdefault("limits", {})
    approval.setdefault("approval_scope", "prepare_source_text_evidence_only")
    approval["does_not_confirm_original_source"] = True
    approval["does_not_allow_material_library_write"] = True
    approval["does_not_allow_material_card_write"] = True
    return approval


def build_source_text_evidence(
    *,
    seeds: list[dict[str, Any]],
    approval: dict[str, Any],
    source_seed_registry_path: Path,
    crawl_seed_manifest_path: Path | None,
    manual_texts: dict[str, dict[str, Any]],
    mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    approved_ids = {str(value) for value in (approval.get("approved_seed_ids") or [])}
    limits = approval.get("limits") or {}
    max_urls = int(limits.get("max_urls") or len(approved_ids) or 0)
    allowed_domains = {str(value).lower() for value in (limits.get("allowed_domains") or [])}
    blocked_domains = {str(value).lower() for value in (limits.get("blocked_domains") or [])}
    allow_risky = bool(limits.get("allow_risky_seed"))

    rows: list[dict[str, Any]] = []
    selected_count = 0
    for seed in seeds:
        seed_id = str(seed.get("seed_id") or "")
        if seed_id not in approved_ids:
            continue
        if selected_count >= max_urls:
            rows.append(source_text_blocked_row(seed, "approval_max_urls_exceeded"))
            continue
        domain = str(seed.get("domain") or domain_from_url(str(seed.get("url") or ""))).lower()
        source_risk = str(seed.get("source_risk") or "unknown")
        if domain in blocked_domains:
            rows.append(source_text_blocked_row(seed, "domain_blocked_by_approval"))
            continue
        if allowed_domains and domain not in allowed_domains:
            rows.append(source_text_blocked_row(seed, "domain_not_allowed_by_approval"))
            continue
        if source_risk in {"question_bank_like", "exam_training_like"} and not allow_risky:
            rows.append(source_text_blocked_row(seed, "risky_seed_not_allowed_for_source_text_evidence"))
            continue

        selected_count += 1
        manual = manual_texts.get(seed_id) or manual_texts.get(str(seed.get("url") or ""))
        rows.append(source_text_row_from_seed(seed=seed, manual=manual, mode=mode))

    missing_approved = approved_ids - {str(seed.get("seed_id") or "") for seed in seeds}
    for seed_id in sorted(missing_approved):
        rows.append(
            {
                "evidence_version": "v1",
                "seed_id": seed_id,
                "sample_id": "",
                "url": "",
                "domain": "",
                "source_use": "unknown",
                "text_status": "blocked",
                "title": "",
                "text_excerpt": "",
                "text_hash": "",
                "text_length": 0,
                "boilerplate_risk": "unknown",
                "question_bank_contamination_risk": "unknown",
                "verified_original_source": False,
                "verified": False,
                "formalized": False,
                "warnings": ["approved_seed_not_found"],
                "requires_human_review": True,
            }
        )

    status_counts = Counter(row.get("text_status") or "unknown" for row in rows)
    manifest = {
        "evidence_version": "v1",
        "status": "completed" if rows else "blocked",
        "mode": mode,
        "source_seed_registry_path": str(source_seed_registry_path),
        "crawl_seed_manifest_path": str(crawl_seed_manifest_path or ""),
        "approval_scope": approval.get("approval_scope"),
        "approved_seed_count": len(approved_ids),
        "result_count": len(rows),
        "available_count": status_counts.get("available", 0),
        "blocked_count": status_counts.get("blocked", 0),
        "failed_count": status_counts.get("failed", 0),
        "manual_required_count": status_counts.get("manual_required", 0),
        "verified_original_source_count": 0,
        "verified_count": 0,
        "ready_for_source_gold_alignment": bool(status_counts.get("available", 0)),
        "requires_human_review": True,
        "material_library_write": False,
        "material_card_write": False,
        "limits": [
            "Source text evidence approval does not confirm original source.",
            "Source text evidence is not a material library write.",
            "Source text evidence is not material_card writeback.",
        ],
    }
    return manifest, enforce_unverified(rows)


def source_text_row_from_seed(*, seed: dict[str, Any], manual: dict[str, Any] | None, mode: str) -> dict[str, Any]:
    warnings: list[str] = []
    text = ""
    if manual:
        text = str(manual.get("text") or manual.get("text_excerpt") or "")
    elif mode == "mock":
        text = " ".join(part for part in (str(seed.get("title") or ""), str(seed.get("snippet") or "")) if part).strip()
        warnings.append("mock_source_text_from_seed_metadata")
    if not text:
        status = "manual_required"
        warnings.append("source_text_not_available_without_manual_input")
    else:
        status = "available"
    title = str((manual or {}).get("title") or seed.get("title") or "")
    url = str(seed.get("url") or "")
    domain = str(seed.get("domain") or domain_from_url(url))
    risk = classify_source_risk(title=title, url=url, domain=domain, snippet=text)
    return {
        "evidence_version": "v1",
        "seed_id": seed.get("seed_id") or "",
        "sample_id": seed.get("sample_id") or "",
        "url": url,
        "domain": domain,
        "source_use": seed.get("source_use") or "unknown",
        "text_status": status,
        "title": title,
        "text_excerpt": truncate_text(text, 1200),
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        "text_length": len(text),
        "boilerplate_risk": boilerplate_risk(text),
        "question_bank_contamination_risk": "high" if risk in {"question_bank_like", "exam_training_like"} else risk,
        "verified_original_source": False,
        "verified": False,
        "formalized": False,
        "warnings": dedupe(warnings),
        "requires_human_review": True,
    }


def source_text_blocked_row(seed: dict[str, Any], warning: str) -> dict[str, Any]:
    return {
        "evidence_version": "v1",
        "seed_id": seed.get("seed_id") or "",
        "sample_id": seed.get("sample_id") or "",
        "url": seed.get("url") or "",
        "domain": seed.get("domain") or "",
        "source_use": seed.get("source_use") or "unknown",
        "text_status": "blocked",
        "title": seed.get("title") or "",
        "text_excerpt": "",
        "text_hash": "",
        "text_length": 0,
        "boilerplate_risk": "unknown",
        "question_bank_contamination_risk": "unknown",
        "verified_original_source": False,
        "verified": False,
        "formalized": False,
        "warnings": [warning],
        "requires_human_review": True,
    }


def build_source_gold_alignment(
    *,
    source_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    mode: str,
    model: str = "chat",
    base_url: str | None = None,
    api_key_env: str = "LEAF_PRE_DISTILL_LLM_API_KEY",
    timeout_seconds: int = 30,
    max_output_tokens: int = 900,
    client: ChatClient | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gold_by_sample = {str(row.get("sample_id") or ""): row for row in gold_rows}
    rows: list[dict[str, Any]] = []
    active_client: ChatClient | None = None
    if mode == "llm":
        active_client = client or OpenAICompatibleChatClient(
            base_url=base_url,
            api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
        )
    for source in source_rows:
        gold = gold_by_sample.get(str(source.get("sample_id") or ""))
        rows.append(
            build_alignment_row(
                source=source,
                gold=gold,
                mode=mode,
                model=model,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
                client=active_client,
            )
        )
    status_counts = Counter(row.get("alignment_status") or "unknown" for row in rows)
    relationship_counts = Counter(row.get("relationship") or "unknown" for row in rows)
    summary = {
        "alignment_version": "v1",
        "status": "completed" if rows else "blocked",
        "mode": mode,
        "alignment_count": len(rows),
        "status_counts": dict(status_counts),
        "relationship_counts": dict(relationship_counts),
        "blocked_count": status_counts.get("blocked", 0),
        "needs_human_review_count": sum(1 for row in rows if row.get("requires_human_review")),
        "verified_original_source_count": 0,
        "verified_count": 0,
        "ready_for_material_quality_regression": bool(rows),
        "ready_for_material_card_draft": False,
        "limits": [
            "Alignment is not source verification.",
            "Original-source candidate remains unverified until explicit source verification.",
            "Similar material cannot be treated as original source.",
        ],
    }
    return enforce_unverified(rows), summary


def build_alignment_row(
    *,
    source: dict[str, Any],
    gold: dict[str, Any] | None,
    mode: str,
    model: str = "chat",
    timeout_seconds: int = 30,
    max_output_tokens: int = 900,
    client: ChatClient | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    text = str(source.get("text_excerpt") or "")
    gold_material = (gold or {}).get("gold_material") or {}
    gold_text = " ".join(
        str(part or "")
        for part in (
            gold_material.get("restored_text"),
            gold_material.get("context_window"),
            " ".join(gold_material.get("evidence_units") or []),
        )
        if part
    )
    if mode == "dry-run":
        status = "needs_human_review"
        relationship = "unknown"
        confidence = "low"
        overlap = 0.0
        warnings.append("alignment_dry_run_no_semantic_judgment")
    elif source.get("text_status") != "available":
        status = "blocked"
        relationship = "unknown"
        confidence = "low"
        overlap = 0.0
        warnings.append("source_text_unavailable")
    elif not gold:
        status = "blocked"
        relationship = "unknown"
        confidence = "low"
        overlap = 0.0
        warnings.append("gold_reconstruction_missing")
    elif str(source.get("question_bank_contamination_risk")) == "high":
        status = "blocked"
        relationship = "question_bank_pollution"
        confidence = "medium"
        overlap = lexical_overlap(text, gold_text)
        warnings.append("source_text_has_question_bank_contamination_risk")
    elif mode == "llm" and client is not None:
        overlap = max(lexical_overlap(text, gold_text), lexical_overlap(gold_text, text))
        llm_row = run_llm_alignment_judgment(
            source=source,
            gold=gold,
            model=model,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            client=client,
            overlap=overlap,
        )
        llm_row["verified_original_source"] = False
        llm_row["verified"] = False
        llm_row["formalized"] = False
        llm_row["requires_human_review"] = True
        return llm_row
    else:
        overlap = max(lexical_overlap(text, gold_text), lexical_overlap(gold_text, text))
        if overlap >= 0.45:
            status = "aligned"
            relationship = "original_source_candidate" if source.get("source_use") == "original_source_candidate" else "similar_material"
            confidence = "medium"
        elif overlap >= 0.18:
            status = "partial"
            relationship = "similar_material" if source.get("source_use") == "similar_material" else "topic_related"
            confidence = "medium"
        elif text and gold_text:
            status = "weak"
            relationship = "topic_related"
            confidence = "low"
            warnings.append("low_lexical_overlap_requires_human_review")
        else:
            status = "needs_human_review"
            relationship = "unknown"
            confidence = "low"
            warnings.append("insufficient_text_for_alignment")

    return {
        "alignment_version": "v1",
        "sample_id": source.get("sample_id") or "",
        "seed_id": source.get("seed_id") or "",
        "url": source.get("url") or "",
        "alignment_status": status,
        "relationship": relationship,
        "confidence": confidence,
        "matched_spans": build_matched_spans(text, gold_text, overlap),
        "gold_material_refs": [gold.get("sample_id")] if gold else [],
        "transformation_hypothesis": {
            "possible_extraction": status in {"aligned", "partial"},
            "possible_compression": status in {"aligned", "partial"},
            "possible_rewrite": status in {"partial", "weak"},
            "possible_splicing": False,
            "notes": "Heuristic v1 only; model or human review is still required.",
        },
        "overlap_score": round(overlap, 4),
        "verified_original_source": False,
        "verified": False,
        "formalized": False,
        "requires_human_review": True,
        "warnings": dedupe(warnings),
    }


def run_llm_alignment_judgment(
    *,
    source: dict[str, Any],
    gold: dict[str, Any],
    model: str,
    timeout_seconds: int,
    max_output_tokens: int,
    client: ChatClient,
    overlap: float,
) -> dict[str, Any]:
    try:
        raw = client.complete(
            messages=build_alignment_messages(source=source, gold=gold, overlap=overlap),
            model=model,
            timeout_seconds=timeout_seconds,
            temperature=0.1,
            max_tokens=max_output_tokens,
        )
        parsed = _parse_json_output(raw)
        status = str(parsed.get("alignment_status") or "needs_human_review")
        if status not in {"aligned", "partial", "weak", "irrelevant", "blocked", "needs_human_review"}:
            status = "needs_human_review"
        relationship = str(parsed.get("relationship") or "unknown")
        if relationship not in {"original_source_candidate", "similar_material", "topic_related", "question_bank_pollution", "unknown"}:
            relationship = "unknown"
        confidence = str(parsed.get("confidence") or "low")
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        warnings = [str(item) for item in (parsed.get("warnings") or []) if str(item or "").strip()]
        if parsed.get("verified") or parsed.get("verified_original_source"):
            warnings.append("model_verification_claim_ignored")
        hypothesis = parsed.get("transformation_hypothesis") if isinstance(parsed.get("transformation_hypothesis"), dict) else {}
        return {
            "alignment_version": "v1",
            "sample_id": source.get("sample_id") or "",
            "seed_id": source.get("seed_id") or "",
            "url": source.get("url") or "",
            "alignment_status": status,
            "relationship": relationship,
            "confidence": confidence,
            "matched_spans": normalize_matched_spans(parsed.get("matched_spans"), source, gold, overlap),
            "gold_material_refs": [gold.get("sample_id")] if gold else [],
            "transformation_hypothesis": {
                "possible_extraction": bool(hypothesis.get("possible_extraction")),
                "possible_compression": bool(hypothesis.get("possible_compression")),
                "possible_rewrite": bool(hypothesis.get("possible_rewrite")),
                "possible_splicing": bool(hypothesis.get("possible_splicing")),
                "notes": str(hypothesis.get("notes") or parsed.get("notes") or "LLM-assisted judgment; requires human review."),
            },
            "overlap_score": round(overlap, 4),
            "llm_assisted": True,
            "verified_original_source": False,
            "verified": False,
            "formalized": False,
            "requires_human_review": True,
            "warnings": dedupe(warnings),
        }
    except Exception as exc:
        fallback = build_alignment_row(source=source, gold=gold, mode="mock")
        fallback["alignment_status"] = "needs_human_review"
        fallback["confidence"] = "low"
        fallback["llm_assisted"] = False
        fallback["warnings"] = dedupe((fallback.get("warnings") or []) + [f"llm_alignment_failed: {exc}"])
        return fallback


def build_alignment_messages(*, source: dict[str, Any], gold: dict[str, Any], overlap: float) -> list[dict[str, str]]:
    gold_material = gold.get("gold_material") or {}
    digest = {
        "sample_id": source.get("sample_id"),
        "seed_id": source.get("seed_id"),
        "source_use": source.get("source_use"),
        "url": source.get("url"),
        "title": source.get("title"),
        "source_text_excerpt": truncate_text(source.get("text_excerpt") or "", 1600),
        "source_text_status": source.get("text_status"),
        "question_bank_contamination_risk": source.get("question_bank_contamination_risk"),
        "gold_restored_text": truncate_text(gold_material.get("restored_text") or "", 1600),
        "gold_context_window": truncate_text(gold_material.get("context_window") or "", 800),
        "gold_evidence_units": (gold_material.get("evidence_units") or [])[:6],
        "heuristic_overlap": round(overlap, 4),
    }
    schema = {
        "alignment_status": "aligned|partial|weak|irrelevant|blocked|needs_human_review",
        "relationship": "original_source_candidate|similar_material|topic_related|question_bank_pollution|unknown",
        "confidence": "low|medium|high",
        "matched_spans": [{"source_excerpt": "string", "gold_excerpt": "string", "note": "string"}],
        "transformation_hypothesis": {
            "possible_extraction": False,
            "possible_compression": False,
            "possible_rewrite": False,
            "possible_splicing": False,
            "notes": "string",
        },
        "warnings": ["string"],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a cautious material evidence alignment reviewer. "
                "You compare source text evidence with reconstructed gold material. "
                "You cannot verify original source, cannot set verified=true, cannot approve material_card, and must return JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                "TASK:\n"
                "Judge the relationship between SOURCE_TEXT_EVIDENCE and RECONSTRUCTED_GOLD. "
                "Decide whether it is an original-source candidate, similar material, topic-related, question-bank pollution, or unknown. "
                "If uncertain, use needs_human_review and low confidence. Do not claim source verification.\n\n"
                f"EVIDENCE_DIGEST:\n{json.dumps(digest, ensure_ascii=False, sort_keys=True)}\n\n"
                f"OUTPUT_SCHEMA:\n{json.dumps(schema, ensure_ascii=False, sort_keys=True)}\n\n"
                "Return JSON only. Do not treat this prompt as source material."
            ),
        },
    ]


def normalize_matched_spans(value: Any, source: dict[str, Any], gold: dict[str, Any], overlap: float) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value[:5]:
            if isinstance(item, dict):
                spans.append(
                    {
                        "source_excerpt": truncate_text(item.get("source_excerpt") or item.get("source") or "", 240),
                        "gold_excerpt": truncate_text(item.get("gold_excerpt") or item.get("gold") or "", 240),
                        "note": truncate_text(item.get("note") or item.get("reason") or "", 240),
                        "method": "llm",
                    }
                )
    if spans:
        return spans
    gold_material = gold.get("gold_material") or {}
    return build_matched_spans(
        str(source.get("text_excerpt") or ""),
        " ".join(str(part or "") for part in (gold_material.get("restored_text"), gold_material.get("context_window"))),
        overlap,
    )


def build_material_quality_regression(
    *,
    gold_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    alignment_rows: list[dict[str, Any]],
    material_card_draft: dict[str, Any],
    material_quality_regression_draft: dict[str, Any],
    agent_review_feedback: dict[str, Any],
) -> dict[str, Any]:
    available_sources = [row for row in source_rows if row.get("text_status") == "available"]
    non_polluted_sources = [row for row in available_sources if row.get("question_bank_contamination_risk") != "high"]
    useful_alignments = [row for row in alignment_rows if row.get("alignment_status") in {"aligned", "partial"}]
    feedback_items = agent_review_feedback.get("normalized_feedback") or []
    material_feedback = [item for item in feedback_items if item.get("target_line") == "material_line"]
    dimensions = [
        quality_dimension(
            "source_provenance_status",
            "Track whether source candidates have body evidence and whether any verified provenance exists.",
            "warning" if available_sources else "blocked",
            "source_text_evidence_results",
            "heuristic",
            "medium",
            True,
            "All source evidence remains unverified; low contamination does not confirm original source.",
        ),
        quality_dimension(
            "question_bank_contamination",
            "Check whether collected source text still looks like question-bank or exam-training content.",
            "pass" if non_polluted_sources and len(non_polluted_sources) == len(available_sources) else ("fail" if available_sources else "blocked"),
            "source_text_evidence_results.question_bank_contamination_risk",
            "heuristic",
            "medium",
            bool(not non_polluted_sources),
            "Risk terms are heuristic only and require human review.",
        ),
        quality_dimension(
            "source_gold_alignment",
            "Assess whether source text evidence can support reconstructed gold material.",
            "warning" if useful_alignments else "blocked",
            "source_gold_alignment_results",
            "mixed",
            "low",
            True,
            "Alignment is not source verification and cannot approve material_card formalization.",
        ),
        quality_dimension(
            "material_independence",
            "Check whether material evidence can stand apart from the original question wrapper.",
            "warning" if available_sources else "blocked",
            "source_text_evidence_results.text_excerpt",
            "heuristic",
            "low",
            True,
            "V1 does not fetch or clean full body text.",
        ),
        quality_dimension(
            "material_sufficiency",
            "Check whether available excerpts are long enough for future cleaning and slicing.",
            "warning" if any(int(row.get("text_length") or 0) >= 80 for row in available_sources) else "blocked",
            "source_text_evidence_results.text_length",
            "heuristic",
            "low",
            True,
            "Excerpt length is not semantic sufficiency.",
        ),
        quality_dimension(
            "context_dependency",
            "Check whether material evidence preserves enough context for the family.",
            "warning" if gold_rows and available_sources else "blocked",
            "gold_reconstruction_results + source_text_evidence_results",
            "model",
            "low",
            True,
            "Requires later model/human source-gold review.",
        ),
        quality_dimension(
            "slicing_potential",
            "Estimate whether future span selection is possible.",
            "warning" if useful_alignments else "blocked",
            "source_gold_alignment_results.matched_spans",
            "heuristic",
            "low",
            True,
            "No production material span is created in this gate.",
        ),
        quality_dimension(
            "family_fit",
            "Check whether material evidence appears usable for the current family.",
            "warning" if material_card_draft else "blocked",
            "material_card_draft + alignment evidence",
            "human",
            "low",
            True,
            "Family fit cannot be decided by statistics alone.",
        ),
        quality_dimension(
            "distractor_support",
            "Check whether material evidence can support plausible distractors.",
            "warning" if material_quality_regression_draft else "blocked",
            "material_quality_regression_draft",
            "unavailable",
            "low",
            True,
            "Requires generated comparison and human item review.",
        ),
        quality_dimension(
            "overfit_or_copy_risk",
            "Check whether material usage risks copying original question text or overfitting gold samples.",
            "warning",
            "gold_reconstruction_results + alignment overlap",
            "heuristic",
            "low",
            True,
            "High fit is not true question quality.",
        ),
        quality_dimension(
            "bridge_compatibility",
            "Check whether draft material evidence can later map into MaterialBridgeV2.",
            "warning" if material_card_draft else "blocked",
            "material_card_draft/material_bridge_mapping_draft",
            "metadata",
            "low",
            True,
            "No bridge request was executed and no runtime mapping was changed.",
        ),
        quality_dimension(
            "human_review_required",
            "Ensure human review remains mandatory before formalization.",
            "pass",
            "all material evidence artifacts",
            "human",
            "high",
            True,
            "Human review is required even when other dimensions pass.",
        ),
    ]
    blocking = [item for item in dimensions if item.get("blocking") and item.get("status") in {"fail", "blocked"}]
    unresolved_feedback = [
        item.get("dimension")
        for item in material_feedback
        if item.get("severity") == "high"
    ]
    if unresolved_feedback:
        blocking.append(
            {
                "dimension": "agent_review_feedback",
                "status": "blocked",
                "notes": f"Unresolved high-severity material feedback: {unresolved_feedback}",
            }
        )
    return {
        "regression_version": "v1",
        "status": "blocked" if blocking else "review_needed",
        "formalized": False,
        "writeback_allowed": False,
        "ready_for_material_card_formalization": False,
        "source_text_count": len(source_rows),
        "available_source_text_count": len(available_sources),
        "alignment_count": len(alignment_rows),
        "useful_alignment_count": len(useful_alignments),
        "verified_original_source_count": 0,
        "verified_count": 0,
        "dimensions": dimensions,
        "blocking_issues": [item.get("dimension") or item.get("notes") for item in blocking],
        "recommended_next_action": "human_material_review" if available_sources else "collect_source_text_evidence",
        "requires_human_review": True,
        "limits": [
            "Material quality regression is readiness evidence, not material_card approval.",
            "High score cannot automatically approve formalization.",
            "Low contamination does not equal verified source.",
        ],
    }


def quality_dimension(
    dimension: str,
    purpose: str,
    status: str,
    evidence: str,
    method: str,
    confidence: str,
    blocking: bool,
    notes: str,
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "purpose": purpose,
        "status": status,
        "evidence": evidence,
        "method": method,
        "confidence": confidence,
        "blocking": blocking,
        "notes": notes,
    }


def build_source_gold_alignment_review(summary: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "review_version": "v1",
        "status": "pending_human_review",
        "alignment_count": len(rows),
        "verified_original_source_count": 0,
        "requires_human_review": True,
        "review_questions": [
            "Does the source text actually support the reconstructed gold material?",
            "Is this an original-source candidate, similar material, or only topic-related evidence?",
            "Is any question-bank or exam-training contamination present?",
        ],
        "limits": [
            "This review placeholder does not confirm original source.",
            "No material_card or material library write is allowed from this artifact.",
        ],
    }


def build_material_quality_review(quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_version": "v1",
        "status": "pending_human_review",
        "material_quality_status": quality.get("status"),
        "ready_for_material_card_formalization": False,
        "verified_original_source_count": 0,
        "requires_human_review": True,
        "review_questions": [
            "Are the source text evidence and alignment good enough for a material-card draft iteration?",
            "Which blocking dimensions should be addressed before formalization?",
            "Does user feedback indicate unresolved material quality issues?",
        ],
        "limits": [
            "This review placeholder is not approval for writeback.",
            "No material_card, card_specs, runtime, prompt, validator, or generation change is made.",
        ],
    }


def render_source_text_evidence_report(manifest: dict[str, Any], rows: list[dict[str, Any]], crawl_manifest: dict[str, Any]) -> str:
    status_counts = Counter(row.get("text_status") or "unknown" for row in rows)
    lines = [
        "# Source Text Evidence Report",
        "",
        "> Source text evidence prepares reviewable body/excerpt evidence from human-reviewed seeds. It does not confirm original source, write material_card, or write a material library.",
        "",
        f"- status: `{manifest.get('status')}`",
        f"- mode: `{manifest.get('mode')}`",
        f"- approved_seed_count: `{manifest.get('approved_seed_count')}`",
        f"- result_count: `{manifest.get('result_count')}`",
        f"- status_counts: `{dict(status_counts)}`",
        f"- verified_original_source_count: `{manifest.get('verified_original_source_count')}`",
        f"- crawl_allowed: `{crawl_manifest.get('crawl_allowed', False)}`",
        f"- ready_for_source_gold_alignment: `{manifest.get('ready_for_source_gold_alignment')}`",
        "",
        "## Evidence Preview",
        "",
    ]
    for row in rows[:5]:
        lines.append(f"- `{row.get('sample_id')}` `{row.get('text_status')}` `{row.get('domain')}`: {truncate_text(row.get('text_excerpt') or row.get('title') or '', 120)}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- No original source was verified.",
            "- No passage_service ingest happened.",
            "- No material_card or card_specs writeback happened.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_source_gold_alignment_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Source/Gold Alignment Report",
        "",
        "> Source/gold alignment compares source text evidence with reconstructed gold. It is not source verification.",
        "",
        f"- status: `{summary.get('status')}`",
        f"- alignment_count: `{summary.get('alignment_count')}`",
        f"- status_counts: `{summary.get('status_counts')}`",
        f"- relationship_counts: `{summary.get('relationship_counts')}`",
        f"- verified_original_source_count: `{summary.get('verified_original_source_count')}`",
        f"- ready_for_material_quality_regression: `{summary.get('ready_for_material_quality_regression')}`",
        "",
        "## Alignment Preview",
        "",
    ]
    for row in rows[:5]:
        lines.append(f"- `{row.get('sample_id')}` `{row.get('alignment_status')}` `{row.get('relationship')}` overlap={row.get('overlap_score')}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Original-source candidate remains unverified.",
            "- Similar material is not original source.",
            "- No material_card or material library write happened.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_material_quality_regression_report(quality: dict[str, Any]) -> str:
    lines = [
        "# Material Quality Regression Report",
        "",
        "> Material quality regression is readiness evidence. It is not formal material_card approval.",
        "",
        f"- status: `{quality.get('status')}`",
        f"- source_text_count: `{quality.get('source_text_count')}`",
        f"- available_source_text_count: `{quality.get('available_source_text_count')}`",
        f"- alignment_count: `{quality.get('alignment_count')}`",
        f"- useful_alignment_count: `{quality.get('useful_alignment_count')}`",
        f"- verified_original_source_count: `{quality.get('verified_original_source_count')}`",
        f"- ready_for_material_card_formalization: `{quality.get('ready_for_material_card_formalization')}`",
        f"- recommended_next_action: `{quality.get('recommended_next_action')}`",
        "",
        "## Dimensions",
        "",
        "| dimension | status | method | confidence | blocking |",
        "|---|---|---|---|---|",
    ]
    for item in quality.get("dimensions") or []:
        lines.append(f"| `{item.get('dimension')}` | `{item.get('status')}` | `{item.get('method')}` | `{item.get('confidence')}` | `{item.get('blocking')}` |")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- High score cannot automatically approve formalization.",
            "- Low contamination does not equal verified source.",
            "- No material_card, card_specs, prompt, validator, runtime, or generation write happened.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_matched_spans(text: str, gold_text: str, overlap: float) -> list[dict[str, Any]]:
    if not text or not gold_text or overlap <= 0:
        return []
    return [
        {
            "source_excerpt": truncate_text(text, 160),
            "gold_excerpt": truncate_text(gold_text, 160),
            "method": "lexical_overlap",
            "overlap_score": round(overlap, 4),
        }
    ]


def boilerplate_risk(text: str) -> str:
    if not text:
        return "unknown"
    length = len(text)
    if length < 40:
        return "medium"
    boilerplate_terms = ["责任编辑", "版权", "转载", "免责声明", "点击", "上一页", "下一页"]
    hits = sum(1 for term in boilerplate_terms if term in text)
    if hits >= 2:
        return "high"
    if hits == 1:
        return "medium"
    return "low"


def load_manual_source_texts(path: str | Path | None) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(path) if path else []
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("seed_id"):
            output[str(row["seed_id"])] = row
        if row.get("url"):
            output[str(row["url"])] = row
    return output


def load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


def enforce_unverified(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        row["verified"] = False
        row["verified_original_source"] = False
        row["formalized"] = False
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run source text evidence, source/gold alignment, and material quality regression gates.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-seed-registry", required=True)
    parser.add_argument("--crawl-seed-manifest")
    parser.add_argument("--source-text-evidence-approval", required=True)
    parser.add_argument("--source-text-manual-results")
    parser.add_argument("--gold-reconstruction-results")
    parser.add_argument("--material-card-draft")
    parser.add_argument("--material-quality-regression-draft")
    parser.add_argument("--agent-review-feedback-normalized")
    parser.add_argument("--source-text-mode", choices=("manual", "mock"), default="mock")
    parser.add_argument("--alignment-mode", choices=("dry-run", "mock", "llm"), default="mock")
    parser.add_argument("--alignment-model", default="chat")
    parser.add_argument("--alignment-base-url")
    parser.add_argument("--alignment-api-key-env", default="LEAF_PRE_DISTILL_LLM_API_KEY")
    parser.add_argument("--alignment-timeout-seconds", type=int, default=30)
    parser.add_argument("--alignment-max-output-tokens", type=int, default=900)
    args = parser.parse_args()
    artifacts = run_material_evidence_alignment_regression(
        output_dir=args.output_dir,
        source_seed_registry_path=args.source_seed_registry,
        crawl_seed_manifest_path=args.crawl_seed_manifest,
        source_text_evidence_approval_path=args.source_text_evidence_approval,
        source_text_manual_results_path=args.source_text_manual_results,
        gold_reconstruction_results_path=args.gold_reconstruction_results,
        material_card_draft_path=args.material_card_draft,
        material_quality_regression_draft_path=args.material_quality_regression_draft,
        agent_review_feedback_normalized_path=args.agent_review_feedback_normalized,
        source_text_mode=args.source_text_mode,
        alignment_mode=args.alignment_mode,
        alignment_model=args.alignment_model,
        alignment_base_url=args.alignment_base_url,
        alignment_api_key_env=args.alignment_api_key_env,
        alignment_timeout_seconds=args.alignment_timeout_seconds,
        alignment_max_output_tokens=args.alignment_max_output_tokens,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

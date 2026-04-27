from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any


DEFAULT_MAX_DIGEST_CHARS = 8000
DEFAULT_MAX_EVIDENCE_EXAMPLES = 5
DEFAULT_MAX_FIELD_CANDIDATES = 8


def build_llm_safe_digest(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    candidate_report: dict[str, Any],
    slot_projection: dict[str, Any],
    max_digest_chars: int = DEFAULT_MAX_DIGEST_CHARS,
    max_evidence_examples: int = DEFAULT_MAX_EVIDENCE_EXAMPLES,
    max_field_candidates: int = DEFAULT_MAX_FIELD_CANDIDATES,
) -> dict[str, Any]:
    digest = {
        "digest_version": "v1",
        "mother_family_id": manifest.get("mother_family_id") or candidate_report.get("mother_family_id"),
        "child_family_id": manifest.get("child_family_id"),
        "leaf_label": manifest.get("leaf_label") or candidate_report.get("leaf_label"),
        "sample_count": candidate_report.get("sample_count") or len(samples),
        "field_candidates": _field_candidates(
            candidate_report.get("field_candidates") or [],
            max_evidence_examples=max_evidence_examples,
            max_field_candidates=max_field_candidates,
        ),
        "schema_gaps": _schema_gaps(candidate_report.get("schema_gaps") or []),
        "slot_projection_summary": {
            "canonical_slot_updates": _plain_mapping(slot_projection.get("canonical_slot_updates") or {}),
            "overlay_updates": _plain_mapping(slot_projection.get("overlay_updates") or {}),
            "validator_contract_candidates": [
                _clip_text(item, 120) for item in (slot_projection.get("validator_contract_candidates") or [])[:8]
            ],
        },
        "behavior_action_stats": _behavior_action_stats(traces),
        "safety_notes": [
            "Full source text, full stem, full analysis, and docx content are intentionally excluded.",
            "This digest is evidence-only and cannot update formal card configuration.",
        ],
        "truncation": {
            "max_digest_chars": max_digest_chars,
            "max_evidence_examples": max_evidence_examples,
            "max_field_candidates": max_field_candidates,
            "applied": False,
        },
    }
    return _fit_digest(digest, max_digest_chars=max_digest_chars)


def digest_hash(digest: dict[str, Any]) -> str:
    encoded = json.dumps(digest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def digest_json_size(digest: dict[str, Any]) -> int:
    return len(json.dumps(digest, ensure_ascii=False, sort_keys=True))


def _field_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_evidence_examples: int,
    max_field_candidates: int,
) -> list[dict[str, Any]]:
    ordered = sorted(
        candidates,
        key=lambda item: (
            _confidence_rank(str(item.get("confidence") or "")),
            float(item.get("support_rate") or 0),
            int(item.get("support_count") or 0),
        ),
        reverse=True,
    )
    result: list[dict[str, Any]] = []
    for candidate in ordered[:max_field_candidates]:
        result.append(
            {
                "field_path": str(candidate.get("field_path") or ""),
                "proposed_value": str(candidate.get("proposed_value") or ""),
                "target_layer": str(candidate.get("target_layer") or ""),
                "support_rate": float(candidate.get("support_rate") or 0),
                "confidence": str(candidate.get("confidence") or ""),
                "evidence_examples": [
                    _clip_text(example, 80)
                    for example in (candidate.get("evidence_examples") or [])[:max_evidence_examples]
                ],
                "uniqueness_source": [
                    _clip_text(item, 80) for item in (candidate.get("uniqueness_source") or [])[:5]
                ],
                "distractor_modes": [
                    _clip_text(item, 80) for item in (candidate.get("distractor_modes") or [])[:5]
                ],
            }
        )
    return result


def _schema_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "field": _clip_text(gap.get("field"), 120),
            "reason": _clip_text(gap.get("reason"), 240),
            "suggested_resolution": _clip_text(gap.get("suggested_resolution"), 240),
        }
        for gap in gaps[:8]
    ]


def _plain_mapping(value: dict[str, Any]) -> dict[str, str]:
    return {str(key): _clip_text(item, 120) for key, item in value.items()}


def _behavior_action_stats(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str, str]] = Counter()
    for trace in traces:
        for action in trace.get("observed_actions") or []:
            counter[
                (
                    str(action.get("action") or ""),
                    str(action.get("field_path") or ""),
                    str(action.get("proposed_value") or ""),
                )
            ] += 1
    return [
        {
            "action": action,
            "field_path": field_path,
            "proposed_value": proposed_value,
            "count": count,
        }
        for (action, field_path, proposed_value), count in counter.most_common(12)
    ]


def _fit_digest(digest: dict[str, Any], *, max_digest_chars: int) -> dict[str, Any]:
    if max_digest_chars <= 0 or digest_json_size(digest) <= max_digest_chars:
        return digest

    digest["truncation"]["applied"] = True
    digest["truncation"]["reason"] = "digest exceeded max_digest_chars"

    for candidate in digest.get("field_candidates") or []:
        candidate["evidence_examples"] = candidate.get("evidence_examples", [])[:1]
        candidate["uniqueness_source"] = candidate.get("uniqueness_source", [])[:2]
        candidate["distractor_modes"] = candidate.get("distractor_modes", [])[:2]
    if digest_json_size(digest) <= max_digest_chars:
        return digest

    digest["behavior_action_stats"] = digest.get("behavior_action_stats", [])[:3]
    digest["slot_projection_summary"]["validator_contract_candidates"] = (
        digest["slot_projection_summary"].get("validator_contract_candidates") or []
    )[:3]
    if digest_json_size(digest) <= max_digest_chars:
        return digest

    while digest.get("field_candidates") and digest_json_size(digest) > max_digest_chars:
        digest["field_candidates"].pop()
    if digest_json_size(digest) <= max_digest_chars:
        return digest

    digest["schema_gaps"] = digest.get("schema_gaps", [])[:1]
    digest["behavior_action_stats"] = []
    if digest_json_size(digest) <= max_digest_chars:
        return digest

    digest["field_candidates"] = []
    digest["schema_gaps"] = []
    digest["slot_projection_summary"] = {
        "canonical_slot_updates": {},
        "overlay_updates": {},
        "validator_contract_candidates": [],
    }
    digest["truncation"]["severe"] = True
    return digest


def _confidence_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


def _clip_text(value: Any, max_chars: int) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."

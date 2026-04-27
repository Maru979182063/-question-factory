from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ALLOWED_DECISIONS = {
    "keep_as_original_source_candidate",
    "keep_as_similar_material_seed",
    "keep_as_domain_seed",
    "reject_question_bank",
    "reject_irrelevant",
    "defer",
}
ALLOWED_SOURCE_USES = {
    "original_source_candidate",
    "similar_material",
    "domain_seed",
    "reject",
    "defer",
}
ACCEPT_DECISIONS = {
    "keep_as_original_source_candidate",
    "keep_as_similar_material_seed",
    "keep_as_domain_seed",
}
REJECT_DECISIONS = {"reject_question_bank", "reject_irrelevant"}
RISKY_SOURCE_RISKS = {"question_bank_like", "exam_training_like"}
NEGATIVE_SOURCE_PATTERNS = [
    "question_bank_page",
    "answer_explanation_page",
    "exam_training_page",
]
BLOCKED_DOMAINS_OR_PATTERNS = [
    "offcn",
    "huatu",
    "fenbi",
    "tiku",
    "shiti",
    "daan",
    "gongwuyuan",
    "guokao",
    "shengkao",
    "xingce",
]


def run_source_candidate_review(
    *,
    source_candidate_results_path: str | Path,
    review_decisions_path: str | Path,
    output_dir: str | Path,
    allow_manual_url_additions: bool = False,
    allow_risky_seeds: bool = False,
) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    candidate_path = Path(source_candidate_results_path)
    decisions_path = Path(review_decisions_path)
    candidates = load_jsonl(candidate_path)
    decision_payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    review, seeds = build_source_candidate_review(
        candidates=candidates,
        decision_payload=decision_payload,
        source_candidate_results_path=candidate_path,
        allow_manual_url_additions=allow_manual_url_additions,
        allow_risky_seeds=allow_risky_seeds,
    )
    registry_path = output_path / "source_seed_registry.jsonl"
    crawl_manifest = build_crawl_seed_manifest(seeds=seeds, registry_path=registry_path)
    report = render_source_candidate_human_review_report(
        review=review,
        seeds=seeds,
        crawl_manifest=crawl_manifest,
    )

    review_path = output_path / "source_candidate_review.json"
    crawl_path = output_path / "crawl_seed_manifest.json"
    report_path = output_path / "source_candidate_human_review_report.md"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(registry_path, seeds)
    crawl_path.write_text(json.dumps(crawl_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    return {
        "source_candidate_review": str(review_path),
        "source_seed_registry": str(registry_path),
        "crawl_seed_manifest": str(crawl_path),
        "source_candidate_human_review_report": str(report_path),
    }


def build_source_candidate_review(
    *,
    candidates: list[dict[str, Any]],
    decision_payload: dict[str, Any],
    source_candidate_results_path: str | Path,
    allow_manual_url_additions: bool = False,
    allow_risky_seeds: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate_index = {
        candidate_key(candidate.get("sample_id"), candidate.get("url")): candidate
        for candidate in candidates
    }
    reviewed: list[dict[str, Any]] = []
    seeds: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, decision in enumerate(decision_payload.get("decisions") or []):
        reviewed_item, seed = process_decision(
            decision=decision,
            decision_index=index,
            candidate_index=candidate_index,
            allow_manual_url_additions=allow_manual_url_additions,
            allow_risky_seeds=allow_risky_seeds,
        )
        reviewed.append(reviewed_item)
        warnings.extend(reviewed_item.get("warnings") or [])
        if seed is not None:
            seeds.append(seed)

    decision_counts = Counter(item.get("decision") or "missing" for item in reviewed)
    rejected_count = sum(1 for item in reviewed if item.get("decision") in REJECT_DECISIONS)
    deferred_count = sum(1 for item in reviewed if item.get("decision") == "defer")
    accepted_count = len(seeds)
    review = {
        "review_version": "v1",
        "status": "reviewed",
        "reviewer": decision_payload.get("reviewer") or "human",
        "reviewed_at": decision_payload.get("reviewed_at") or datetime.now(timezone.utc).isoformat(),
        "source_candidate_results_path": str(source_candidate_results_path),
        "decision_counts": dict(decision_counts),
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "deferred_count": deferred_count,
        "seed_count": len(seeds),
        "risky_accepted_seed_count": sum(1 for seed in seeds if "risky_seed_accepted_by_human" in (seed.get("warnings") or [])),
        "verified_original_source_count": 0,
        "ready_for_material_card_draft": False,
        "reviewed_candidates": reviewed,
        "warnings": dedupe(warnings),
        "limits": [
            "Human review does not confirm original source unless a later source verification step is performed.",
            "Reviewed source candidates do not write material_card or material library.",
            "Similar material is not original material.",
            "Source seed is seed-only.",
        ],
    }
    return review, seeds


def process_decision(
    *,
    decision: dict[str, Any],
    decision_index: int,
    candidate_index: dict[tuple[str, str], dict[str, Any]],
    allow_manual_url_additions: bool,
    allow_risky_seeds: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    warnings: list[str] = []
    decision_name = str(decision.get("decision") or "")
    source_use = str(decision.get("source_use") or inferred_source_use(decision_name))
    if decision_name not in ALLOWED_DECISIONS:
        warnings.append("unknown_review_decision")
    if source_use not in ALLOWED_SOURCE_USES:
        warnings.append("unknown_source_use")
        source_use = "defer"

    sample_id = str(decision.get("sample_id") or "")
    url = str(decision.get("url") or "")
    candidate = candidate_index.get(candidate_key(sample_id, url))
    candidate_known = candidate is not None
    if not candidate_known:
        if allow_manual_url_additions and manual_addition_is_complete(decision):
            candidate = manual_candidate_from_decision(decision)
            warnings.append("manual_url_addition_unverified")
        else:
            candidate = manual_candidate_from_decision(decision)
            warnings.append("unknown_candidate_rejected")
            reviewed = reviewed_candidate_payload(
                decision=decision,
                candidate=candidate,
                decision_name=decision_name or "defer",
                source_use=source_use,
                candidate_known=False,
                warnings=warnings,
            )
            return reviewed, None

    source_risk = str(candidate.get("source_risk") or "unknown")
    accepted_decision = decision_name in ACCEPT_DECISIONS
    seed: dict[str, Any] | None = None
    if accepted_decision:
        if source_risk in RISKY_SOURCE_RISKS and not (allow_risky_seeds and bool(decision.get("allow_risky_seed"))):
            warnings.append("risky_candidate_seed_rejected_without_explicit_allowance")
        else:
            seed = seed_from_decision(
                decision=decision,
                candidate=candidate,
                source_use=source_use,
                warnings=["risky_seed_accepted_by_human"] if source_risk in RISKY_SOURCE_RISKS else [],
            )
    reviewed = reviewed_candidate_payload(
        decision=decision,
        candidate=candidate,
        decision_name=decision_name,
        source_use=source_use,
        candidate_known=candidate_known,
        warnings=warnings,
    )
    return reviewed, seed


def reviewed_candidate_payload(
    *,
    decision: dict[str, Any],
    candidate: dict[str, Any],
    decision_name: str,
    source_use: str,
    candidate_known: bool,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "sample_id": str(decision.get("sample_id") or candidate.get("sample_id") or ""),
        "url": str(decision.get("url") or candidate.get("url") or ""),
        "title": candidate.get("title") or decision.get("title") or "",
        "domain": candidate.get("domain") or domain_from_url(str(decision.get("url") or "")),
        "snippet": candidate.get("snippet") or decision.get("snippet") or "",
        "source_risk": candidate.get("source_risk") or "unknown",
        "candidate_status": candidate.get("candidate_status") or "weak_candidate",
        "candidate_score": candidate.get("candidate_score") or 0.0,
        "decision": decision_name,
        "source_use": source_use,
        "verification_status": "human_reviewed_unverified",
        "verified": False,
        "verified_original_source": False,
        "formalized": False,
        "candidate_known": bool(candidate_known),
        "rationale": decision.get("rationale") or "",
        "review_notes": decision.get("review_notes") or "",
        "human_opened_url": bool(decision.get("human_opened_url")),
        "warnings": dedupe(warnings),
    }


def seed_from_decision(
    *,
    decision: dict[str, Any],
    candidate: dict[str, Any],
    source_use: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    seed_type = "domain_seed" if source_use == "domain_seed" else "url_seed"
    priority = decision.get("crawl_priority") or ("medium" if seed_type == "domain_seed" else "low")
    return {
        "seed_id": seed_id_for(candidate.get("sample_id"), candidate.get("url"), source_use),
        "seed_version": "v1",
        "sample_id": candidate.get("sample_id") or decision.get("sample_id") or "",
        "source_use": source_use,
        "seed_type": seed_type,
        "url": candidate.get("url") or decision.get("url") or "",
        "domain": candidate.get("domain") or domain_from_url(str(candidate.get("url") or decision.get("url") or "")),
        "title": candidate.get("title") or decision.get("title") or "",
        "snippet": candidate.get("snippet") or decision.get("snippet") or "",
        "source_risk": candidate.get("source_risk") or "unknown",
        "candidate_status": candidate.get("candidate_status") or "weak_candidate",
        "crawl_priority": priority,
        "usable_for_family": decision.get("usable_for_family") or "word_usage",
        "usable_for_leaf": decision.get("usable_for_leaf") or "word_usage_content_word",
        "linked_query": candidate.get("query") or "",
        "linked_candidate_score": candidate.get("candidate_score") or 0.0,
        "verification_status": "human_reviewed_unverified",
        "verified_original_source": False,
        "verified": False,
        "formalized": False,
        "status": "seed_only",
        "negative_patterns": list(NEGATIVE_SOURCE_PATTERNS),
        "review_rationale": decision.get("rationale") or "",
        "warnings": dedupe(warnings or []),
    }


def build_crawl_seed_manifest(*, seeds: list[dict[str, Any]], registry_path: Path) -> dict[str, Any]:
    domain_counts = Counter(seed.get("domain") or "unknown" for seed in seeds)
    priority_counts = Counter(seed.get("crawl_priority") or "low" for seed in seeds)
    return {
        "crawl_seed_version": "v1",
        "source_seed_registry_path": str(registry_path),
        "seed_count": len(seeds),
        "domain_counts": dict(domain_counts),
        "priority_counts": dict(priority_counts),
        "allowed_seed_uses": [
            "original_source_candidate",
            "similar_material",
            "domain_seed",
        ],
        "crawl_allowed": False,
        "requires_explicit_crawl_approval": True,
        "recommended_limits": {
            "max_urls_per_domain": 5,
            "max_total_urls": 20,
            "fetch_body": False,
        },
        "blocked_domains_or_patterns": list(BLOCKED_DOMAINS_OR_PATTERNS),
        "ready_for_crawl_review": bool(seeds),
        "ready_for_material_card_draft": False,
        "limits": [
            "This manifest does not execute crawling.",
            "This manifest does not write a material library.",
            "This manifest does not confirm original sources.",
        ],
    }


def render_source_candidate_human_review_report(
    *,
    review: dict[str, Any],
    seeds: list[dict[str, Any]],
    crawl_manifest: dict[str, Any],
) -> str:
    reviewed = review.get("reviewed_candidates") or []
    accepted_similar = [seed for seed in seeds if seed.get("source_use") == "similar_material"]
    accepted_original = [seed for seed in seeds if seed.get("source_use") == "original_source_candidate"]
    accepted_domain = [seed for seed in seeds if seed.get("source_use") == "domain_seed"]
    rejected_question_bank = [item for item in reviewed if item.get("decision") == "reject_question_bank"]
    rejected_irrelevant = [item for item in reviewed if item.get("decision") == "reject_irrelevant"]
    deferred = [item for item in reviewed if item.get("decision") == "defer"]
    risky = [seed for seed in seeds if "risky_seed_accepted_by_human" in (seed.get("warnings") or [])]
    lines = [
        "# Source Candidate Human Review Report",
        "",
        "> Reviewed source candidates are seed-only evidence. They are not verified sources, material library entries, or material_card drafts.",
        "",
        "## Input Candidate Summary",
        "",
        f"- source_candidate_results_path: `{review.get('source_candidate_results_path')}`",
        f"- reviewed_candidate_count: `{len(reviewed)}`",
        f"- accepted_count: `{review.get('accepted_count')}`",
        f"- rejected_count: `{review.get('rejected_count')}`",
        f"- deferred_count: `{review.get('deferred_count')}`",
        f"- seed_count: `{len(seeds)}`",
        f"- verified_original_source_count: `{review.get('verified_original_source_count')}`",
        f"- crawl_allowed: `{crawl_manifest.get('crawl_allowed')}`",
        f"- ready_for_crawl_review: `{crawl_manifest.get('ready_for_crawl_review')}`",
        f"- ready_for_material_card_draft: `{crawl_manifest.get('ready_for_material_card_draft')}`",
        "",
        "## Decision Counts",
        "",
    ]
    lines.extend(counter_lines(review.get("decision_counts") or {}))
    append_seed_section(lines, "Accepted Similar Material Seeds", accepted_similar)
    append_seed_section(lines, "Accepted Original-Source Candidates", accepted_original)
    append_seed_section(lines, "Accepted Domain Seeds", accepted_domain)
    append_review_section(lines, "Rejected Question-Bank / Exam-Training Pages", rejected_question_bank)
    append_review_section(lines, "Rejected Irrelevant Items", rejected_irrelevant)
    append_review_section(lines, "Deferred Items", deferred)
    append_seed_section(lines, "Risky Accepted Seeds", risky)
    lines.extend(
        [
            "## Crawl Seed Preview",
            "",
            f"- seed_count: `{crawl_manifest.get('seed_count')}`",
            f"- domain_counts: `{crawl_manifest.get('domain_counts') or {}}`",
            f"- priority_counts: `{crawl_manifest.get('priority_counts') or {}}`",
            f"- crawl_allowed: `{crawl_manifest.get('crawl_allowed')}`",
            f"- fetch_body: `{(crawl_manifest.get('recommended_limits') or {}).get('fetch_body')}`",
            "",
            "## Human Review Checklist",
            "",
            "- Similar material is not original source.",
            "- Original-source candidate is not verified original source.",
            "- Risky accepted seeds require explicit later review before any crawling.",
            "- Crawl manifest is not crawl approval.",
            "- Do not write material_card or material library from this report.",
            "",
            "## Boundaries",
            "",
            "- No original source was confirmed.",
            "- No webpage body was fetched.",
            "- No crawler was executed.",
            "- No material library write happened.",
            "- No material_card was generated.",
            "- No card_specs, prompt, validator, generation, runtime, API, UI, or promotion target was changed.",
        ]
    )
    return "\n".join(lines) + "\n"


def append_seed_section(lines: list[str], title: str, seeds: list[dict[str, Any]]) -> None:
    lines.extend([f"## {title}", ""])
    if not seeds:
        lines.extend(["- None", ""])
        return
    for seed in seeds:
        lines.append(
            "- `{source_use}` `{priority}` `{domain}`: [{title}]({url})".format(
                source_use=seed.get("source_use"),
                priority=seed.get("crawl_priority"),
                domain=seed.get("domain"),
                title=seed.get("title") or seed.get("url"),
                url=seed.get("url"),
            )
        )
    lines.append("")


def append_review_section(lines: list[str], title: str, items: list[dict[str, Any]]) -> None:
    lines.extend([f"## {title}", ""])
    if not items:
        lines.extend(["- None", ""])
        return
    for item in items:
        lines.append(f"- `{item.get('sample_id')}` `{item.get('domain')}`: {item.get('title') or item.get('url')}")
    lines.append("")


def inferred_source_use(decision_name: str) -> str:
    if decision_name == "keep_as_original_source_candidate":
        return "original_source_candidate"
    if decision_name == "keep_as_similar_material_seed":
        return "similar_material"
    if decision_name == "keep_as_domain_seed":
        return "domain_seed"
    if decision_name in REJECT_DECISIONS:
        return "reject"
    return "defer"


def manual_addition_is_complete(decision: dict[str, Any]) -> bool:
    return bool(decision.get("sample_id") and decision.get("url") and decision.get("title") and decision.get("source_use") and decision.get("rationale"))


def manual_candidate_from_decision(decision: dict[str, Any]) -> dict[str, Any]:
    url = str(decision.get("url") or "")
    return {
        "sample_id": decision.get("sample_id") or "",
        "url": url,
        "title": decision.get("title") or "",
        "domain": decision.get("domain") or domain_from_url(url),
        "snippet": decision.get("snippet") or "",
        "source_risk": decision.get("source_risk") or "unknown",
        "candidate_status": decision.get("candidate_status") or "weak_candidate",
        "candidate_score": decision.get("candidate_score") or 0.0,
        "query": decision.get("query") or "",
    }


def candidate_key(sample_id: Any, url: Any) -> tuple[str, str]:
    return (str(sample_id or ""), str(url or ""))


def seed_id_for(sample_id: Any, url: Any, source_use: str) -> str:
    digest = hashlib.sha256(f"{sample_id}|{url}|{source_use}".encode("utf-8")).hexdigest()[:16]
    return f"source_seed_{digest}"


def domain_from_url(url: str) -> str:
    return urlparse(str(url or "")).netloc.lower()


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


def counter_lines(counter: dict[str, Any]) -> list[str]:
    if not counter:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in sorted(counter.items())]


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize human review decisions over source candidates into seed-only source registry artifacts.")
    parser.add_argument("--source-candidate-results", required=True)
    parser.add_argument("--review-decisions", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--allow-manual-url-additions", action="store_true")
    parser.add_argument("--allow-risky-seeds", action="store_true")
    args = parser.parse_args()
    artifacts = run_source_candidate_review(
        source_candidate_results_path=args.source_candidate_results,
        review_decisions_path=args.review_decisions,
        output_dir=args.output_dir,
        allow_manual_url_additions=args.allow_manual_url_additions,
        allow_risky_seeds=args.allow_risky_seeds,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

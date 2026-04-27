from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.gold_reconstruction import QUESTION_WRAPPER_TERMS
from tools.leaf_pre_distill.material_seed_pack import build_initial_material_seed_pack


ANTI_QUESTION_BANK_TERMS = [
    "下列",
    "加点词",
    "答案解析",
    "本题考查",
    "正确的是",
    "不正确的是",
    "答案",
    "解析",
    "本题",
    "选项",
    "A项",
    "B项",
    "C项",
    "D项",
    "题号",
    "所属试卷",
    "题干",
    "网友回忆",
    "正确率",
    "易错项",
    "考点",
    "文段出处",
]
QUESTION_WRAPPER_LEAKAGE_WARNING = "restored_text_contains_question_wrapper_terms"
DEFAULT_MAX_QUERIES_PER_SAMPLE = 6
DEFAULT_MIN_QUERY_CHARS = 8


def run_source_discovery_preparation_from_artifact_dir(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path | None = None,
    gold_reconstruction_results_path: str | Path | None = None,
    max_queries_per_sample: int = DEFAULT_MAX_QUERIES_PER_SAMPLE,
    min_query_chars: int = DEFAULT_MIN_QUERY_CHARS,
    use_raw_fallback: bool = False,
) -> dict[str, str]:
    artifact_path = Path(artifact_dir)
    output_path = Path(output_dir) if output_dir is not None else artifact_path
    manifest = json.loads((artifact_path / "manifest.json").read_text(encoding="utf-8"))
    samples = load_jsonl(artifact_path / "samples.jsonl")
    reconstruction_path = Path(gold_reconstruction_results_path) if gold_reconstruction_results_path is not None else artifact_path / "gold_reconstruction_results.jsonl"
    gold_reconstructions = load_jsonl(reconstruction_path) if reconstruction_path.exists() else []
    return run_source_discovery_preparation(
        manifest=manifest,
        samples=samples,
        source_artifact_dir=artifact_path,
        output_dir=output_path,
        gold_reconstructions=gold_reconstructions,
        max_queries_per_sample=max_queries_per_sample,
        min_query_chars=min_query_chars,
        use_raw_fallback=use_raw_fallback,
    )


def run_source_discovery_preparation(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    source_artifact_dir: str | Path,
    output_dir: str | Path,
    gold_reconstructions: list[dict[str, Any]] | None = None,
    max_queries_per_sample: int = DEFAULT_MAX_QUERIES_PER_SAMPLE,
    min_query_chars: int = DEFAULT_MIN_QUERY_CHARS,
    use_raw_fallback: bool = False,
) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    reconstructions = gold_reconstructions or []

    if not reconstructions and not use_raw_fallback:
        queries: list[dict[str, Any]] = []
        seeds: list[dict[str, Any]] = []
        profile = build_blocked_profile(
            manifest=manifest,
            source_artifact_dir=source_artifact_dir,
            sample_count=len(samples),
        )
    else:
        queries = build_source_discovery_queries(
            manifest=manifest,
            samples=samples,
            gold_reconstructions=reconstructions,
            use_raw_fallback=use_raw_fallback,
            max_queries_per_sample=max_queries_per_sample,
            min_query_chars=min_query_chars,
        )
        seeds = build_initial_material_seed_pack(manifest=manifest, query_rows=queries)
        profile = build_material_source_profile(
            manifest=manifest,
            source_artifact_dir=source_artifact_dir,
            query_rows=queries,
            seed_count=len(seeds),
        )

    report = render_source_discovery_preparation_report(
        profile=profile,
        query_rows=queries,
        seed_rows=seeds,
    )
    query_path = output_path / "source_discovery_queries.jsonl"
    profile_path = output_path / "material_source_profile.json"
    seed_path = output_path / "initial_material_seed_pack.jsonl"
    report_path = output_path / "source_discovery_preparation_report.md"
    write_jsonl(query_path, queries)
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(seed_path, seeds)
    report_path.write_text(report, encoding="utf-8")
    return {
        "source_discovery_queries": str(query_path),
        "material_source_profile": str(profile_path),
        "initial_material_seed_pack": str(seed_path),
        "source_discovery_preparation_report": str(report_path),
    }


def build_source_discovery_queries(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    gold_reconstructions: list[dict[str, Any]],
    use_raw_fallback: bool,
    max_queries_per_sample: int = DEFAULT_MAX_QUERIES_PER_SAMPLE,
    min_query_chars: int = DEFAULT_MIN_QUERY_CHARS,
) -> list[dict[str, Any]]:
    recon_by_id = {
        str(row.get("sample_id")): row
        for row in gold_reconstructions
        if row.get("sample_id") is not None
    }
    rows: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        sample_id = sample_id_for(sample, index)
        reconstruction = recon_by_id.get(sample_id)
        row = build_query_row(
            manifest=manifest,
            sample=sample,
            sample_id=sample_id,
            reconstruction=reconstruction,
            use_raw_fallback=use_raw_fallback,
            max_queries_per_sample=max_queries_per_sample,
            min_query_chars=min_query_chars,
        )
        rows.append(row)
    return rows


def build_query_row(
    *,
    manifest: dict[str, Any],
    sample: dict[str, Any],
    sample_id: str,
    reconstruction: dict[str, Any] | None,
    use_raw_fallback: bool,
    max_queries_per_sample: int,
    min_query_chars: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    invalid_reconstruction = False
    if reconstruction:
        gold_source = "gold_reconstruction_results"
        invalid_reconstruction = bool((reconstruction.get("source") or {}).get("raw_model_error")) or (
            (reconstruction.get("mechanical_checks") or {}).get("json_parse_ok") is False
        )
        leakage_risk = str((reconstruction.get("gold_quality_flags") or {}).get("question_wrapper_leakage_risk") or "low")
        if invalid_reconstruction:
            restored = ""
            requires_article = True
            warnings.append("gold reconstruction failed; source discovery requires human review")
        else:
            restored, requires_article = restored_material_from_reconstruction(reconstruction)
            if not restored:
                restored = auxiliary_material_from_reconstruction(reconstruction)
                warnings.append("restored material was weak; query used auxiliary gold question or mechanism text")
    else:
        gold_source = "raw_samples"
        leakage_risk = "high"
        restored = raw_fallback_material(sample) if use_raw_fallback else ""
        requires_article = True
        warnings.append("using raw sample material fallback; high contamination risk")

    original_restored = restored
    restored = normalize_spaces(restored)
    queries = build_queries_from_material(
        restored,
        max_queries=max_queries_per_sample,
        min_query_chars=min_query_chars,
    )
    risk = contamination_risk(
        restored=original_restored,
        queries=queries,
        gold_source=gold_source,
    )
    if invalid_reconstruction:
        risk = "high"
    if leakage_risk == "high":
        risk = "high"
        lower_query_confidence(queries)
        if QUESTION_WRAPPER_LEAKAGE_WARNING not in warnings:
            warnings.append(QUESTION_WRAPPER_LEAKAGE_WARNING)
    if not restored:
        warnings.append("no usable restored human material found")
    if not queries:
        warnings.append("no safe search query could be produced")
    if risk == "high" and "high question-bank contamination risk" not in warnings:
        warnings.append("high question-bank contamination risk")

    return {
        "sample_id": sample_id,
        "query_version": "v1",
        "gold_source": gold_source,
        "using_raw_sample_material": gold_source == "raw_samples",
        "restored_human_material": truncate_text(clean_question_bank_terms(restored), 1200),
        "search_queries": queries,
        "anti_question_bank_terms": list(ANTI_QUESTION_BANK_TERMS),
        "question_bank_contamination_risk": risk,
        "likely_source_type": infer_likely_source_type(restored, manifest=manifest),
        "requires_source_article": bool(requires_article or not restored or risk == "high"),
        "needs_human_review": bool(risk == "high" or not queries or not restored),
        "warnings": dedupe(warnings),
    }


def restored_material_from_reconstruction(reconstruction: dict[str, Any]) -> tuple[str, bool]:
    material = reconstruction.get("gold_material") or {}
    flags = reconstruction.get("gold_quality_flags") or {}
    restored_text = str(material.get("restored_text") or "").strip()
    if restored_text:
        return restored_text, bool(flags.get("requires_source_article"))
    parts = [
        material.get("context_window") or "",
        " ".join(str(item) for item in material.get("evidence_units") or []),
    ]
    return "\n".join(part for part in parts if part).strip(), bool(flags.get("requires_source_article"))


def auxiliary_material_from_reconstruction(reconstruction: dict[str, Any]) -> str:
    question = reconstruction.get("gold_question") or {}
    answer = reconstruction.get("answer_mechanism") or {}
    parts = [
        question.get("stem") or "",
        answer.get("core_reasoning") or "",
    ]
    return "\n".join(part for part in parts if part).strip()


def raw_fallback_material(sample: dict[str, Any]) -> str:
    parts = [
        sample.get("raw_text") or "",
        sample.get("stem") or "",
        sample.get("analysis") or "",
        sample.get("exam_points") or "",
    ]
    return "\n".join(str(part) for part in parts if part).strip()


def build_queries_from_material(
    material: str,
    *,
    max_queries: int,
    min_query_chars: int,
) -> list[dict[str, Any]]:
    cleaned = clean_question_bank_terms(material)
    candidates: list[dict[str, Any]] = []
    for sentence in sentence_candidates(cleaned):
        if len(sentence) >= min_query_chars:
            candidates.append(
                {
                    "query": sentence,
                    "query_type": "exact_sentence",
                    "purpose": "find_original_source",
                    "confidence": "high" if len(sentence) >= 20 else "medium",
                }
            )
    keywords = keyword_combo(cleaned)
    if keywords:
        candidates.append(
            {
                "query": keywords,
                "query_type": "keyword_combo",
                "purpose": "find_similar_material",
                "confidence": "medium",
            }
        )
    title_like = title_like_query(cleaned)
    if title_like:
        candidates.append(
            {
                "query": title_like,
                "query_type": "title_like",
                "purpose": "find_original_source",
                "confidence": "low",
            }
        )
    return dedupe_queries(candidates, max_queries=max_queries, min_query_chars=min_query_chars)


def sentence_candidates(text: str) -> list[str]:
    chunks = re.split(r"[。！？!?；;\n]+", text)
    candidates: list[str] = []
    for chunk in chunks:
        item = normalize_spaces(chunk)
        if not item or has_question_bank_terms(item):
            continue
        if item.lower().startswith(("stem:", "answer:", "analysis:", "options:", "exam_points:", "raw_text:")):
            continue
        candidates.append(truncate_text(item, 90))
    return candidates


def keyword_combo(text: str) -> str:
    cleaned = normalize_spaces(remove_ascii_labels(clean_question_bank_terms(text)))
    tokens = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9_-]{3,}", cleaned)
    blocked = set(ANTI_QUESTION_BANK_TERMS) | {"raw", "text", "stem", "analysis", "options", "answer", "exam", "points"}
    picked: list[str] = []
    for token in tokens:
        if token in blocked or has_question_bank_terms(token):
            continue
        if token not in picked:
            picked.append(token)
        if len(picked) >= 5:
            break
    return " ".join(picked)


def title_like_query(text: str) -> str:
    sentences = sentence_candidates(text)
    if not sentences:
        return ""
    first = sentences[0]
    if len(first) <= 28:
        return first
    return ""


def clean_question_bank_terms(text: str) -> str:
    cleaned = remove_ascii_labels(text)
    for term in set(ANTI_QUESTION_BANK_TERMS) | set(QUESTION_WRAPPER_TERMS):
        cleaned = cleaned.replace(term, " ")
    cleaned = re.sub(r"[A-D][\.、．]\s*[^。！？!?；;\n]{0,40}", " ", cleaned)
    return normalize_spaces(cleaned)


def remove_ascii_labels(text: str) -> str:
    return re.sub(r"\b(raw_text|stem|options|answer|analysis|exam_points)\s*:", " ", text, flags=re.IGNORECASE)


def contamination_risk(*, restored: str, queries: list[dict[str, Any]], gold_source: str) -> str:
    if gold_source == "raw_samples":
        return "high"
    if has_question_bank_terms(restored):
        return "high"
    if any(has_question_bank_terms(str(item.get("query") or "")) for item in queries):
        return "high"
    if not restored or not queries:
        return "medium"
    if len(restored) < 40:
        return "medium"
    return "low"


def infer_likely_source_type(text: str, *, manifest: dict[str, Any]) -> str:
    material = text.lower()
    if any(term in material for term in ("研究", "实验", "科学", "技术", "生物", "宇宙")):
        return "science"
    if any(term in material for term in ("评论", "观点", "社会", "治理", "文化")):
        return "commentary"
    if any(term in material for term in ("报道", "记者", "消息", "近日")):
        return "news"
    if any(term in material for term in ("小说", "散文", "诗", "文学")):
        return "literature"
    if manifest.get("mother_family_id") == "word_usage":
        return "education_text"
    return "unknown"


def build_material_source_profile(
    *,
    manifest: dict[str, Any],
    source_artifact_dir: str | Path,
    query_rows: list[dict[str, Any]],
    seed_count: int,
) -> dict[str, Any]:
    source_types = Counter(row.get("likely_source_type") or "unknown" for row in query_rows)
    risk = Counter(row.get("question_bank_contamination_risk") or "unknown" for row in query_rows)
    quality = Counter()
    for row in query_rows:
        row_queries = row.get("search_queries") or []
        if not row_queries:
            quality["low"] += 1
        else:
            for query in row_queries:
                quality[query.get("confidence") or "low"] += 1
    needs_review = sum(1 for row in query_rows if row.get("needs_human_review"))
    requires_source = sum(1 for row in query_rows if row.get("requires_source_article"))
    blockers = []
    if not query_rows:
        blockers.append("no source discovery queries generated")
    if risk.get("high", 0):
        blockers.append("high question-bank contamination risk exists")
    if needs_review:
        blockers.append("some samples require human review")
    return {
        "profile_version": "v1",
        "status": "ready" if query_rows else "blocked",
        "source_artifact_dir": str(source_artifact_dir),
        "sample_count": len(query_rows),
        "gold_source": "gold_reconstruction_results" if any(row.get("gold_source") == "gold_reconstruction_results" for row in query_rows) else "raw_samples",
        "using_raw_sample_material": any(row.get("using_raw_sample_material") for row in query_rows),
        "source_type_distribution": dict(source_types),
        "question_bank_contamination_summary": dict(risk),
        "requires_source_article_count": requires_source,
        "needs_human_review_count": needs_review,
        "query_quality_summary": dict(quality),
        "seed_count": seed_count,
        "material_line_conclusion": {
            "ready_for_source_discovery": bool(query_rows and risk.get("high", 0) == 0),
            "ready_for_material_card_draft": False,
            "main_blockers": blockers,
        },
        "boundaries": [
            "This is material-line preparation, not card protocol landing.",
            "No web search was executed.",
            "No material library or card_specs files were written.",
        ],
    }


def build_blocked_profile(*, manifest: dict[str, Any], source_artifact_dir: str | Path, sample_count: int) -> dict[str, Any]:
    return {
        "profile_version": "v1",
        "status": "blocked",
        "source_artifact_dir": str(source_artifact_dir),
        "sample_count": sample_count,
        "gold_source": "missing",
        "using_raw_sample_material": False,
        "source_type_distribution": {},
        "question_bank_contamination_summary": {},
        "requires_source_article_count": 0,
        "needs_human_review_count": sample_count,
        "query_quality_summary": {"high": 0, "medium": 0, "low": 0},
        "seed_count": 0,
        "material_line_conclusion": {
            "ready_for_source_discovery": False,
            "ready_for_material_card_draft": False,
            "main_blockers": [
                "gold_reconstruction_results.jsonl is required before source discovery preparation",
                "raw sample fallback was not enabled",
            ],
        },
        "boundaries": [
            "This is material-line preparation, not card protocol landing.",
            "No web search was executed.",
            "No material library or card_specs files were written.",
        ],
    }


def render_source_discovery_preparation_report(
    *,
    profile: dict[str, Any],
    query_rows: list[dict[str, Any]],
    seed_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Source Discovery Preparation Report",
        "",
        "> This is material-line preparation only. It is not card protocol landing, not a formal material_card, and not web search execution.",
        "> initial_material_seed_pack is seed-only input for later source discovery or passage services, not a production material library.",
        "",
        "## Summary",
        "",
        f"- status: `{profile.get('status')}`",
        f"- sample_count: `{profile.get('sample_count')}`",
        f"- gold_source: `{profile.get('gold_source')}`",
        f"- using_raw_sample_material: `{profile.get('using_raw_sample_material')}`",
        f"- requires_source_article_count: `{profile.get('requires_source_article_count')}`",
        f"- needs_human_review_count: `{profile.get('needs_human_review_count')}`",
        f"- ready_for_source_discovery: `{(profile.get('material_line_conclusion') or {}).get('ready_for_source_discovery')}`",
        f"- ready_for_material_card_draft: `{(profile.get('material_line_conclusion') or {}).get('ready_for_material_card_draft')}`",
        "",
        "## Query Quality Distribution",
        "",
    ]
    lines.extend(counter_lines(profile.get("query_quality_summary") or {}))
    lines.extend(["", "## Question Bank Contamination Risk", ""])
    lines.extend(counter_lines(profile.get("question_bank_contamination_summary") or {}))
    lines.extend(["", "## Source Type Distribution", ""])
    lines.extend(counter_lines(profile.get("source_type_distribution") or {}))

    blockers = (profile.get("material_line_conclusion") or {}).get("main_blockers") or []
    if blockers:
        lines.extend(["", "## Main Blockers", ""])
        for blocker in blockers:
            lines.append(f"- {blocker}")

    review_rows = [row for row in query_rows if row.get("needs_human_review")]
    lines.extend(["", "## Needs Human Review Samples", ""])
    if review_rows:
        for row in review_rows[:20]:
            lines.append(f"- `{row.get('sample_id')}`: {', '.join(row.get('warnings') or [])}")
    else:
        lines.append("- None")

    lines.extend(["", "## Restored Human Material Examples", ""])
    for row in query_rows[:3]:
        lines.append(f"### `{row.get('sample_id')}`")
        lines.append("")
        lines.append(row.get("restored_human_material") or "(empty)")
        lines.append("")

    lines.extend(["", "## Search Query Examples", ""])
    if query_rows:
        for row in query_rows[:3]:
            lines.append(f"### `{row.get('sample_id')}`")
            for query in row.get("search_queries") or []:
                lines.append(f"- [{query.get('query_type')}] {query.get('query')} ({query.get('confidence')})")
            lines.append("")
    else:
        lines.append("- None")

    lines.extend(["", "## Initial Material Seed Examples", ""])
    if seed_rows:
        for seed in seed_rows[:3]:
            lines.append(f"- `{seed.get('seed_id')}`: {seed.get('material_seed_type')} / formalized=`{seed.get('formalized')}`")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- No real web search was executed.",
            "- No material_card, card_specs, generation, validator, prompt, runtime, or promotion target was changed.",
            "- Queries are prepared for later human-reviewed source discovery and may still need manual URLs or original text.",
        ]
    )
    return "\n".join(lines) + "\n"


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = Path(path)
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sample_id_for(sample: dict[str, Any], index: int) -> str:
    return str(sample.get("sample_id") or sample.get("id") or sample.get("qid") or f"sample-{index}")


def has_question_bank_terms(text: str) -> bool:
    return any(term in text for term in set(ANTI_QUESTION_BANK_TERMS) | set(QUESTION_WRAPPER_TERMS))


def lower_query_confidence(queries: list[dict[str, Any]]) -> None:
    for query in queries:
        query["confidence"] = "low"


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def truncate_text(text: str, max_chars: int) -> str:
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


def dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value and value not in output:
            output.append(value)
    return output


def dedupe_queries(
    queries: list[dict[str, Any]],
    *,
    max_queries: int,
    min_query_chars: int,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        text = normalize_spaces(str(query.get("query") or ""))
        text = clean_question_bank_terms(text)
        if len(text) < min_query_chars or has_question_bank_terms(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        next_query = dict(query)
        next_query["query"] = text
        output.append(next_query)
        if len(output) >= max_queries:
            break
    return output


def counter_lines(counter: dict[str, Any]) -> list[str]:
    if not counter:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in sorted(counter.items())]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare source discovery material artifacts from reconstructed gold.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--gold-reconstruction-results")
    parser.add_argument("--max-queries-per-sample", type=int, default=DEFAULT_MAX_QUERIES_PER_SAMPLE)
    parser.add_argument("--min-query-chars", type=int, default=DEFAULT_MIN_QUERY_CHARS)
    parser.add_argument("--use-raw-fallback", action="store_true")
    args = parser.parse_args()
    artifacts = run_source_discovery_preparation_from_artifact_dir(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        gold_reconstruction_results_path=args.gold_reconstruction_results,
        max_queries_per_sample=args.max_queries_per_sample,
        min_query_chars=args.min_query_chars,
        use_raw_fallback=args.use_raw_fallback,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.gold_reconstruction import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    run_gold_reconstruction,
)
from tools.leaf_pre_distill.llm_field_probe import ChatClient
from tools.leaf_pre_distill.source_discovery_preparation import (
    ANTI_QUESTION_BANK_TERMS,
    load_jsonl,
    run_source_discovery_preparation,
)


DEFAULT_SAMPLE_SIZE = 8
DEFAULT_SEED = 7


def run_gold_reconstruction_llm_smoke(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    run_llm: bool = False,
    model: str = DEFAULT_MODEL,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    report_name: str = "gold_reconstruction_llm_smoke_report.md",
    client: ChatClient | None = None,
) -> dict[str, str]:
    artifact_path = Path(artifact_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((artifact_path / "manifest.json").read_text(encoding="utf-8"))
    samples = load_jsonl(artifact_path / "samples.jsonl")
    sampled_samples, notes = select_smoke_samples(samples=samples, sample_size=sample_size, seed=seed)
    sample_manifest = build_smoke_sample_manifest(
        source_artifact_dir=artifact_path,
        samples=sampled_samples,
        sample_size=sample_size,
        seed=seed,
        run_llm=run_llm,
        model=model,
        max_input_chars=max_input_chars,
        max_output_tokens=max_output_tokens,
        selection_notes=notes,
    )
    sample_manifest_path = output_path / "llm_smoke_sample_manifest.json"
    sample_manifest_path.write_text(json.dumps(sample_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    mode = "llm" if run_llm else "dry-run"
    reconstruction_summary = run_gold_reconstruction(
        manifest=manifest,
        samples=sampled_samples,
        output_dir=output_path,
        mode=mode,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
        timeout_seconds=timeout_seconds,
        max_input_chars=max_input_chars,
        max_output_tokens=max_output_tokens,
        client=client,
    )

    source_artifacts: dict[str, str] = {}
    reconstructions: list[dict[str, Any]] = []
    reconstruction_path = output_path / "gold_reconstruction_results.jsonl"
    if run_llm and reconstruction_path.exists():
        reconstructions = load_jsonl(reconstruction_path)
        source_artifacts = run_source_discovery_preparation(
            manifest=manifest,
            samples=sampled_samples,
            source_artifact_dir=artifact_path,
            output_dir=output_path,
            gold_reconstructions=reconstructions,
            use_raw_fallback=False,
        )

    profile = {}
    profile_path = source_artifacts.get("material_source_profile")
    if profile_path:
        profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    queries = load_jsonl(source_artifacts["source_discovery_queries"]) if source_artifacts.get("source_discovery_queries") else []
    seeds = load_jsonl(source_artifacts["initial_material_seed_pack"]) if source_artifacts.get("initial_material_seed_pack") else []
    mock_profile = load_mock_reference_profile(artifact_path)
    report = render_llm_smoke_report(
        sample_manifest=sample_manifest,
        reconstruction_summary=reconstruction_summary,
        reconstructions=reconstructions,
        query_rows=queries,
        seed_rows=seeds,
        profile=profile,
        mock_profile=mock_profile,
    )
    report_path = output_path / report_name
    report_path.write_text(report, encoding="utf-8")

    artifacts = {
        "llm_smoke_sample_manifest": str(sample_manifest_path),
        "model_safe_gold_reconstruction_input": str(output_path / "model_safe_gold_reconstruction_input.jsonl"),
        "gold_reconstruction_llm_smoke_report": str(report_path),
    }
    if reconstruction_path.exists():
        artifacts["gold_reconstruction_results"] = str(reconstruction_path)
    artifacts.update(source_artifacts)
    return artifacts


def select_smoke_samples(
    *,
    samples: list[dict[str, Any]],
    sample_size: int,
    seed: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    if sample_size <= 0:
        return [], ["sample_size was <= 0; no samples selected"]
    rng = random.Random(seed)
    indexed = list(enumerate(samples))
    rng.shuffle(indexed)
    buckets: dict[str, list[tuple[int, dict[str, Any]]]] = {
        "has_parse_warnings": [],
        "has_correct_rate": [],
        "has_easy_wrong_option": [],
        "plain": [],
    }
    for item in indexed:
        sample = item[1]
        if sample.get("parse_warnings"):
            buckets["has_parse_warnings"].append(item)
        elif sample.get("correct_rate"):
            buckets["has_correct_rate"].append(item)
        elif sample.get("easy_wrong_option") or sample.get("wrong_option"):
            buckets["has_easy_wrong_option"].append(item)
        else:
            buckets["plain"].append(item)
    selected: list[tuple[int, dict[str, Any]]] = []
    notes: list[str] = []
    for bucket_name, bucket_items in buckets.items():
        if bucket_items and len(selected) < sample_size:
            selected.append(bucket_items.pop(0))
            notes.append(f"covered bucket: {bucket_name}")
    for item in indexed:
        if len(selected) >= sample_size:
            break
        if item not in selected:
            selected.append(item)
    selected = selected[:sample_size]
    notes.append(f"fixed seed selection with seed={seed}")
    return [sample for _, sample in selected], notes


def build_smoke_sample_manifest(
    *,
    source_artifact_dir: Path,
    samples: list[dict[str, Any]],
    sample_size: int,
    seed: int,
    run_llm: bool,
    model: str,
    max_input_chars: int,
    max_output_tokens: int,
    selection_notes: list[str],
) -> dict[str, Any]:
    return {
        "smoke_version": "v1",
        "source_artifact_dir": str(source_artifact_dir),
        "sample_size": sample_size,
        "actual_sample_count": len(samples),
        "seed": seed,
        "sample_ids": [sample_id_for(sample, index) for index, sample in enumerate(samples)],
        "selection_notes": selection_notes,
        "run_llm": bool(run_llm),
        "model": model,
        "max_input_chars": max_input_chars,
        "max_output_tokens": max_output_tokens,
        "max_retry_per_sample": 1,
    }


def render_llm_smoke_report(
    *,
    sample_manifest: dict[str, Any],
    reconstruction_summary: dict[str, Any],
    reconstructions: list[dict[str, Any]],
    query_rows: list[dict[str, Any]],
    seed_rows: list[dict[str, Any]],
    profile: dict[str, Any],
    mock_profile: dict[str, Any] | None = None,
) -> str:
    confidence = Counter((item.get("reconstruction_summary") or {}).get("confidence") or "missing" for item in reconstructions)
    leakage = Counter((item.get("gold_quality_flags") or {}).get("question_wrapper_leakage_risk") or "missing" for item in reconstructions)
    needs_review = [item for item in reconstructions if (item.get("reconstruction_summary") or {}).get("needs_human_review")]
    parse_ok = [item for item in reconstructions if (item.get("mechanical_checks") or {}).get("json_parse_ok")]
    failed = [item for item in reconstructions if not (item.get("mechanical_checks") or {}).get("json_parse_ok")]
    risk = Counter(row.get("question_bank_contamination_risk") or "missing" for row in query_rows)
    query_quality = profile.get("query_quality_summary") or Counter(query.get("confidence") or "missing" for row in query_rows for query in (row.get("search_queries") or []))
    natural_quality = assess_natural_material_quality(query_rows)
    readiness = assess_source_discovery_readiness(profile=profile, query_rows=query_rows, reconstructions=reconstructions)
    lines = [
        "# Gold Reconstruction LLM Smoke for Source Discovery",
        "",
        "> This is a small-sample smoke for material-source preparation. It is not source search, not material_card writeback, and not protocol-line promotion.",
        "",
        "## Sample Manifest",
        "",
        f"- source_artifact_dir: `{sample_manifest.get('source_artifact_dir')}`",
        f"- requested_sample_size: `{sample_manifest.get('sample_size')}`",
        f"- actual_sample_count: `{sample_manifest.get('actual_sample_count')}`",
        f"- seed: `{sample_manifest.get('seed')}`",
        f"- run_llm: `{sample_manifest.get('run_llm')}`",
        f"- model: `{sample_manifest.get('model')}`",
        f"- max_input_chars: `{sample_manifest.get('max_input_chars')}`",
        f"- max_output_tokens: `{sample_manifest.get('max_output_tokens')}`",
        f"- max_retry_per_sample: `{sample_manifest.get('max_retry_per_sample')}`",
        "",
        "### Sample IDs",
        "",
    ]
    lines.extend([f"- `{sample_id}`" for sample_id in sample_manifest.get("sample_ids") or []] or ["- None"])
    lines.extend(["", "## LLM Reconstruction", ""])
    lines.extend(
        [
            f"- mode: `{reconstruction_summary.get('mode')}`",
            f"- request_count: `{reconstruction_summary.get('input_count')}`",
            f"- input_count: `{reconstruction_summary.get('input_count')}`",
            f"- result_count: `{reconstruction_summary.get('result_count')}`",
            f"- parse_success_count: `{len(parse_ok)}`",
            f"- failed_count: `{len(failed)}`",
            f"- reconstruction_success_rate: `{_rate(len(parse_ok), len(reconstructions))}`",
            f"- needs_human_review_count: `{len(needs_review)}`",
            "",
            "### Confidence Distribution",
            "",
        ]
    )
    lines.extend(counter_lines(confidence))
    lines.extend(["", "### Question Wrapper Leakage Risk Distribution", ""])
    lines.extend(counter_lines(leakage))
    lines.extend(["", "### Failed Sample IDs", ""])
    lines.extend([f"- `{item.get('sample_id')}`" for item in failed] or ["- None"])
    lines.extend(["", "## Source Discovery Preparation Result", ""])
    lines.extend(
        [
            f"- query_rows: `{len(query_rows)}`",
            f"- seed_rows: `{len(seed_rows)}`",
            f"- natural_material_quality: `{natural_quality}`",
            f"- query_de_question_bank_score: `{query_de_question_bank_score(query_rows)}`",
            f"- source_discovery_readiness: `{readiness}`",
            "",
            "### Question Bank Contamination Risk",
            "",
        ]
    )
    lines.extend(counter_lines(risk))
    lines.extend(["", "### Query Quality Distribution", ""])
    lines.extend(counter_lines(query_quality))
    lines.extend(["", "## Mock Comparison", ""])
    if mock_profile:
        mock_risk = mock_profile.get("question_bank_contamination_summary") or {}
        lines.append(f"- mock_gold_risk_distribution: `{json.dumps(mock_risk, ensure_ascii=False)}`")
        lines.append("- note: previous mock reconstruction can remain all high risk because it preserves question-bank/source-pack metadata.")
    else:
        lines.append("- mock reference profile unavailable in this artifact directory.")
    lines.extend(["", "## Restored Human Material Examples", ""])
    for row in query_rows[:3]:
        lines.append(f"### `{row.get('sample_id')}`")
        lines.append("")
        lines.append(row.get("restored_human_material") or "(empty)")
        lines.append("")
    if not query_rows:
        lines.append("- Not available. Dry-run mode does not create LLM reconstruction results.")
    lines.extend(["", "## Search Query Examples", ""])
    for row in query_rows[:3]:
        lines.append(f"### `{row.get('sample_id')}`")
        for query in row.get("search_queries") or []:
            lines.append(f"- [{query.get('query_type')}] {query.get('query')} ({query.get('confidence')})")
        lines.append("")
    if not query_rows:
        lines.append("- Not available.")
    lines.extend(["", "## Human Review Needed", ""])
    review_ids = [row.get("sample_id") for row in query_rows if row.get("needs_human_review")]
    lines.extend([f"- `{sample_id}`" for sample_id in review_ids[:20]] or ["- None"])
    lines.extend(
        [
            "",
            "## Next Step Judgment",
            "",
            f"- ready_for_source_candidate_search: `{readiness}`",
            "- If partial, only low-risk samples should enter a later source_candidate_search pilot.",
            "- Enter source_candidate_search v1 only if restored material is more natural and contamination risk is not all high.",
            "",
            "## Boundaries",
            "",
            "- No web search was executed.",
            "- No original source was confirmed.",
            "- No material_card, card_specs, prompt, validator, generation, runtime, API, UI, or promotion target was changed.",
            "- The card/protocol line was not affected by this material-line smoke.",
        ]
    )
    return "\n".join(lines) + "\n"


def assess_natural_material_quality(query_rows: list[dict[str, Any]]) -> str:
    if not query_rows:
        return "unavailable"
    good = 0
    for row in query_rows:
        text = str(row.get("restored_human_material") or "")
        if len(text) >= 50 and not any(term in text for term in ANTI_QUESTION_BANK_TERMS):
            good += 1
    ratio = good / len(query_rows)
    if ratio >= 0.75:
        return "high"
    if ratio >= 0.4:
        return "medium"
    return "low"


def query_de_question_bank_score(query_rows: list[dict[str, Any]]) -> str:
    queries = [
        str(query.get("query") or "")
        for row in query_rows
        for query in (row.get("search_queries") or [])
    ]
    if not queries:
        return "unavailable"
    contaminated = sum(1 for query in queries if any(term in query for term in ANTI_QUESTION_BANK_TERMS))
    clean_ratio = 1 - (contaminated / len(queries))
    if clean_ratio >= 0.95:
        return "high"
    if clean_ratio >= 0.75:
        return "medium"
    return "low"


def assess_source_discovery_readiness(
    *,
    profile: dict[str, Any],
    query_rows: list[dict[str, Any]],
    reconstructions: list[dict[str, Any]],
) -> str:
    if not reconstructions or not query_rows:
        return "blocked"
    risk = Counter(row.get("question_bank_contamination_risk") or "missing" for row in query_rows)
    high_ratio = risk.get("high", 0) / len(query_rows)
    review_ratio = sum(1 for row in query_rows if row.get("needs_human_review")) / len(query_rows)
    if high_ratio == 0 and review_ratio <= 0.25:
        return "ready"
    if high_ratio < 1.0 and review_ratio < 0.8:
        return "partial"
    return "blocked"


def load_mock_reference_profile(artifact_dir: Path) -> dict[str, Any] | None:
    candidates = [
        artifact_dir / "source_discovery_prep_v1" / "material_source_profile.json",
        artifact_dir / "source_discovery_prep_mock" / "material_source_profile.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def sample_id_for(sample: dict[str, Any], index: int) -> str:
    return str(sample.get("sample_id") or sample.get("id") or sample.get("qid") or f"sample-{index}")


def counter_lines(counter: Counter[str] | dict[str, Any]) -> list[str]:
    if not counter:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in sorted(dict(counter).items())]


def _rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{numerator / denominator:.1%}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small LLM gold reconstruction smoke for source discovery prep.")
    parser.add_argument("--artifact-dir", default="data/leaf_pre_distill/real_word_usage_full_chain_20260425")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--gold-reconstruction-model", default=DEFAULT_MODEL)
    parser.add_argument("--gold-reconstruction-base-url")
    parser.add_argument("--gold-reconstruction-api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--gold-reconstruction-timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--gold-reconstruction-max-input-chars", type=int, default=DEFAULT_MAX_INPUT_CHARS)
    parser.add_argument("--gold-reconstruction-max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--report-name", default="gold_reconstruction_llm_smoke_report.md")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-llm", action="store_true")
    args = parser.parse_args()
    if args.dry_run and args.run_llm:
        raise SystemExit("Choose either --dry-run or --run-llm, not both.")
    artifacts = run_gold_reconstruction_llm_smoke(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        sample_size=args.sample_size,
        seed=args.seed,
        run_llm=bool(args.run_llm),
        model=args.gold_reconstruction_model,
        base_url=args.gold_reconstruction_base_url,
        api_key_env=args.gold_reconstruction_api_key_env,
        timeout_seconds=args.gold_reconstruction_timeout_seconds,
        max_input_chars=args.gold_reconstruction_max_input_chars,
        max_output_tokens=args.gold_reconstruction_max_output_tokens,
        report_name=args.report_name,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

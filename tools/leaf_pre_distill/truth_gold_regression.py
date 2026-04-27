from __future__ import annotations

import json
import random
import re
import argparse
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


SPLIT_NAMES = ("train_observation", "dev_tuning", "eval", "insurance_holdout")

WORD_USAGE_INTENT_TERMS = ("词语", "含义", "指代", "理解", "文中", "加点词", "意思")
MECHANISM_TERMS = ("上下文", "语境", "字面", "指代", "前文", "后文", "概念", "范围")
DISTRACTOR_TERMS = {
    "literal_meaning_trap": ("字面", "表面", "本义"),
    "context_detached": ("脱离语境", "上下文", "无中生有"),
    "concept_swap": ("偷换概念", "概念"),
    "scope_shift": ("范围", "扩大", "缩小"),
}
EXPLANATION_PATH_TERMS = ("上下文", "语境", "指代", "排除", "错误", "因此", "故")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_generated_items(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    return load_jsonl(path)


def load_gold_reconstructions(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    return load_jsonl(path)


def run_truth_gold_regression_from_artifact_dir(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path | None = None,
    generated_items_path: str | Path | None = None,
    split_seed: int = 7,
    train_ratio: float = 0.4,
    dev_ratio: float = 0.2,
    eval_ratio: float = 0.2,
    insurance_ratio: float = 0.2,
) -> dict[str, str]:
    artifact_path = Path(artifact_dir)
    output_path = Path(output_dir) if output_dir is not None else artifact_path
    output_path.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((artifact_path / "manifest.json").read_text(encoding="utf-8"))
    samples = load_jsonl(artifact_path / "samples.jsonl")
    generated_path = generated_items_path
    if generated_path is None and (artifact_path / "generated_items.jsonl").exists():
        generated_path = artifact_path / "generated_items.jsonl"
    reconstruction_path = artifact_path / "gold_reconstruction_results.jsonl"
    if not reconstruction_path.exists() and output_path != artifact_path and (output_path / "gold_reconstruction_results.jsonl").exists():
        reconstruction_path = output_path / "gold_reconstruction_results.jsonl"
    split_manifest, results, report = run_truth_gold_regression(
        manifest=manifest,
        samples=samples,
        source_artifact_dir=artifact_path,
        generated_items=load_generated_items(generated_path),
        gold_reconstructions=load_gold_reconstructions(reconstruction_path if reconstruction_path.exists() else None),
        split_seed=split_seed,
        train_ratio=train_ratio,
        dev_ratio=dev_ratio,
        eval_ratio=eval_ratio,
        insurance_ratio=insurance_ratio,
    )
    split_path = output_path / "truth_gold_split_manifest.json"
    results_path = output_path / "truth_gold_regression_results.json"
    report_path = output_path / "truth_gold_regression_report.md"
    split_path.write_text(json.dumps(split_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    return {
        "truth_gold_split_manifest": str(split_path),
        "truth_gold_regression_results": str(results_path),
        "truth_gold_regression_report": str(report_path),
    }


def build_truth_gold_split_manifest(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    source_artifact_dir: str | Path,
    split_seed: int = 7,
    train_ratio: float = 0.4,
    dev_ratio: float = 0.2,
    eval_ratio: float = 0.2,
    insurance_ratio: float = 0.2,
) -> dict[str, Any]:
    ids = [_sample_id(sample, index) for index, sample in enumerate(samples)]
    rng = random.Random(split_seed)
    shuffled = list(ids)
    rng.shuffle(shuffled)
    counts = _split_counts(
        sample_count=len(shuffled),
        train_ratio=train_ratio,
        dev_ratio=dev_ratio,
        eval_ratio=eval_ratio,
        insurance_ratio=insurance_ratio,
    )
    cursor = 0
    splits: dict[str, list[str]] = {}
    for name in SPLIT_NAMES:
        count = counts[name]
        splits[name] = shuffled[cursor : cursor + count]
        cursor += count
    return {
        "split_version": "v1",
        "source_artifact_dir": str(source_artifact_dir),
        "mother_family_id": manifest.get("mother_family_id"),
        "child_family_id": manifest.get("child_family_id"),
        "leaf_label": manifest.get("leaf_label"),
        "sample_count": len(samples),
        "splits": splits,
        "split_counts": {name: len(splits[name]) for name in SPLIT_NAMES},
        "split_seed": split_seed,
        "split_ratios": {
            "train_observation": train_ratio,
            "dev_tuning": dev_ratio,
            "eval": eval_ratio,
            "insurance_holdout": insurance_ratio,
        },
        "anti_overfit_notes": [
            "insurance_holdout must not be used for axis discovery or prompt tuning",
            "high lexical fit is not proof of true question-production quality",
        ],
    }


def run_truth_gold_regression(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    source_artifact_dir: str | Path,
    generated_items: list[dict[str, Any]] | None = None,
    gold_reconstructions: list[dict[str, Any]] | None = None,
    split_seed: int = 7,
    train_ratio: float = 0.4,
    dev_ratio: float = 0.2,
    eval_ratio: float = 0.2,
    insurance_ratio: float = 0.2,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    split_manifest = build_truth_gold_split_manifest(
        manifest=manifest,
        samples=samples,
        source_artifact_dir=source_artifact_dir,
        split_seed=split_seed,
        train_ratio=train_ratio,
        dev_ratio=dev_ratio,
        eval_ratio=eval_ratio,
        insurance_ratio=insurance_ratio,
    )
    generated = generated_items or []
    results = build_truth_gold_results(
        manifest=manifest,
        samples=samples,
        generated_items=generated,
        gold_reconstructions=gold_reconstructions or [],
        split_manifest=split_manifest,
        source_artifact_dir=source_artifact_dir,
    )
    report = render_truth_gold_regression_report(split_manifest=split_manifest, results=results)
    return split_manifest, results, report


def build_truth_gold_results(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    generated_items: list[dict[str, Any]],
    split_manifest: dict[str, Any],
    source_artifact_dir: str | Path,
    gold_reconstructions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    reconstructed_by_id = {
        str(item.get("sample_id")): item
        for item in (gold_reconstructions or [])
        if item.get("sample_id")
    }
    gold_source = "gold_reconstruction_results" if reconstructed_by_id else "raw_samples"
    sample_by_id = (
        {sample_id: _gold_from_reconstruction(item) for sample_id, item in reconstructed_by_id.items()}
        if reconstructed_by_id
        else {_sample_id(sample, index): sample for index, sample in enumerate(samples)}
    )
    generated_by_id = {_generated_sample_id(item, index): item for index, item in enumerate(generated_items)}
    mode = "generated_comparison" if generated_by_id else "gold_only_baseline"
    sample_results: list[dict[str, Any]] = []
    if generated_by_id:
        split_for_id = {
            sample_id: split
            for split, ids in (split_manifest.get("splits") or {}).items()
            for sample_id in ids
        }
        for sample_id, gold in sample_by_id.items():
            generated = generated_by_id.get(sample_id)
            if generated is None:
                continue
            reconstruction = reconstructed_by_id.get(sample_id)
            sample_results.append(
                _compare_sample(
                    sample_id=sample_id,
                    split=split_for_id.get(sample_id, "unknown"),
                    gold=gold,
                    generated=generated,
                    reconstruction=reconstruction,
                )
            )

    dimensions = _aggregate_dimensions(sample_results)
    split_scores = _aggregate_split_scores(split_manifest=split_manifest, sample_results=sample_results, generated_available=bool(generated_by_id))
    fit_type = _fit_type(sample_results, generated_available=bool(generated_by_id))
    return {
        "regression_version": "v1",
        "mode": mode,
        "gold_source": gold_source,
        "warnings": [] if reconstructed_by_id else ["using raw sample gold, reconstruction not available"],
        "source_artifact_dir": str(source_artifact_dir),
        "mother_family_id": manifest.get("mother_family_id"),
        "child_family_id": manifest.get("child_family_id"),
        "leaf_label": manifest.get("leaf_label"),
        "gold_sample_count": len(samples),
        "generated_item_count": len(generated_items),
        "split_scores": split_scores,
        "dimensions": dimensions,
        "sample_results": sample_results,
        "summary": {
            "fit_type": fit_type,
            "ready_for_user_sample_review": True,
            "ready_for_formalization": False,
            "comparison_available": bool(generated_by_id),
            "gold_source": gold_source,
            "limitation": "Deterministic lexical/heuristic scoring only; not a human quality judgment.",
        },
    }


def render_truth_gold_regression_report(*, split_manifest: dict[str, Any], results: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Truth Gold Regression Report")
    lines.append("")
    lines.append("> This report evaluates distillation quality. It is not formal writeback approval.")
    lines.append("> High fit does not mean true-question quality is good; it may also indicate source overfit.")
    lines.append("")
    lines.append("## Dataset Split")
    lines.append("")
    lines.append(f"- source_artifact_dir: `{split_manifest.get('source_artifact_dir')}`")
    lines.append(f"- mother_family_id: `{split_manifest.get('mother_family_id')}`")
    lines.append(f"- child_family_id: `{split_manifest.get('child_family_id')}`")
    lines.append(f"- leaf_label: `{split_manifest.get('leaf_label')}`")
    lines.append(f"- sample_count: `{split_manifest.get('sample_count')}`")
    lines.append(f"- split_seed: `{split_manifest.get('split_seed')}`")
    lines.append(f"- insurance_holdout_count: `{(split_manifest.get('split_counts') or {}).get('insurance_holdout', 0)}`")
    lines.append("")
    lines.append("| split | count |")
    lines.append("|---|---:|")
    for split, count in (split_manifest.get("split_counts") or {}).items():
        lines.append(f"| `{split}` | {count} |")
    lines.append("")

    lines.append("## Generated Comparison")
    lines.append("")
    lines.append(f"- mode: `{results.get('mode')}`")
    lines.append(f"- gold_source: `{results.get('gold_source')}`")
    lines.append(f"- gold_sample_count: `{results.get('gold_sample_count')}`")
    lines.append(f"- generated_item_count: `{results.get('generated_item_count')}`")
    lines.append(f"- fit_type: `{(results.get('summary') or {}).get('fit_type')}`")
    lines.append(f"- ready_for_formalization: `{(results.get('summary') or {}).get('ready_for_formalization')}`")
    lines.append("")

    lines.append("## Split Scores")
    lines.append("")
    lines.append("| split | gold | compared | avg_alignment | high_overfit_risk |")
    lines.append("|---|---:|---:|---:|---:|")
    for split, score in (results.get("split_scores") or {}).items():
        lines.append(
            "| `{split}` | {gold} | {compared} | {avg} | {risk} |".format(
                split=split,
                gold=score.get("gold_count", 0),
                compared=score.get("compared_count", 0),
                avg=_fmt(score.get("avg_alignment")),
                risk=score.get("high_overfit_risk_count", 0),
            )
        )
    lines.append("")

    lines.append("## Dimension Scores")
    lines.append("")
    lines.append("| dimension | method | confidence | score | limitation |")
    lines.append("|---|---|---|---:|---|")
    for name, info in (results.get("dimensions") or {}).items():
        lines.append(f"| `{name}` | {info.get('method')} | {info.get('confidence')} | {_fmt(info.get('score'))} | {info.get('limitation')} |")
    lines.append("")

    lines.append("## Original Vs Generated Examples")
    lines.append("")
    examples = (results.get("sample_results") or [])[:5]
    if not examples:
        lines.append("- Generated comparison is unavailable. Gold-only baseline artifacts were produced.")
    for item in examples:
        lines.append(f"### `{item.get('sample_id')}` ({item.get('split')})")
        lines.append("")
        lines.append(f"- gold stem: {truncate((item.get('gold') or {}).get('stem'), 180)}")
        lines.append(f"- generated stem: {truncate((item.get('generated') or {}).get('stem'), 180)}")
        lines.append(f"- diagnosis: {'; '.join(item.get('diagnosis') or []) or 'none'}")
        lines.append("")

    failures = [item for item in results.get("sample_results") or [] if item.get("needs_user_review")]
    lines.append("## Failed Or Review-Needed Samples")
    lines.append("")
    if not failures:
        lines.append("- None in the current deterministic pass.")
    for item in failures[:10]:
        lines.append(f"- `{item.get('sample_id')}` ({item.get('split')}): {'; '.join(item.get('diagnosis') or [])}")
    lines.append("")

    lines.append("## User Review Focus")
    lines.append("")
    lines.append("- Check whether generated questions reproduce the same solving mechanism, not just similar wording.")
    lines.append("- Treat insurance_holdout as untouched evidence for anti-overfit checks.")
    lines.append("- Route feedback to material card, question card, prompt guards, validator candidates, or material processing based on the failed dimension.")
    lines.append("- Do not use this report as formal writeback approval.")
    lines.append("")
    return "\n".join(lines)


def render_truth_gold_regression_summary(results: dict[str, Any]) -> str:
    summary = results.get("summary") or {}
    lines = [
        "",
        "## Truth Gold Regression",
        "",
        "> Quality regression evidence only. This is not formal writeback approval.",
        "",
        f"- mode: `{results.get('mode')}`",
        f"- gold_sample_count: `{results.get('gold_sample_count')}`",
        f"- generated_item_count: `{results.get('generated_item_count')}`",
        f"- fit_type: `{summary.get('fit_type')}`",
        f"- ready_for_formalization: `{summary.get('ready_for_formalization')}`",
        "- note: high fit does not imply true-question quality.",
        "",
    ]
    return "\n".join(lines)


def _compare_sample(
    *,
    sample_id: str,
    split: str,
    gold: dict[str, Any],
    generated: dict[str, Any],
    reconstruction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_core = _generated_core(generated)
    scores = {
        "material_alignment": _material_alignment(gold, generated_core),
        "stem_intent_alignment": _keyword_alignment(gold.get("stem"), generated_core.get("stem"), WORD_USAGE_INTENT_TERMS),
        "answer_mechanism_alignment": _keyword_alignment(gold.get("analysis"), generated_core.get("analysis"), MECHANISM_TERMS),
        "distractor_mechanism_alignment": _distractor_alignment(gold, generated_core),
        "explanation_path_alignment": _keyword_alignment(gold.get("analysis"), generated_core.get("analysis"), EXPLANATION_PATH_TERMS),
        "difficulty_signal_alignment": _difficulty_alignment(gold, generated_core),
        "overfit_risk": _overfit_risk(gold, generated_core),
    }
    diagnosis = _diagnose(scores)
    review_needed = bool(diagnosis)
    if reconstruction and (reconstruction.get("reconstruction_summary") or {}).get("needs_human_review"):
        diagnosis.append("reconstructed gold needs human review")
        review_needed = True
    return {
        "sample_id": sample_id,
        "split": split,
        "gold": {
            "stem": gold.get("stem") or "",
            "answer": gold.get("answer") or "",
            "analysis": gold.get("analysis") or "",
            "exam_points": gold.get("exam_points") or "",
        },
        "generated": {
            "stem": generated_core.get("stem") or "",
            "answer": generated_core.get("answer") or "",
            "analysis": generated_core.get("analysis") or "",
            "passage": generated_core.get("passage") or "",
        },
        "scores": scores,
        "diagnosis": diagnosis,
        "needs_user_review": review_needed,
        "gold_reconstruction": {
            "available": reconstruction is not None,
            "confidence": ((reconstruction or {}).get("reconstruction_summary") or {}).get("confidence"),
            "needs_human_review": bool(((reconstruction or {}).get("reconstruction_summary") or {}).get("needs_human_review")),
        },
    }


def _gold_from_reconstruction(item: dict[str, Any]) -> dict[str, Any]:
    material = item.get("gold_material") or {}
    question = item.get("gold_question") or {}
    answer = item.get("answer_mechanism") or {}
    distractor = item.get("distractor_mechanism") or {}
    flags = item.get("gold_quality_flags") or {}
    return {
        "sample_id": item.get("sample_id"),
        "stem": question.get("stem") or "",
        "options": question.get("options") or {},
        "answer": question.get("answer") or "",
        "analysis": answer.get("core_reasoning") or "",
        "passage": material.get("restored_text") or material.get("context_window") or "",
        "raw_text": material.get("restored_text") or "",
        "wrong_option_analysis": json.dumps(distractor, ensure_ascii=False),
        "gold_quality_flags": flags,
        "reconstruction_confidence": (item.get("reconstruction_summary") or {}).get("confidence"),
    }


def _split_counts(*, sample_count: int, train_ratio: float, dev_ratio: float, eval_ratio: float, insurance_ratio: float) -> dict[str, int]:
    if sample_count <= 0:
        return {name: 0 for name in SPLIT_NAMES}
    insurance = max(1, int(round(sample_count * insurance_ratio)))
    remaining = max(0, sample_count - insurance)
    eval_count = min(remaining, max(1, int(round(sample_count * eval_ratio))) if sample_count >= 3 else 0)
    remaining -= eval_count
    dev = min(remaining, max(1, int(round(sample_count * dev_ratio))) if sample_count >= 4 else 0)
    remaining -= dev
    train = remaining
    return {
        "train_observation": train,
        "dev_tuning": dev,
        "eval": eval_count,
        "insurance_holdout": insurance,
    }


def _sample_id(sample: dict[str, Any], index: int) -> str:
    return str(sample.get("sample_id") or sample.get("id") or sample.get("qid") or f"sample-{index}")


def _generated_sample_id(item: dict[str, Any], index: int) -> str:
    return str(item.get("sample_id") or item.get("gold_sample_id") or item.get("source_sample_id") or item.get("id") or f"sample-{index}")


def _generated_core(item: dict[str, Any]) -> dict[str, Any]:
    for key in ("generated", "generated_question", "item", "question"):
        if isinstance(item.get(key), dict):
            merged = dict(item[key])
            for outer_key in ("sample_id", "gold_sample_id", "source_sample_id"):
                if outer_key in item:
                    merged[outer_key] = item[outer_key]
            return merged
    return item


def _material_alignment(gold: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    gold_text = _first_text(gold, ("passage", "material", "raw_text"))
    generated_text = _first_text(generated, ("passage", "material", "raw_text"))
    if not gold_text or not generated_text:
        return _score(None, "lexical", "low", "material text missing on one or both sides")
    return _score(_similarity(gold_text, generated_text), "lexical", "low", "character sequence overlap, not semantic material fidelity")


def _keyword_alignment(gold_text: Any, generated_text: Any, terms: tuple[str, ...]) -> dict[str, Any]:
    gold_hits = _term_hits(str(gold_text or ""), terms)
    generated_hits = _term_hits(str(generated_text or ""), terms)
    if not gold_hits and not generated_hits:
        return _score(None, "heuristic", "low", "no trigger terms on either side")
    if not gold_hits:
        return _score(0.0, "heuristic", "low", "gold trigger terms unavailable")
    return _score(len(gold_hits & generated_hits) / len(gold_hits), "heuristic", "medium", "keyword overlap only")


def _distractor_alignment(gold: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    gold_text = " ".join(str(gold.get(key) or "") for key in ("analysis", "wrong_option_analysis", "options"))
    generated_text = " ".join(str(generated.get(key) or "") for key in ("analysis", "wrong_option_analysis", "options"))
    gold_modes = _distractor_modes(gold_text)
    generated_modes = _distractor_modes(generated_text)
    if not gold_modes and not generated_modes:
        return _score(None, "heuristic", "low", "distractor mechanism terms unavailable")
    if not gold_modes:
        return _score(0.0, "heuristic", "low", "gold distractor modes unavailable")
    return _score(len(gold_modes & generated_modes) / len(gold_modes), "heuristic", "medium", "taxonomy keyword overlap only")


def _difficulty_alignment(gold: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    gold_has_signal = bool(gold.get("correct_rate") or gold.get("easy_wrong_option") or gold.get("wrong_option"))
    generated_has_signal = bool(generated.get("correct_rate") or generated.get("easy_wrong_option") or generated.get("wrong_option") or (generated.get("metadata") or {}).get("difficulty_signal"))
    if not gold_has_signal:
        return _score(None, "metadata", "low", "gold difficulty signal unavailable")
    return _score(1.0 if generated_has_signal else 0.0, "metadata", "medium", "presence/absence only")


def _overfit_risk(gold: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    pairs = [
        (gold.get("stem"), generated.get("stem")),
        (gold.get("analysis"), generated.get("analysis")),
        (_first_text(gold, ("passage", "material", "raw_text")), _first_text(generated, ("passage", "material", "raw_text"))),
    ]
    ratios = [_similarity(str(a), str(b)) for a, b in pairs if a and b]
    if not ratios:
        return _score(None, "lexical", "low", "no comparable text")
    ratio = max(ratios)
    risk = 1.0 if ratio >= 0.85 else 0.5 if ratio >= 0.65 else 0.0
    return {
        "score": risk,
        "band": "high" if risk == 1.0 else "medium" if risk == 0.5 else "low",
        "method": "lexical",
        "confidence": "medium",
        "limitation": "high similarity may be expected for replay but is overfit risk for generation",
        "max_similarity": ratio,
    }


def _score(value: float | None, method: str, confidence: str, limitation: str) -> dict[str, Any]:
    return {
        "score": value,
        "method": method if value is not None else "unavailable",
        "confidence": confidence,
        "limitation": limitation,
    }


def _aggregate_dimensions(sample_results: list[dict[str, Any]]) -> dict[str, Any]:
    names = (
        "material_alignment",
        "stem_intent_alignment",
        "answer_mechanism_alignment",
        "distractor_mechanism_alignment",
        "explanation_path_alignment",
        "difficulty_signal_alignment",
        "overfit_risk",
    )
    if not sample_results:
        return {
            name: {
                "score": None,
                "method": "unavailable",
                "confidence": "low",
                "limitation": "generated comparison unavailable",
            }
            for name in names
        }
    dimensions = {}
    for name in names:
        items = [(result.get("scores") or {}).get(name) or {} for result in sample_results]
        values = [item.get("score") for item in items if item.get("score") is not None]
        dimensions[name] = {
            "score": sum(values) / len(values) if values else None,
            "method": _dominant([item.get("method") for item in items]) or "heuristic",
            "confidence": _dominant([item.get("confidence") for item in items]) or "low",
            "limitation": _dominant([item.get("limitation") for item in items]) or "deterministic first-pass score",
        }
    return dimensions


def _aggregate_split_scores(*, split_manifest: dict[str, Any], sample_results: list[dict[str, Any]], generated_available: bool) -> dict[str, Any]:
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in sample_results:
        by_split[result.get("split") or "unknown"].append(result)
    split_scores = {}
    for split in SPLIT_NAMES:
        rows = by_split.get(split, [])
        alignment_values = []
        high_overfit = 0
        for row in rows:
            scores = row.get("scores") or {}
            for name in ("material_alignment", "stem_intent_alignment", "answer_mechanism_alignment", "distractor_mechanism_alignment", "explanation_path_alignment"):
                value = (scores.get(name) or {}).get("score")
                if value is not None:
                    alignment_values.append(value)
            if (scores.get("overfit_risk") or {}).get("band") == "high":
                high_overfit += 1
        split_scores[split] = {
            "gold_count": len((split_manifest.get("splits") or {}).get(split) or []),
            "compared_count": len(rows),
            "avg_alignment": sum(alignment_values) / len(alignment_values) if alignment_values else None,
            "high_overfit_risk_count": high_overfit,
            "comparison_status": "available" if generated_available else "comparison_unavailable",
        }
    return split_scores


def _fit_type(sample_results: list[dict[str, Any]], *, generated_available: bool) -> str:
    if not generated_available:
        return "gold_only_baseline"
    if not sample_results:
        return "comparison_unavailable"
    avg_overfit = (sum(((row.get("scores") or {}).get("overfit_risk") or {}).get("score") or 0 for row in sample_results) / len(sample_results))
    avg_mechanism = (sum(((row.get("scores") or {}).get("answer_mechanism_alignment") or {}).get("score") or 0 for row in sample_results) / len(sample_results))
    if avg_overfit >= 0.8:
        return "surface_fit_high_overfit_risk"
    if avg_mechanism >= 0.7:
        return "mechanism_approaching"
    return "route_available_not_quality_proven"


def _diagnose(scores: dict[str, dict[str, Any]]) -> list[str]:
    diagnosis = []
    for name, info in scores.items():
        value = info.get("score")
        if name == "overfit_risk":
            if info.get("band") == "high":
                diagnosis.append("generated item uses source wording too closely")
            continue
        if value is None:
            diagnosis.append(f"{name} unavailable")
        elif value < 0.5:
            diagnosis.append(f"{name} weak")
    return diagnosis


def _term_hits(text: str, terms: tuple[str, ...]) -> set[str]:
    return {term for term in terms if term and term in text}


def _distractor_modes(text: str) -> set[str]:
    return {mode for mode, terms in DISTRACTOR_TERMS.items() if any(term in text for term in terms)}


def _similarity(left: str, right: str) -> float:
    left = _normalize_text(left)
    right = _normalize_text(right)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _dominant(values: list[Any]) -> Any:
    counts: dict[Any, int] = {}
    for value in values:
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0][0]


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)


def truncate(value: Any, limit: int = 160) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description="Run truth-gold regression from a leaf_pre_distill artifact directory.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--generated-items")
    parser.add_argument("--split-seed", type=int, default=7)
    parser.add_argument("--train-ratio", type=float, default=0.4)
    parser.add_argument("--dev-ratio", type=float, default=0.2)
    parser.add_argument("--eval-ratio", type=float, default=0.2)
    parser.add_argument("--insurance-ratio", type=float, default=0.2)
    args = parser.parse_args()
    result = run_truth_gold_regression_from_artifact_dir(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        generated_items_path=args.generated_items,
        split_seed=args.split_seed,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        eval_ratio=args.eval_ratio,
        insurance_ratio=args.insurance_ratio,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

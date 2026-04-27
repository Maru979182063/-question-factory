from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.gold_reconstruction_prompt import build_gold_reconstruction_messages
from tools.leaf_pre_distill.llm_field_probe import ChatClient, OpenAICompatibleChatClient


DEFAULT_MODEL = "chat"
DEFAULT_API_KEY_ENV = "LEAF_PRE_DISTILL_LLM_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_INPUT_CHARS = 6000
DEFAULT_MAX_OUTPUT_TOKENS = 1800
QUESTION_WRAPPER_TERMS = [
    "下列",
    "正确的是",
    "不正确的是",
    "本题考查",
    "答案解析",
    "选项",
    "加点词",
    "文中",
    "理解正确",
    "理解不正确",
    "题干",
]
REQUIRED_TOP_LEVEL_FIELDS = [
    "sample_id",
    "reconstruction_version",
    "question_family_guess",
    "leaf_label_guess",
    "reconstruction_summary",
    "gold_material",
    "gold_question",
    "answer_mechanism",
    "distractor_mechanism",
    "gold_quality_flags",
]


def run_gold_reconstruction(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    output_dir: str | Path,
    mode: str = "dry-run",
    model: str = DEFAULT_MODEL,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    client: ChatClient | None = None,
) -> dict[str, Any]:
    if mode not in {"dry-run", "mock", "llm"}:
        raise ValueError("gold reconstruction mode must be dry-run, mock, or llm.")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    input_rows = build_model_safe_inputs(manifest=manifest, samples=samples, max_input_chars=max_input_chars)
    input_path = output_path / "model_safe_gold_reconstruction_input.jsonl"
    _write_jsonl(input_path, input_rows)

    artifacts: dict[str, str] = {"model_safe_gold_reconstruction_input": str(input_path)}
    results: list[dict[str, Any]] = []
    report = ""
    if mode != "dry-run":
        results = reconstruct_gold_rows(
            input_rows=input_rows,
            mode=mode,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            client=client,
        )
        results_path = output_path / "gold_reconstruction_results.jsonl"
        _write_jsonl(results_path, results)
        artifacts["gold_reconstruction_results"] = str(results_path)
        report = render_gold_reconstruction_report(results=results, mode=mode, model=model)
        report_path = output_path / "gold_reconstruction_report.md"
        report_path.write_text(report, encoding="utf-8")
        artifacts["gold_reconstruction_report"] = str(report_path)

    return {
        "enabled": True,
        "mode": mode,
        "model": model,
        "sample_count": len(samples),
        "input_count": len(input_rows),
        "result_count": len(results),
        "artifacts": artifacts,
    }


def build_model_safe_inputs(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> list[dict[str, Any]]:
    return [
        build_model_safe_input_row(
            manifest=manifest,
            sample=sample,
            index=index,
            max_input_chars=max_input_chars,
        )
        for index, sample in enumerate(samples)
    ]


def build_model_safe_input_row(
    *,
    manifest: dict[str, Any],
    sample: dict[str, Any],
    index: int,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    raw_block = _raw_question_block(sample)
    truncated_block, truncated = _truncate(raw_block, max_input_chars)
    row = {
        "sample_id": _sample_id(sample, index),
        "source_file": sample.get("source_file") or sample.get("source_file_name") or "",
        "source_file_name": sample.get("source_file_name") or "",
        "mother_family_id": sample.get("mother_family_id") or manifest.get("mother_family_id") or "",
        "child_family_id": sample.get("child_family_id") or manifest.get("child_family_id") or "",
        "leaf_label": sample.get("leaf_label") or manifest.get("leaf_label") or "",
        "raw_question_block": truncated_block,
        "stem": sample.get("stem") or "",
        "options": sample.get("options") or {},
        "answer": sample.get("answer") or "",
        "analysis": sample.get("analysis") or "",
        "exam_points": sample.get("exam_points") or "",
        "correct_rate": sample.get("correct_rate"),
        "easy_wrong_option": sample.get("easy_wrong_option") or sample.get("wrong_option"),
        "truncation": {
            "truncated": truncated,
            "max_chars": max_input_chars,
        },
    }
    row["input_hash"] = _hash_json(row)
    return row


def reconstruct_gold_rows(
    *,
    input_rows: list[dict[str, Any]],
    mode: str,
    model: str,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    client: ChatClient | None = None,
) -> list[dict[str, Any]]:
    active_client = client
    if mode == "llm" and active_client is None:
        active_client = OpenAICompatibleChatClient(
            base_url=base_url,
            api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
        )
    results = []
    for row in input_rows:
        if mode == "mock" and active_client is None:
            parsed = _mock_reconstruction(row)
            raw_error = ""
        else:
            parsed, raw_error = _complete_with_single_retry(
                client=active_client,
                input_row=row,
                model=model,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
            )
        results.append(normalize_gold_reconstruction(parsed, input_row=row, model=model, mode=mode, raw_model_error=raw_error))
    return results


def _complete_with_single_retry(
    *,
    client: ChatClient,
    input_row: dict[str, Any],
    model: str,
    timeout_seconds: int,
    max_output_tokens: int,
) -> tuple[dict[str, Any], str]:
    errors: list[str] = []
    for _attempt in range(2):
        try:
            raw_text = client.complete(
                messages=build_gold_reconstruction_messages(input_row),
                model=model,
                timeout_seconds=timeout_seconds,
                temperature=0.1,
                max_tokens=max_output_tokens,
            )
            return _parse_json_output(raw_text), ""
        except Exception as exc:
            errors.append(str(exc))
    return {}, " | retry_failed: ".join(errors)


def normalize_gold_reconstruction(
    parsed: dict[str, Any],
    *,
    input_row: dict[str, Any],
    model: str,
    mode: str,
    raw_model_error: str = "",
) -> dict[str, Any]:
    base = _empty_reconstruction(input_row=input_row, model=model, mode=mode, raw_model_error=raw_model_error)
    if isinstance(parsed, dict):
        for key in REQUIRED_TOP_LEVEL_FIELDS:
            if key in parsed:
                base[key] = parsed[key]
    base["sample_id"] = input_row["sample_id"]
    base["reconstruction_version"] = "v1"
    base["source"] = {
        "source_file": input_row.get("source_file") or input_row.get("source_file_name") or "",
        "input_hash": input_row.get("input_hash") or "",
        "model": model,
        "mode": mode,
        "raw_model_error": raw_model_error,
    }
    _normalize_nested(base)
    checks = mechanical_check_reconstruction(base, input_row=input_row)
    base["mechanical_checks"] = checks
    apply_question_wrapper_leakage_check(base)
    if raw_model_error:
        _append_warning(base, "model reconstruction failed; human review required")
        base["reconstruction_summary"]["needs_human_review"] = True
        base["gold_quality_flags"]["is_reconstructable"] = False
        base["gold_quality_flags"]["missing_information"].append("valid model JSON")
    if not all(value is True for value in checks.values() if isinstance(value, bool)):
        _append_warning(base, "mechanical structure checks found issues")
        base["reconstruction_summary"]["needs_human_review"] = True
    return base


def mechanical_check_reconstruction(payload: dict[str, Any], *, input_row: dict[str, Any]) -> dict[str, Any]:
    required_present = all(key in payload for key in REQUIRED_TOP_LEVEL_FIELDS)
    summary = payload.get("reconstruction_summary") or {}
    question = payload.get("gold_question") or {}
    options = question.get("options") or {}
    answer = str(question.get("answer") or "")
    return {
        "json_parse_ok": not bool((payload.get("source") or {}).get("raw_model_error")),
        "required_fields_present": required_present,
        "sample_id_matches": payload.get("sample_id") == input_row.get("sample_id"),
        "answer_exists_in_options": bool(answer and isinstance(options, dict) and answer in options),
        "option_count_reasonable": isinstance(options, dict) and 2 <= len(options) <= 8,
        "has_confidence": summary.get("confidence") in {"high", "medium", "low"},
        "has_warnings": isinstance(summary.get("warnings"), list),
        "has_needs_human_review": isinstance(summary.get("needs_human_review"), bool),
        "has_gold_material": isinstance(payload.get("gold_material"), dict),
        "has_gold_question": isinstance(payload.get("gold_question"), dict),
        "has_answer_mechanism": isinstance(payload.get("answer_mechanism"), dict),
        "evidence_units_is_array": isinstance((payload.get("gold_material") or {}).get("evidence_units"), list),
    }


def apply_question_wrapper_leakage_check(payload: dict[str, Any]) -> str:
    material = payload.setdefault("gold_material", {})
    flags = payload.setdefault("gold_quality_flags", {})
    restored_text = str(material.get("restored_text") or "")
    existing_risk = flags.get("question_wrapper_leakage_risk")
    risk = existing_risk if existing_risk in {"low", "medium", "high"} else "low"
    if restored_text_contains_question_wrapper_terms(restored_text):
        risk = "high"
        flags["requires_source_article"] = True
        payload.setdefault("reconstruction_summary", {})["needs_human_review"] = True
        _append_warning(payload, "restored_text_contains_question_wrapper_terms")
    flags["question_wrapper_leakage_risk"] = risk
    return risk


def restored_text_contains_question_wrapper_terms(text: str) -> bool:
    return any(term in str(text or "") for term in QUESTION_WRAPPER_TERMS)


def render_gold_reconstruction_report(*, results: list[dict[str, Any]], mode: str, model: str) -> str:
    confidence = Counter((item.get("reconstruction_summary") or {}).get("confidence") or "missing" for item in results)
    family = Counter(item.get("question_family_guess") or "unknown" for item in results)
    leakage = Counter((item.get("gold_quality_flags") or {}).get("question_wrapper_leakage_risk") or "missing" for item in results)
    needs_review = [item for item in results if (item.get("reconstruction_summary") or {}).get("needs_human_review")]
    requires_article = [item for item in results if (item.get("gold_quality_flags") or {}).get("requires_source_article")]
    warning_counter: Counter[str] = Counter()
    for item in results:
        for warning in (item.get("reconstruction_summary") or {}).get("warnings") or []:
            warning_counter[str(warning)] += 1
    lines = [
        "# Gold Reconstruction Report",
        "",
        "> This is gold schema reconstruction. It is not formal card, prompt, validator, or protocol field discovery.",
        "> Later truth_gold_regression should prefer reconstructed gold over raw samples when available.",
        "",
        "## Summary",
        "",
        f"- mode: `{mode}`",
        f"- model: `{model}`",
        f"- sample_count: `{len(results)}`",
        f"- needs_human_review_count: `{len(needs_review)}`",
        f"- requires_source_article_count: `{len(requires_article)}`",
        "",
        "## Question Family Guess Distribution",
        "",
    ]
    lines.extend(_counter_lines(family))
    lines.extend(["", "## Confidence Distribution", ""])
    lines.extend(_counter_lines(confidence))
    lines.extend(["", "## Question Wrapper Leakage Risk Distribution", ""])
    lines.extend(_counter_lines(leakage))
    lines.extend(["", "## Warning Type Statistics", ""])
    lines.extend(_counter_lines(warning_counter) if warning_counter else ["- None"])
    lines.extend(["", "## Mechanical Check Summary", ""])
    check_counter: Counter[str] = Counter()
    for item in results:
        for key, value in (item.get("mechanical_checks") or {}).items():
            if value is not True:
                check_counter[key] += 1
    lines.extend(_counter_lines(check_counter) if check_counter else ["- All checked samples passed low-level structure checks."])
    lines.extend(["", "## Low Confidence Samples", ""])
    low = [item for item in results if (item.get("reconstruction_summary") or {}).get("confidence") == "low"]
    lines.extend([f"- `{item.get('sample_id')}`" for item in low[:20]] or ["- None"])
    lines.extend(["", "## Needs Human Review Samples", ""])
    lines.extend([f"- `{item.get('sample_id')}`: {'; '.join((item.get('reconstruction_summary') or {}).get('warnings') or [])}" for item in needs_review[:20]] or ["- None"])
    lines.extend(["", "## Examples", ""])
    for item in results[:5]:
        summary = item.get("reconstruction_summary") or {}
        question = item.get("gold_question") or {}
        lines.extend(
            [
                f"### `{item.get('sample_id')}`",
                "",
                f"- family_guess: `{item.get('question_family_guess') or ''}`",
                f"- confidence: `{summary.get('confidence') or ''}`",
                f"- needs_human_review: `{summary.get('needs_human_review')}`",
                f"- stem: {str(question.get('stem') or '')[:180]}",
                "",
            ]
        )
    return "\n".join(lines)


def _empty_reconstruction(*, input_row: dict[str, Any], model: str, mode: str, raw_model_error: str) -> dict[str, Any]:
    return {
        "sample_id": input_row["sample_id"],
        "reconstruction_version": "v1",
        "question_family_guess": "",
        "leaf_label_guess": input_row.get("leaf_label") or "",
        "reconstruction_summary": {
            "what_was_reconstructed": "",
            "why_this_reconstruction_is_needed": "",
            "confidence": "low",
            "needs_human_review": bool(raw_model_error),
            "warnings": [],
        },
        "gold_material": {
            "restored_text": "",
            "context_window": "",
            "material_units": [],
            "evidence_units": [],
            "material_boundary_note": "",
        },
        "gold_question": {
            "stem": input_row.get("stem") or "",
            "options": input_row.get("options") or {},
            "answer": input_row.get("answer") or "",
            "correct_option_text": "",
        },
        "answer_mechanism": {
            "core_reasoning": "",
            "uniqueness_source": "",
            "evidence_mapping": [],
        },
        "distractor_mechanism": {
            "distractor_modes": [],
            "easy_wrong_reason": "",
            "option_diagnostics": {},
        },
        "gold_quality_flags": {
            "is_reconstructable": not bool(raw_model_error),
            "missing_information": [],
            "ambiguous_points": [],
            "requires_source_article": False,
            "question_wrapper_leakage_risk": "low",
            "overfit_risk_note": "",
        },
        "mechanical_checks": {},
        "source": {
            "source_file": input_row.get("source_file") or "",
            "input_hash": input_row.get("input_hash") or "",
            "model": model,
            "mode": mode,
            "raw_model_error": raw_model_error,
        },
    }


def _mock_reconstruction(input_row: dict[str, Any]) -> dict[str, Any]:
    options = input_row.get("options") if isinstance(input_row.get("options"), dict) else {}
    answer = str(input_row.get("answer") or "")
    return {
        "sample_id": input_row["sample_id"],
        "reconstruction_version": "v1",
        "question_family_guess": input_row.get("mother_family_id") or "",
        "leaf_label_guess": input_row.get("leaf_label") or "",
        "reconstruction_summary": {
            "what_was_reconstructed": "Unified gold schema reconstructed from provided true-question fields.",
            "why_this_reconstruction_is_needed": "A normalized gold reference is needed before regression comparison.",
            "confidence": "medium",
            "needs_human_review": False,
            "warnings": [],
        },
        "gold_material": {
            "restored_text": input_row.get("raw_question_block") or "",
            "context_window": input_row.get("raw_question_block") or "",
            "material_units": [],
            "evidence_units": [],
            "material_boundary_note": "",
        },
        "gold_question": {
            "stem": input_row.get("stem") or "",
            "options": options,
            "answer": answer,
            "correct_option_text": str(options.get(answer) or ""),
        },
        "answer_mechanism": {
            "core_reasoning": input_row.get("analysis") or "",
            "uniqueness_source": "",
            "evidence_mapping": [],
        },
        "distractor_mechanism": {
            "distractor_modes": [],
            "easy_wrong_reason": str(input_row.get("easy_wrong_option") or ""),
            "option_diagnostics": {},
        },
        "gold_quality_flags": {
            "is_reconstructable": True,
            "missing_information": [],
            "ambiguous_points": [],
            "requires_source_article": False,
            "question_wrapper_leakage_risk": "low",
            "overfit_risk_note": "",
        },
    }


def _normalize_nested(payload: dict[str, Any]) -> None:
    summary = payload.setdefault("reconstruction_summary", {})
    summary["confidence"] = summary.get("confidence") if summary.get("confidence") in {"high", "medium", "low"} else "low"
    summary["needs_human_review"] = bool(summary.get("needs_human_review"))
    summary["warnings"] = _list(summary.get("warnings"))
    material = payload.setdefault("gold_material", {})
    material["material_units"] = _list(material.get("material_units"))
    material["evidence_units"] = _list(material.get("evidence_units"))
    question = payload.setdefault("gold_question", {})
    if not isinstance(question.get("options"), dict):
        question["options"] = {}
    answer = payload.setdefault("answer_mechanism", {})
    answer["evidence_mapping"] = _list(answer.get("evidence_mapping"))
    distractor = payload.setdefault("distractor_mechanism", {})
    distractor["distractor_modes"] = _list(distractor.get("distractor_modes"))
    if not isinstance(distractor.get("option_diagnostics"), dict):
        distractor["option_diagnostics"] = {}
    flags = payload.setdefault("gold_quality_flags", {})
    flags["is_reconstructable"] = bool(flags.get("is_reconstructable"))
    flags["missing_information"] = _list(flags.get("missing_information"))
    flags["ambiguous_points"] = _list(flags.get("ambiguous_points"))
    flags["requires_source_article"] = bool(flags.get("requires_source_article"))
    if flags.get("question_wrapper_leakage_risk") not in {"low", "medium", "high"}:
        flags["question_wrapper_leakage_risk"] = "low"


def _append_warning(payload: dict[str, Any], warning: str) -> None:
    warnings = (payload.setdefault("reconstruction_summary", {})).setdefault("warnings", [])
    if warning not in warnings:
        warnings.append(warning)


def _raw_question_block(sample: dict[str, Any]) -> str:
    parts = []
    for key in ("raw_text", "stem", "options", "answer", "analysis", "exam_points"):
        value = sample.get(key)
        if value:
            parts.append(f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value}")
    return "\n".join(parts)


def _truncate(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    return value[:max_chars], True


def _sample_id(sample: dict[str, Any], index: int) -> str:
    return str(sample.get("sample_id") or sample.get("id") or sample.get("qid") or f"sample-{index}")


def _hash_json(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _parse_json_output(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model output was not a JSON object")
    return parsed


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _counter_lines(counter: Counter[str]) -> list[str]:
    return [f"- `{key}`: {count}" for key, count in sorted(counter.items())]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run model-based gold reconstruction over samples.jsonl.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=("dry-run", "mock", "llm"), default="dry-run")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-input-chars", type=int, default=DEFAULT_MAX_INPUT_CHARS)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in Path(args.samples).read_text(encoding="utf-8").splitlines() if line.strip()]
    result = run_gold_reconstruction(
        manifest=manifest,
        samples=samples,
        output_dir=args.output_dir,
        mode=args.mode,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        timeout_seconds=args.timeout_seconds,
        max_input_chars=args.max_input_chars,
        max_output_tokens=args.max_output_tokens,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

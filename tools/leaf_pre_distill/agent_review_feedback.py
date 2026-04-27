from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.agent_review_feedback_prompt import build_agent_review_feedback_messages
from tools.leaf_pre_distill.llm_field_probe import (
    ChatClient,
    OpenAICompatibleChatClient,
    _parse_chat_completion_body,
)


DEFAULT_MODEL = "chat"
DEFAULT_API_KEY_ENV = "LEAF_PRE_DISTILL_LLM_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_OUTPUT_TOKENS = 900

ARTIFACT_NAMES = {
    "input": "agent_review_feedback_input.json",
    "normalized": "agent_review_feedback_normalized.json",
    "report": "agent_review_feedback_report.md",
}

DIMENSION_TARGET_LINE = {
    "difficulty_too_low": "question_card",
    "difficulty_too_high": "question_card",
    "exam_style_mismatch": "question_card",
    "distractor_weakness": "question_card",
    "answer_too_obvious": "question_card",
    "explanation_weak": "question_card",
    "family_fit_mismatch": "question_card",
    "reasoning_depth_insufficient": "question_card",
    "material_too_short": "material_line",
    "material_too_long": "material_line",
    "context_dependency_insufficient": "material_line",
    "source_like_material_weak": "material_line",
    "question_bank_style_contamination": "material_line",
    "material_noise_high": "material_line",
    "material_information_density_low": "material_line",
    "prompt_instruction_weak": "prompt_assets",
    "validator_too_loose": "validator",
    "validator_too_strict": "validator",
    "runtime_binding_unclear": "runtime",
    "material_bridge_mismatch": "runtime",
}


def build_feedback_input(
    *,
    raw_feedback: str,
    reviewer: str = "human",
    target_scope: str = "batch",
    target_artifacts: list[str] | None = None,
    family_context: dict[str, Any] | None = None,
    sample_ids: list[str] | None = None,
    artifact_paths: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "feedback_version": "v1",
        "reviewer": reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "target_scope": target_scope,
        "target_artifacts": list(target_artifacts or []),
        "raw_feedback": raw_feedback,
        "context": {
            "family_context": dict(family_context or {}),
            "sample_ids": list(sample_ids or []),
            "artifact_paths": list(artifact_paths or []),
        },
    }


def run_agent_review_feedback_normalization(
    *,
    feedback_input: dict[str, Any],
    output_dir: str | Path,
    mode: str = "dry-run",
    model: str = DEFAULT_MODEL,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    client: ChatClient | None = None,
) -> dict[str, str]:
    if mode not in {"dry-run", "mock", "llm"}:
        raise ValueError("agent review feedback mode must be dry-run, mock, or llm.")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    input_path = output_path / ARTIFACT_NAMES["input"]
    normalized_path = output_path / ARTIFACT_NAMES["normalized"]
    report_path = output_path / ARTIFACT_NAMES["report"]
    _write_json(input_path, feedback_input)

    normalized: dict[str, Any] | None = None
    if mode == "mock":
        normalized = normalize_feedback_output(
            {"normalized_feedback": heuristic_feedback_dimensions(str(feedback_input.get("raw_feedback") or ""))},
            feedback_input=feedback_input,
            model="mock",
        )
    elif mode == "llm":
        normalized = _run_llm_feedback_normalization(
            feedback_input=feedback_input,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            client=client,
        )

    if normalized is None:
        normalized = build_disabled_feedback(feedback_input=feedback_input, mode=mode)
    _write_json(normalized_path, normalized)
    report_path.write_text(render_agent_review_feedback_report(normalized), encoding="utf-8")
    return {
        "agent_review_feedback_input": str(input_path),
        "agent_review_feedback_normalized": str(normalized_path),
        "agent_review_feedback_report": str(report_path),
    }


def normalize_feedback_output(
    payload: dict[str, Any],
    *,
    feedback_input: dict[str, Any],
    model: str,
    error: str | None = None,
) -> dict[str, Any]:
    raw_items = payload.get("normalized_feedback") or []
    normalized_items = []
    warnings = list(payload.get("warnings") or [])
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension") or "").strip()
        if dimension not in DIMENSION_TARGET_LINE:
            warnings.append(f"ignored_unknown_feedback_dimension:{dimension}")
            continue
        target_line = str(item.get("target_line") or DIMENSION_TARGET_LINE[dimension])
        if target_line not in {"question_card", "material_line", "prompt_assets", "validator", "runtime", "unknown"}:
            target_line = DIMENSION_TARGET_LINE[dimension]
        severity = str(item.get("severity") or "medium")
        if severity not in {"low", "medium", "high"}:
            severity = "medium"
        normalized_items.append(
            {
                "dimension": dimension,
                "severity": severity,
                "target_line": target_line,
                "evidence_hint": str(item.get("evidence_hint") or ""),
                "suggested_next_action": str(item.get("suggested_next_action") or _default_next_action(dimension)),
                "requires_regression": True,
                "requires_human_review": True,
            }
        )
    routing = {
        "question_card_line": any(item["target_line"] == "question_card" for item in normalized_items),
        "material_line": any(item["target_line"] == "material_line" for item in normalized_items),
        "prompt_assets_line": any(item["target_line"] == "prompt_assets" for item in normalized_items),
        "validator_line": any(item["target_line"] == "validator" for item in normalized_items),
        "runtime_line": any(item["target_line"] == "runtime" for item in normalized_items),
    }
    status = "normalized" if normalized_items and error is None else "needs_human_review"
    result = {
        "feedback_version": "v1",
        "status": status,
        "mode": "llm" if model != "mock" else "mock",
        "model": model,
        "reviewer": feedback_input.get("reviewer") or "human",
        "reviewed_at": feedback_input.get("reviewed_at"),
        "target_scope": feedback_input.get("target_scope"),
        "target_artifacts": list(feedback_input.get("target_artifacts") or []),
        "raw_feedback": feedback_input.get("raw_feedback") or "",
        "normalized_feedback": normalized_items,
        "routing": routing,
        "warnings": warnings,
        "writeback_allowed": False,
        "formalized": False,
        "requires_human_review": True,
        "requires_regression": True,
        "limits": [
            "User feedback is evidence, not direct config change.",
            "This artifact does not write question cards, material cards, prompt assets, validators, or runtime mappings.",
        ],
    }
    if error:
        result["error"] = error
    assert_feedback_boundaries(result)
    return result


def heuristic_feedback_dimensions(raw_feedback: str) -> list[dict[str, Any]]:
    text = raw_feedback.lower()
    checks = [
        (("太简单", "简单", "容易", "too easy"), "difficulty_too_low", "high"),
        (("太难", "难度太高", "too hard"), "difficulty_too_high", "medium"),
        (("不像真题", "风格不像", "exam style"), "exam_style_mismatch", "medium"),
        (("干扰项", "不够迷惑", "迷惑性弱", "distractor"), "distractor_weakness", "high"),
        (("太直给", "答案明显", "选项太直"), "answer_too_obvious", "high"),
        (("解析", "没说服力", "解释弱"), "explanation_weak", "medium"),
        (("不是这个考点", "题型不对", "考点不对"), "family_fit_mismatch", "high"),
        (("推理", "思考太浅", "深度不够"), "reasoning_depth_insufficient", "medium"),
        (("材料太短", "字数太少", "文本太短", "太短"), "material_too_short", "high"),
        (("材料太长", "文本太长"), "material_too_long", "medium"),
        (("语境依赖不够", "上下文不够"), "context_dependency_insufficient", "medium"),
        (("不像自然原文", "不像原文", "人话材料弱"), "source_like_material_weak", "high"),
        (("题库解析", "像题库", "答案解析"), "question_bank_style_contamination", "high"),
        (("噪声", "杂乱"), "material_noise_high", "medium"),
        (("信息密度低", "内容太空"), "material_information_density_low", "medium"),
        (("提示词", "prompt"), "prompt_instruction_weak", "medium"),
        (("校验太松", "validator too loose"), "validator_too_loose", "medium"),
        (("校验太严", "validator too strict"), "validator_too_strict", "medium"),
        (("绑定不清", "runtime"), "runtime_binding_unclear", "medium"),
        (("材料桥接", "materialbridge", "bridge mismatch"), "material_bridge_mismatch", "medium"),
    ]
    found: list[dict[str, Any]] = []
    for keywords, dimension, severity in checks:
        if any(keyword.lower() in text for keyword in keywords):
            found.append(
                {
                    "dimension": dimension,
                    "severity": severity,
                    "target_line": DIMENSION_TARGET_LINE[dimension],
                    "evidence_hint": raw_feedback[:160],
                    "suggested_next_action": _default_next_action(dimension),
                    "requires_regression": True,
                    "requires_human_review": True,
                }
            )
    if not found and raw_feedback.strip():
        found.append(
            {
                "dimension": "exam_style_mismatch",
                "severity": "medium",
                "target_line": "question_card",
                "evidence_hint": raw_feedback[:160],
                "suggested_next_action": "人工复核该反馈是否对应题卡、材料、prompt、validator 或 runtime。",
                "requires_regression": True,
                "requires_human_review": True,
            }
        )
    return found


def build_disabled_feedback(*, feedback_input: dict[str, Any], mode: str) -> dict[str, Any]:
    return {
        "feedback_version": "v1",
        "status": "disabled" if mode == "dry-run" else "needs_human_review",
        "mode": mode,
        "model": "",
        "reviewer": feedback_input.get("reviewer") or "human",
        "reviewed_at": feedback_input.get("reviewed_at"),
        "target_scope": feedback_input.get("target_scope"),
        "target_artifacts": list(feedback_input.get("target_artifacts") or []),
        "raw_feedback": feedback_input.get("raw_feedback") or "",
        "normalized_feedback": [],
        "routing": {
            "question_card_line": False,
            "material_line": False,
            "prompt_assets_line": False,
            "validator_line": False,
            "runtime_line": False,
        },
        "warnings": ["dry-run generated input only; feedback is not semantically normalized."],
        "writeback_allowed": False,
        "formalized": False,
        "requires_human_review": True,
        "requires_regression": True,
        "limits": ["User feedback is evidence, not direct config change."],
    }


def assert_feedback_boundaries(payload: dict[str, Any]) -> None:
    if payload.get("writeback_allowed") is True:
        raise ValueError("agent review feedback cannot allow writeback")
    if payload.get("formalized") is True:
        raise ValueError("agent review feedback cannot be formalized")
    text = json.dumps(payload, ensure_ascii=False)
    forbidden = ["card_specs_write", "prompt_assets_write", "validator_write", "runtime_write"]
    for token in forbidden:
        if f'"{token}": true' in text.lower():
            raise ValueError(f"agent review feedback cannot include {token}=true")


def render_agent_review_feedback_report(feedback: dict[str, Any]) -> str:
    lines = [
        "# Agent Review Feedback",
        "",
        "> 用户反馈是 evidence，不是配置修改。不会直接写题卡、材料卡、prompt、validator 或 runtime。",
        "",
        f"- status: `{feedback.get('status')}`",
        f"- mode: `{feedback.get('mode')}`",
        f"- reviewer: `{feedback.get('reviewer')}`",
        f"- target_scope: `{feedback.get('target_scope')}`",
        f"- writeback_allowed: `{bool(feedback.get('writeback_allowed'))}`",
        f"- formalized: `{bool(feedback.get('formalized'))}`",
        "",
        "## Normalized Feedback",
        "",
    ]
    items = feedback.get("normalized_feedback") or []
    if not items:
        lines.append("- none")
    else:
        lines.append("| dimension | severity | target_line | next_action |")
        lines.append("|---|---|---|---|")
        for item in items:
            lines.append(
                f"| `{item.get('dimension')}` | `{item.get('severity')}` | `{item.get('target_line')}` | {item.get('suggested_next_action') or ''} |"
            )
    warnings = feedback.get("warnings") or []
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"


def _run_llm_feedback_normalization(
    *,
    feedback_input: dict[str, Any],
    model: str,
    base_url: str | None,
    api_key_env: str,
    timeout_seconds: int,
    max_output_tokens: int,
    client: ChatClient | None,
) -> dict[str, Any]:
    try:
        active_client = client or OpenAICompatibleChatClient(
            base_url=base_url,
            api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
        )
        raw_text = active_client.complete(
            messages=build_agent_review_feedback_messages(feedback_input),
            model=model,
            timeout_seconds=timeout_seconds,
            temperature=0.1,
            max_tokens=max_output_tokens,
        )
        parsed = _parse_json_output(raw_text)
        return normalize_feedback_output(parsed, feedback_input=feedback_input, model=model)
    except Exception as exc:
        return normalize_feedback_output(
            {"normalized_feedback": [], "warnings": ["LLM feedback normalization failed."]},
            feedback_input=feedback_input,
            model=model,
            error=str(exc),
        )


def _parse_json_output(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        parsed = _parse_chat_completion_body(raw_text)
        content = str((parsed.get("choices") or [{}])[0].get("message", {}).get("content") or "")
        return json.loads(content)


def _default_next_action(dimension: str) -> str:
    target = DIMENSION_TARGET_LINE.get(dimension, "unknown")
    if target == "material_line":
        return "进入材料线 evidence 复核和 material quality regression。"
    if target == "question_card":
        return "进入题卡/候选轴/难度回归复核。"
    if target == "prompt_assets":
        return "进入 prompt assets draft 与回归复核。"
    if target == "validator":
        return "进入 validator contract draft 与回归复核。"
    if target == "runtime":
        return "进入 runtime activation plan 复核。"
    return "需要人工判断反馈归属。"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize human review feedback into evidence artifacts.")
    parser.add_argument("--raw-feedback", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=["dry-run", "mock", "llm"], default="dry-run")
    parser.add_argument("--reviewer", default="human")
    parser.add_argument("--target-scope", default="batch")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    feedback_input = build_feedback_input(
        raw_feedback=args.raw_feedback,
        reviewer=args.reviewer,
        target_scope=args.target_scope,
    )
    artifacts = run_agent_review_feedback_normalization(
        feedback_input=feedback_input,
        output_dir=args.output_dir,
        mode=args.mode,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.leaf_pre_distill.llm_field_probe import ChatClient, OpenAICompatibleChatClient
from tools.leaf_pre_distill.material_protocol_draft import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    build_bridge_mapping_from_family,
    build_default_quality_dimensions,
    build_material_protocol_draft_input_digest,
    build_prompt_assets_draft,
    build_system_alignment_findings,
    infer_material_requirements,
    next_required_evidence,
    resolve_evidence_paths,
    summarize_alignment,
    validate_material_protocol_bundle,
)
from tools.leaf_pre_distill.material_protocol_split_runtime import execute_split_stages
from tools.leaf_pre_distill.material_protocol_split_state import STAGE_FILE_BY_KEY


SPLIT_ARTIFACTS = {
    "system_alignment_findings": "system_alignment_findings.json",
    "material_protocol_draft_input_digest": "material_protocol_draft_input_digest.json",
    "material_evidence_map": "material_evidence_map.json",
    "material_semantic_requirements_draft": "material_semantic_requirements_draft.json",
    "material_card_draft": "material_card_draft.json",
    "material_line_prompt_assets_draft": "material_line_prompt_assets_draft.json",
    "material_quality_regression_draft": "material_quality_regression_draft.json",
    "material_bridge_mapping_draft": "material_bridge_mapping_draft.json",
    "material_protocol_split_pipeline_report": "material_protocol_split_pipeline_report.md",
}

DRAFT_FLAGS = {
    "status": "draft_only",
    "formalized": False,
    "writeback_allowed": False,
    "requires_human_review": True,
    "requires_regression": True,
}


def run_material_protocol_split_pipeline(
    *,
    artifact_dir: str | Path,
    output_dir: str | Path | None = None,
    mode: str = "dry-run",
    model: str = DEFAULT_MODEL,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    client: ChatClient | None = None,
    repo_root: str | Path | None = None,
    resume: bool = False,
    max_stage_retries: int = 1,
    gold_reconstruction_results: str | Path | None = None,
    truth_gold_regression_results: str | Path | None = None,
    truth_gold_split_manifest: str | Path | None = None,
    source_discovery_queries: str | Path | None = None,
    material_source_profile: str | Path | None = None,
    source_candidate_summary: str | Path | None = None,
    source_candidate_review: str | Path | None = None,
    source_seed_registry: str | Path | None = None,
    crawl_seed_manifest: str | Path | None = None,
    initial_plan_doc: str | Path | None = None,
) -> dict[str, str]:
    if mode not in {"dry-run", "mock", "llm"}:
        raise ValueError("material protocol split pipeline mode must be dry-run, mock, or llm.")
    artifact_path = Path(artifact_dir)
    output_path = Path(output_dir) if output_dir is not None else artifact_path
    output_path.mkdir(parents=True, exist_ok=True)
    root = Path(repo_root) if repo_root is not None else Path.cwd()

    alignment = build_system_alignment_findings(root)
    evidence_paths = resolve_evidence_paths(
        artifact_dir=artifact_path,
        gold_reconstruction_results=gold_reconstruction_results,
        truth_gold_regression_results=truth_gold_regression_results,
        truth_gold_split_manifest=truth_gold_split_manifest,
        source_discovery_queries=source_discovery_queries,
        material_source_profile=material_source_profile,
        source_candidate_summary=source_candidate_summary,
        source_candidate_review=source_candidate_review,
        source_seed_registry=source_seed_registry,
        crawl_seed_manifest=crawl_seed_manifest,
        initial_plan_doc=initial_plan_doc,
    )
    digest = build_material_protocol_draft_input_digest(
        artifact_dir=artifact_path,
        evidence_paths=evidence_paths,
        system_alignment_findings=alignment,
        max_input_chars=max_input_chars,
    )

    artifacts: dict[str, str] = {}
    stages_dir = output_path / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / SPLIT_ARTIFACTS["system_alignment_findings"], alignment)
    _write_json(output_path / SPLIT_ARTIFACTS["material_protocol_draft_input_digest"], digest)
    artifacts["system_alignment_findings"] = str(output_path / SPLIT_ARTIFACTS["system_alignment_findings"])
    artifacts["material_protocol_draft_input_digest"] = str(output_path / SPLIT_ARTIFACTS["material_protocol_draft_input_digest"])

    evidence_map = build_material_evidence_map(digest=digest, alignment=alignment)
    _write_json(output_path / SPLIT_ARTIFACTS["material_evidence_map"], evidence_map)
    artifacts["material_evidence_map"] = str(output_path / SPLIT_ARTIFACTS["material_evidence_map"])
    _write_json(stages_dir / STAGE_FILE_BY_KEY["material_evidence_map"], evidence_map)

    stages: dict[str, dict[str, Any]] = {}
    state: dict[str, Any] = {}
    runtime_artifacts: dict[str, str] = {}
    if mode != "dry-run":
        baseline_stages = build_mock_split_stages(digest=digest, alignment=alignment, evidence_map=evidence_map)
        llm_builder = build_llm_stage_builder(
            digest=digest,
            alignment=alignment,
            evidence_map=evidence_map,
            baseline_stages=baseline_stages,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        def stage_builder(stage_key: str, completed: dict[str, dict[str, Any]]) -> dict[str, Any]:
            if stage_key == "material_evidence_map":
                return evidence_map
            if mode == "mock":
                return baseline_stages[stage_key]
            return llm_builder(stage_key, completed)

        stages, state, runtime_artifacts = execute_split_stages(
            output_dir=output_path,
            mode=mode,
            stage_builder=stage_builder,
            stage_validator=lambda candidate: validate_split_stages(stages=candidate, digest=digest, partial=True),
            resume=resume,
            max_retries=max_stage_retries,
        )
        artifacts.update(runtime_artifacts)
        for key, path in runtime_artifacts.items():
            if key in SPLIT_ARTIFACTS:
                final_path = output_path / SPLIT_ARTIFACTS[key]
                _write_json(final_path, json.loads(Path(path).read_text(encoding="utf-8")))
                artifacts[key] = str(final_path)
    else:
        from tools.leaf_pre_distill.material_protocol_split_state import initial_pipeline_state, save_pipeline_state, update_stage_state
        from tools.leaf_pre_distill.material_protocol_split_stage_report import write_pipeline_stage_reports

        state = initial_pipeline_state(mode=mode, output_dir=output_path)
        update_stage_state(
            state,
            stage_key="material_evidence_map",
            status="success",
            output_path=stages_dir / STAGE_FILE_BY_KEY["material_evidence_map"],
            retry_count=0,
            duration_seconds=0.0,
        )
        state_path = output_path / "pipeline_state.json"
        save_pipeline_state(state_path, state)
        artifacts["pipeline_state"] = str(state_path)
        artifacts.update(write_pipeline_stage_reports(output_dir=output_path, state=state))

    report = render_split_pipeline_report(
        mode=mode,
        digest=digest,
        alignment=alignment,
        evidence_map=evidence_map,
        stages=stages,
        stage_errors=collect_stage_errors(state),
    )
    report_path = output_path / SPLIT_ARTIFACTS["material_protocol_split_pipeline_report"]
    report_path.write_text(report, encoding="utf-8")
    artifacts["material_protocol_split_pipeline_report"] = str(report_path)
    return artifacts


def build_material_evidence_map(*, digest: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
    family = digest.get("family_context") or {}
    missing = list(digest.get("missing_evidence") or [])
    evidence_paths = digest.get("evidence_paths") or {}
    return {
        "map_version": "v1",
        "asset_type": "material_evidence_map",
        **DRAFT_FLAGS,
        "family_context": family,
        "evidence_paths": evidence_paths,
        "evidence_gaps": missing,
        "evidence_claims": {
            "gold_reconstruction": digest.get("gold_reconstruction_summary") or {},
            "truth_gold_regression": digest.get("truth_gold_regression_summary") or {},
            "truth_gold_split": digest.get("truth_gold_split_summary") or {},
            "source_discovery": digest.get("source_discovery_summary") or {},
            "source_candidate": digest.get("source_candidate_summary") or {},
            "source_review": digest.get("source_review_summary") or {},
            "seed_registry": digest.get("seed_registry_summary") or {},
            "system_alignment": summarize_alignment(alignment),
        },
        "blocked_claims": [
            "No verified original source is available unless a later verification artifact says so.",
            "No source body is available unless a source_body_fetch artifact is provided.",
            "No source/gold alignment is complete unless a source_gold_alignment artifact is provided.",
            "No material card formalization is allowed from this map.",
        ],
        "next_required_evidence": next_required_evidence(missing),
        "limits": [
            "Evidence map only.",
            "Does not call passage_service.",
            "Does not verify sources.",
            "Does not write material cards.",
        ],
    }


def build_mock_split_stages(
    *,
    digest: dict[str, Any],
    alignment: dict[str, Any],
    evidence_map: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    family = dict(digest.get("family_context") or {})
    gaps = list(digest.get("missing_evidence") or [])
    confirmed_mapping = alignment.get("recommended_minimal_compatible_mapping") or {}
    requirements = infer_material_requirements(digest)
    semantic = {
        "draft_version": "v1",
        "asset_type": "material_semantic_requirements_draft",
        **DRAFT_FLAGS,
        "family_context": family,
        "evidence_map_ref": "material_evidence_map.json",
        "semantic_requirements": {
            "material_role_hypothesis": "Materials must support the solving action implied by the current family evidence; this is family-specific and not universal.",
            "source_type_hints": requirements.get("likely_source_type") or [],
            "context_dependency": requirements.get("context_dependency"),
            "must_contain": requirements.get("must_contain") or [],
            "must_avoid": requirements.get("must_avoid") or [],
        },
        "source_body_required": True,
        "source_gold_alignment_required": True,
        "hypothesis_only": True,
        "evidence_gaps": gaps,
        "next_required_evidence": next_required_evidence(gaps),
        "limits": ["Does not create material card fields directly."],
    }
    card = {
        "draft_version": "v1",
        "asset_type": "material_card_draft",
        **DRAFT_FLAGS,
        "material_card_id_draft": family.get("material_card_id_draft"),
        "family_binding": family,
        "evidence_map_ref": "material_evidence_map.json",
        "semantic_requirements_ref": "material_semantic_requirements_draft.json",
        "evidence_refs": {key: value for key, value in (digest.get("evidence_paths") or {}).items() if value},
        "source_policy": {
            "allowed_source_uses": ["original_source_candidate", "similar_material", "domain_seed"],
            "requires_source_verification_before_formalization": True,
            "allow_question_bank_sources": False,
            "verified_original_source_required_for_original_source_claim": True,
        },
        "material_requirements": requirements,
        "cleaning_and_slicing_hypothesis": {
            "hypothesis_only": True,
            "source_body_required": True,
            "source_gold_alignment_required": True,
            "candidate_rules": [],
            "risk_notes": ["Source body and source/gold alignment are not available in this stage."],
        },
        "quality_gate_draft": {
            "requires_material_quality_regression": True,
            "requires_human_material_review": True,
            "draft_dimensions": [item["dimension"] for item in build_default_quality_dimensions(family=family, digest=digest)],
        },
        "evidence_gaps": gaps,
        "next_required_evidence": next_required_evidence(gaps),
        "limits": ["Draft only. No writeback."],
    }
    prompts = build_prompt_assets_draft(family)
    quality = {
        "draft_version": "v1",
        "asset_type": "material_quality_regression_draft",
        **DRAFT_FLAGS,
        "family_context": family,
        "evidence_map_ref": "material_evidence_map.json",
        "semantic_requirements_ref": "material_semantic_requirements_draft.json",
        "dimensions": build_default_quality_dimensions(family=family, digest=digest),
        "limits": ["Scores do not replace human review."],
    }
    bridge = {
        "mapping_draft_version": "v1",
        "asset_type": "material_bridge_mapping_draft",
        **DRAFT_FLAGS,
        "target_runtime": (alignment.get("confirmed_bridge_request_fields") or {}).get("target_runtime") or "unknown",
        "draft_mapping": build_bridge_mapping_from_family(family=family, confirmed_mapping=confirmed_mapping),
        "mapping_rationale": {"source": "system_alignment_findings"},
        "confirmed_repository_fields_used": list(confirmed_mapping.get("confirmed_fields") or []),
        "proposed_fields_not_confirmed": [],
        "missing_evidence": gaps,
        "requires_bridge_smoke": True,
        "system_alignment_findings_ref": "system_alignment_findings.json",
        "limits": ["Does not modify question_runtime.yaml or call /materials/v2/search."],
    }
    return {
        "material_semantic_requirements_draft": semantic,
        "material_card_draft": card,
        "material_line_prompt_assets_draft": prompts,
        "material_quality_regression_draft": quality,
        "material_bridge_mapping_draft": bridge,
    }


def run_llm_split_stages(
    *,
    digest: dict[str, Any],
    alignment: dict[str, Any],
    evidence_map: dict[str, Any],
    baseline_stages: dict[str, dict[str, Any]],
    model: str,
    base_url: str | None,
    api_key_env: str,
    max_output_tokens: int,
    timeout_seconds: int,
    client: ChatClient | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    active_client = client or OpenAICompatibleChatClient(
        base_url=base_url,
        api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
    )
    stage_inputs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for stage_key, baseline in baseline_stages.items():
        try:
            raw = active_client.complete(
                messages=build_stage_messages(
                    stage_key=stage_key,
                    digest=digest,
                    alignment=alignment,
                    evidence_map=evidence_map,
                    baseline=baseline,
                ),
                model=model,
                timeout_seconds=timeout_seconds,
                temperature=0.2,
                max_tokens=max_output_tokens,
            )
            parsed = _parse_json_object(raw)
            stage_inputs[stage_key] = parsed
        except Exception as exc:
            errors.append(f"{stage_key}: {exc}")
            return {}, errors
    return stage_inputs, errors


def build_llm_stage_builder(
    *,
    digest: dict[str, Any],
    alignment: dict[str, Any],
    evidence_map: dict[str, Any],
    baseline_stages: dict[str, dict[str, Any]],
    model: str,
    base_url: str | None,
    api_key_env: str,
    max_output_tokens: int,
    timeout_seconds: int,
    client: ChatClient | None = None,
):
    active_client = client or OpenAICompatibleChatClient(
        base_url=base_url,
        api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
    )

    def build(stage_key: str, completed: dict[str, dict[str, Any]]) -> dict[str, Any]:
        raw = active_client.complete(
            messages=build_stage_messages(
                stage_key=stage_key,
                digest=digest,
                alignment=alignment,
                evidence_map=evidence_map,
                baseline=baseline_stages[stage_key],
            ),
            model=model,
            timeout_seconds=timeout_seconds,
            temperature=0.2,
            max_tokens=max_output_tokens,
        )
        return _parse_json_object(raw)

    return build


def build_stage_messages(
    *,
    stage_key: str,
    digest: dict[str, Any],
    alignment: dict[str, Any],
    evidence_map: dict[str, Any],
    baseline: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是材料线分工位草案助手。你只能输出当前工位的 JSON。"
                "必须保持 status=draft_only, formalized=false, writeback_allowed=false, "
                "requires_human_review=true, requires_regression=true。"
                "不得确认原文、不得 verified=true、不得 crawl_allowed=true、不得写正式配置。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"STAGE_KEY: {stage_key}\n"
                "请基于 evidence_map 和 digest 改写/完善 BASELINE_JSON，但不要替换字段结构。\n"
                "必须保留 BASELINE_JSON 的顶层字段名。family_context 必须逐字复制。\n"
                "如果证据不足，写 evidence_gaps，不要编造。\n\n"
                f"DIGEST:\n{json.dumps(digest, ensure_ascii=False, indent=2)}\n\n"
                f"SYSTEM_ALIGNMENT_SUMMARY:\n{json.dumps(alignment.get('recommended_minimal_compatible_mapping') or {}, ensure_ascii=False, indent=2)}\n\n"
                f"EVIDENCE_MAP:\n{json.dumps(evidence_map, ensure_ascii=False, indent=2)}\n\n"
                f"BASELINE_JSON:\n{json.dumps(baseline, ensure_ascii=False, indent=2)}\n\n"
                "只返回 JSON object，不要 markdown。"
            ),
        },
    ]


def validate_split_stages(*, stages: dict[str, dict[str, Any]], digest: dict[str, Any], partial: bool = False) -> list[str]:
    errors: list[str] = []
    expected_keys = {
        "material_semantic_requirements_draft",
        "material_card_draft",
        "material_line_prompt_assets_draft",
        "material_quality_regression_draft",
        "material_bridge_mapping_draft",
    }
    if not partial:
        missing = expected_keys - set(stages.keys())
        for key in sorted(missing):
            errors.append(f"missing stage: {key}")
    family = digest.get("family_context") or {}
    for stage_key, payload in stages.items():
        for key, expected in DRAFT_FLAGS.items():
            if payload.get(key) != expected:
                errors.append(f"{stage_key}.{key} must be {expected!r}")
        for path, name, value in _walk_values(payload):
            if name in {"verified", "verified_original_source", "crawl_allowed", "material_library_write", "card_specs_write", "promotion_allowed", "writeback_allowed", "formalized"} and value is True:
                errors.append(f"{stage_key}{path}.{name} must not be true")
    card = stages.get("material_card_draft") or {}
    if "material_card_draft" in stages:
        if (card.get("family_binding") or {}) != family:
            errors.append("material_card_draft.family_binding must exactly match digest.family_context")
        if not (card.get("evidence_refs") or {}):
            errors.append("material_card_draft.evidence_refs must be non-empty")
        slicing = card.get("cleaning_and_slicing_hypothesis") or {}
        if slicing.get("source_body_required") is not True:
            errors.append("material_card_draft.cleaning_and_slicing_hypothesis.source_body_required must be true")
        if slicing.get("source_gold_alignment_required") is not True:
            errors.append("material_card_draft.cleaning_and_slicing_hypothesis.source_gold_alignment_required must be true")
    if "material_line_prompt_assets_draft" in stages:
        prompts = (stages.get("material_line_prompt_assets_draft") or {}).get("prompts") or {}
        for key in ("source_evidence_review", "source_gold_alignment", "material_transformation_hypothesis", "material_quality_review", "material_card_draft"):
            if key not in prompts:
                errors.append(f"material_line_prompt_assets_draft.prompts.{key} is required")
    if "material_quality_regression_draft" in stages:
        dimensions = (stages.get("material_quality_regression_draft") or {}).get("dimensions") or []
        if not dimensions:
            errors.append("material_quality_regression_draft.dimensions must be non-empty")
        for index, dimension in enumerate(dimensions):
            for key in ("dimension", "method", "confidence", "limitation"):
                if key not in dimension:
                    errors.append(f"material_quality_regression_draft.dimensions[{index}].{key} is required")
    if "material_bridge_mapping_draft" in stages:
        bridge = stages.get("material_bridge_mapping_draft") or {}
        if bridge.get("system_alignment_findings_ref") != "system_alignment_findings.json":
            errors.append("material_bridge_mapping_draft.system_alignment_findings_ref is required")
        if not bridge.get("confirmed_repository_fields_used"):
            errors.append("material_bridge_mapping_draft.confirmed_repository_fields_used must be non-empty")
    return errors


def collect_stage_errors(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for stage_key, stage in (state.get("stages") or {}).items():
        status = stage.get("status")
        if status in {"blocked", "provider_error", "validation_error"}:
            errors.append(f"{stage_key}: {stage.get('error_summary') or status}")
    return errors


def render_split_pipeline_report(
    *,
    mode: str,
    digest: dict[str, Any],
    alignment: dict[str, Any],
    evidence_map: dict[str, Any],
    stages: dict[str, dict[str, Any]],
    stage_errors: list[str],
) -> str:
    lines = [
        "# 材料协议分工位草案流水线报告",
        "",
        "## 基本信息",
        "",
        f"- mode: `{mode}`",
        f"- family_context: `{json.dumps(digest.get('family_context') or {}, ensure_ascii=False)}`",
        f"- evidence_gaps_count: `{len(digest.get('missing_evidence') or [])}`",
        f"- stage_count: `{len(stages)}`",
        f"- checked_files: `{len(alignment.get('checked_files') or [])}`",
        "",
        "## 工位产物",
        "",
        f"- material_evidence_map: `ready`",
        f"- material_semantic_requirements_draft: `{'ready' if 'material_semantic_requirements_draft' in stages else 'not_generated'}`",
        f"- material_card_draft: `{'ready' if 'material_card_draft' in stages else 'not_generated'}`",
        f"- material_line_prompt_assets_draft: `{'ready' if 'material_line_prompt_assets_draft' in stages else 'not_generated'}`",
        f"- material_quality_regression_draft: `{'ready' if 'material_quality_regression_draft' in stages else 'not_generated'}`",
        f"- material_bridge_mapping_draft: `{'ready' if 'material_bridge_mapping_draft' in stages else 'not_generated'}`",
        "",
        "## Evidence Gaps",
        "",
    ]
    gaps = digest.get("missing_evidence") or []
    lines.extend([f"- {gap}" for gap in gaps] or ["- None"])
    if stage_errors:
        lines.extend(["", "## Stage Errors", ""])
        lines.extend(f"- {error}" for error in stage_errors)
    lines.extend(
        [
            "",
            "## 边界声明",
            "",
            "- 本流水线只生成 draft-only 离线产物。",
            "- 没有正文抓取，没有 source verification，没有 passage_service ingest。",
            "- 没有写 material_card、card_specs、runtime mapping、prompt、validator、question_card。",
            "- 材料线 evidence 可以被人审引用，但不能自动污染题卡线。",
        ]
    )
    return "\n".join(lines) + "\n"


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:].strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("stage output must be a JSON object")
    return payload


def _walk_values(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, str(key), item
            yield from _walk_values(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_values(item, f"{path}[{index}]")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run split-stage material protocol draft pipeline.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--mode", choices=("dry-run", "mock", "llm"), default="dry-run")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--max-input-chars", type=int, default=DEFAULT_MAX_INPUT_CHARS)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-stage-retries", type=int, default=1)
    parser.add_argument("--gold-reconstruction-results")
    parser.add_argument("--truth-gold-regression-results")
    parser.add_argument("--truth-gold-split-manifest")
    parser.add_argument("--source-discovery-queries")
    parser.add_argument("--material-source-profile")
    parser.add_argument("--source-candidate-summary")
    parser.add_argument("--source-candidate-review")
    parser.add_argument("--source-seed-registry")
    parser.add_argument("--crawl-seed-manifest")
    parser.add_argument("--initial-plan-doc")
    args = parser.parse_args()
    artifacts = run_material_protocol_split_pipeline(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        mode=args.mode,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        max_input_chars=args.max_input_chars,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.timeout_seconds,
        resume=args.resume,
        max_stage_retries=args.max_stage_retries,
        gold_reconstruction_results=args.gold_reconstruction_results,
        truth_gold_regression_results=args.truth_gold_regression_results,
        truth_gold_split_manifest=args.truth_gold_split_manifest,
        source_discovery_queries=args.source_discovery_queries,
        material_source_profile=args.material_source_profile,
        source_candidate_summary=args.source_candidate_summary,
        source_candidate_review=args.source_candidate_review,
        source_seed_registry=args.source_seed_registry,
        crawl_seed_manifest=args.crawl_seed_manifest,
        initial_plan_doc=args.initial_plan_doc,
    )
    print(json.dumps({"artifacts": artifacts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

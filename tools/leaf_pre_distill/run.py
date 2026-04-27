from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fallback for lean environments
    yaml = None

from tools.leaf_pre_distill.behavior_marker import build_behavior_trace
from tools.leaf_pre_distill.axis_confirmation import build_axis_confirmation, load_axis_decisions
from tools.leaf_pre_distill.bootstrap_discovery import build_bootstrap_discovery
from tools.leaf_pre_distill.docx_reader import parse_docx_pack
from tools.leaf_pre_distill.field_candidate_builder import build_field_candidates, build_slot_projection_draft
from tools.leaf_pre_distill.formal_patch_draft import build_formal_patch_draft
from tools.leaf_pre_distill.formal_writeback_plan import build_formal_writeback_plan, render_formal_writeback_diff
from tools.leaf_pre_distill.gold_reconstruction import DEFAULT_MAX_OUTPUT_TOKENS, run_gold_reconstruction
from tools.leaf_pre_distill.llm_field_probe import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    ChatClient,
    build_disabled_probe,
    run_llm_field_probe,
)
from tools.leaf_pre_distill.llm_safe_digest import DEFAULT_MAX_DIGEST_CHARS, build_llm_safe_digest
from tools.leaf_pre_distill.material_protocol_draft import run_material_protocol_draft
from tools.leaf_pre_distill.material_evidence_alignment_regression import run_material_evidence_alignment_regression
from tools.leaf_pre_distill.report_renderer import render_markdown_report
from tools.leaf_pre_distill.source_candidate_review import run_source_candidate_review
from tools.leaf_pre_distill.source_candidate_search import run_source_candidate_search_from_queries
from tools.leaf_pre_distill.source_discovery_preparation import run_source_discovery_preparation
from tools.leaf_pre_distill.truth_gold_regression import load_generated_items, load_gold_reconstructions, run_truth_gold_regression


def run_leaf_pre_distill(
    *,
    mother_family_id: str,
    leaf_label: str,
    source_files: list[str],
    output_dir: str | Path,
    child_family_id: str | None = None,
    clean_leaf_boundary: bool = True,
    operator: str | None = None,
    enable_llm_probe: bool = False,
    llm_model: str = DEFAULT_MODEL,
    llm_base_url: str | None = None,
    llm_api_key_env: str = DEFAULT_API_KEY_ENV,
    llm_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    llm_max_digest_chars: int = DEFAULT_MAX_DIGEST_CHARS,
    llm_dry_run: bool = False,
    llm_client: ChatClient | None = None,
    enable_bootstrap_discovery: bool = False,
    bootstrap_proto_family_label: str | None = None,
    bootstrap_known_family_matched: bool | None = None,
    enable_axis_confirmation: bool = False,
    axis_confirmation_decisions: str | Path | None = None,
    enable_formal_patch_draft: bool = False,
    formal_patch_targets: list[str] | None = None,
    enable_formal_writeback_plan: bool = False,
    writeback_plan_reviewer: str | None = None,
    enable_truth_gold_regression: bool = False,
    truth_gold_generated_items: str | Path | None = None,
    truth_gold_split_seed: int = 7,
    truth_gold_train_ratio: float = 0.4,
    truth_gold_dev_ratio: float = 0.2,
    truth_gold_eval_ratio: float = 0.2,
    truth_gold_insurance_ratio: float = 0.2,
    truth_gold_output_dir: str | Path | None = None,
    enable_gold_reconstruction: bool = False,
    gold_reconstruction_mode: str = "dry-run",
    gold_reconstruction_model: str = DEFAULT_MODEL,
    gold_reconstruction_base_url: str | None = None,
    gold_reconstruction_api_key_env: str = DEFAULT_API_KEY_ENV,
    gold_reconstruction_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    gold_reconstruction_max_input_chars: int = 6000,
    gold_reconstruction_max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    gold_reconstruction_output_dir: str | Path | None = None,
    gold_reconstruction_client: ChatClient | None = None,
    enable_source_discovery_prep: bool = False,
    source_discovery_output_dir: str | Path | None = None,
    source_discovery_max_queries_per_sample: int = 6,
    source_discovery_min_query_chars: int = 8,
    source_discovery_use_raw_fallback: bool = False,
    enable_source_candidate_search: bool = False,
    source_candidate_queries_path: str | Path | None = None,
    source_candidate_output_dir: str | Path | None = None,
    source_candidate_max_samples: int = 5,
    source_candidate_max_queries_per_sample: int = 3,
    source_candidate_max_results_per_query: int = 5,
    source_candidate_allowed_risk: str = "low",
    source_candidate_dry_run: bool = True,
    source_candidate_run_search: bool = False,
    source_candidate_provider: str = "manual",
    source_candidate_api_key_env: str = "SOURCE_SEARCH_API_KEY",
    source_candidate_timeout_seconds: int = 20,
    enable_source_candidate_review: bool = False,
    source_candidate_results_path: str | Path | None = None,
    source_candidate_review_decisions: str | Path | None = None,
    source_candidate_review_output_dir: str | Path | None = None,
    source_candidate_allow_manual_url_additions: bool = False,
    source_candidate_allow_risky_seeds: bool = False,
    enable_material_evidence_alignment_regression: bool = False,
    material_evidence_output_dir: str | Path | None = None,
    material_evidence_source_seed_registry: str | Path | None = None,
    material_evidence_crawl_seed_manifest: str | Path | None = None,
    material_evidence_source_text_approval: str | Path | None = None,
    material_evidence_manual_source_texts: str | Path | None = None,
    material_evidence_gold_reconstruction_results: str | Path | None = None,
    material_evidence_material_card_draft: str | Path | None = None,
    material_evidence_quality_regression_draft: str | Path | None = None,
    material_evidence_agent_feedback: str | Path | None = None,
    material_evidence_source_text_mode: str = "mock",
    material_evidence_alignment_mode: str = "mock",
    material_evidence_alignment_model: str = DEFAULT_MODEL,
    material_evidence_alignment_base_url: str | None = None,
    material_evidence_alignment_api_key_env: str = DEFAULT_API_KEY_ENV,
    material_evidence_alignment_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    material_evidence_alignment_max_output_tokens: int = 900,
    enable_material_protocol_draft: bool = False,
    material_protocol_draft_mode: str = "dry-run",
    material_protocol_draft_model: str = DEFAULT_MODEL,
    material_protocol_draft_base_url: str | None = None,
    material_protocol_draft_api_key_env: str = DEFAULT_API_KEY_ENV,
    material_protocol_draft_max_input_chars: int = 8000,
    material_protocol_draft_max_output_tokens: int = 2500,
    material_protocol_draft_output_dir: str | Path | None = None,
    material_protocol_draft_truth_gold_split_manifest: str | Path | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    job_id = _job_id(mother_family_id=mother_family_id, leaf_label=leaf_label, source_files=source_files)
    manifest = {
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mother_family_id": mother_family_id,
        "child_family_id": child_family_id,
        "leaf_label": leaf_label,
        "source_files": source_files,
        "clean_leaf_boundary": clean_leaf_boundary,
        "operator": operator,
        "artifact_version": "leaf_pre_distill.v1",
    }

    samples: list[dict[str, Any]] = []
    for source_file in source_files:
        samples.extend(parse_docx_pack(source_file, mother_family_id=mother_family_id, leaf_label=leaf_label))
    traces = [build_behavior_trace(sample, mother_family_id=mother_family_id) for sample in samples]
    candidate_report = build_field_candidates(
        mother_family_id=mother_family_id,
        leaf_label=leaf_label,
        samples=samples,
        traces=traces,
    )
    slot_projection = build_slot_projection_draft(candidate_report)
    bootstrap_discovery: dict[str, Any] | None = None
    axis_confirmation: dict[str, Any] | None = None
    formal_patch_draft: dict[str, Any] | None = None
    formal_writeback_plan: dict[str, Any] | None = None
    formal_writeback_diff: str | None = None
    truth_gold_split_manifest: dict[str, Any] | None = None
    truth_gold_regression_results: dict[str, Any] | None = None
    truth_gold_regression_report: str | None = None
    gold_reconstruction_summary: dict[str, Any] | None = None
    source_discovery_artifacts: dict[str, str] | None = None
    source_discovery_profile: dict[str, Any] | None = None
    source_candidate_artifacts: dict[str, str] | None = None
    source_candidate_summary: dict[str, Any] | None = None
    source_candidate_review_artifacts: dict[str, str] | None = None
    source_candidate_review_summary: dict[str, Any] | None = None
    material_evidence_artifacts: dict[str, str] | None = None
    source_text_evidence_summary: dict[str, Any] | None = None
    source_gold_alignment_summary: dict[str, Any] | None = None
    material_quality_regression_summary: dict[str, Any] | None = None
    material_protocol_draft_artifacts: dict[str, str] | None = None
    material_protocol_draft_summary: dict[str, Any] | None = None
    llm_digest: dict[str, Any] | None = None
    llm_probe: dict[str, Any] | None = None
    if enable_llm_probe or llm_dry_run:
        llm_digest = build_llm_safe_digest(
            manifest=manifest,
            samples=samples,
            traces=traces,
            candidate_report=candidate_report,
            slot_projection=slot_projection,
            max_digest_chars=llm_max_digest_chars,
        )
        if llm_dry_run:
            llm_probe = build_disabled_probe(
                digest=llm_digest,
                model=llm_model,
                reason="LLM field probe dry-run: digest generated without model request.",
                dry_run=True,
            )
        elif enable_llm_probe:
            llm_probe = run_llm_field_probe(
                digest=llm_digest,
                model=llm_model,
                base_url=llm_base_url,
                api_key_env=llm_api_key_env,
                timeout_seconds=llm_timeout_seconds,
                client=llm_client,
            )
    if enable_bootstrap_discovery:
        bootstrap_discovery = build_bootstrap_discovery(
            manifest=manifest,
            samples=samples,
            traces=traces,
            candidate_report=candidate_report,
            llm_safe_digest=llm_digest,
            proto_family_label=bootstrap_proto_family_label,
            known_family_matched=bootstrap_known_family_matched,
        )
    if enable_axis_confirmation:
        if bootstrap_discovery is None:
            raise ValueError("axis confirmation requires bootstrap discovery to be enabled.")
        if axis_confirmation_decisions is None:
            raise ValueError("axis confirmation requires an axis decision JSON path.")
        axis_confirmation = build_axis_confirmation(
            manifest=manifest,
            bootstrap_discovery=bootstrap_discovery,
            decision_payload=load_axis_decisions(axis_confirmation_decisions),
        )
    if enable_formal_patch_draft:
        if axis_confirmation is None:
            raise ValueError("formal patch draft requires axis confirmation to be enabled.")
        formal_patch_draft = build_formal_patch_draft(
            manifest=manifest,
            axis_confirmation=axis_confirmation,
            target_filter=formal_patch_targets,
        )
    if enable_formal_writeback_plan:
        if formal_patch_draft is None:
            raise ValueError("formal writeback plan requires formal patch draft to be enabled.")
        formal_writeback_plan = build_formal_writeback_plan(
            formal_patch_draft=formal_patch_draft,
            reviewer=writeback_plan_reviewer or operator,
        )
        formal_writeback_diff = render_formal_writeback_diff(formal_writeback_plan)
    gold_output_path = Path(gold_reconstruction_output_dir) if gold_reconstruction_output_dir is not None else output_path
    if enable_gold_reconstruction:
        gold_reconstruction_summary = run_gold_reconstruction(
            manifest=manifest,
            samples=samples,
            output_dir=gold_output_path,
            mode=gold_reconstruction_mode,
            model=gold_reconstruction_model,
            base_url=gold_reconstruction_base_url,
            api_key_env=gold_reconstruction_api_key_env,
            timeout_seconds=gold_reconstruction_timeout_seconds,
            max_input_chars=gold_reconstruction_max_input_chars,
            max_output_tokens=gold_reconstruction_max_output_tokens,
            client=gold_reconstruction_client,
        )
    if enable_source_discovery_prep:
        source_output_path = Path(source_discovery_output_dir) if source_discovery_output_dir is not None else output_path
        reconstruction_path = None
        if enable_gold_reconstruction and gold_reconstruction_summary:
            reconstruction_path = (gold_reconstruction_summary.get("artifacts") or {}).get("gold_reconstruction_results")
        elif (output_path / "gold_reconstruction_results.jsonl").exists():
            reconstruction_path = output_path / "gold_reconstruction_results.jsonl"
        elif gold_output_path != output_path and (gold_output_path / "gold_reconstruction_results.jsonl").exists():
            reconstruction_path = gold_output_path / "gold_reconstruction_results.jsonl"
        source_discovery_artifacts = run_source_discovery_preparation(
            manifest=manifest,
            samples=samples,
            source_artifact_dir=output_path,
            output_dir=source_output_path,
            gold_reconstructions=load_gold_reconstructions(reconstruction_path),
            max_queries_per_sample=source_discovery_max_queries_per_sample,
            min_query_chars=source_discovery_min_query_chars,
            use_raw_fallback=source_discovery_use_raw_fallback,
        )
        profile_path = source_discovery_artifacts.get("material_source_profile")
        if profile_path:
            source_discovery_profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    if enable_source_candidate_search:
        candidate_output_path = Path(source_candidate_output_dir) if source_candidate_output_dir is not None else output_path
        candidate_queries_path = None
        if source_candidate_queries_path is not None:
            candidate_queries_path = Path(source_candidate_queries_path)
        elif source_discovery_artifacts and source_discovery_artifacts.get("source_discovery_queries"):
            candidate_queries_path = Path(source_discovery_artifacts["source_discovery_queries"])
        elif (output_path / "source_discovery_queries.jsonl").exists():
            candidate_queries_path = output_path / "source_discovery_queries.jsonl"
        if candidate_queries_path is None:
            raise ValueError("source candidate search requires source_discovery_queries.jsonl or --source-candidate-queries.")
        source_candidate_artifacts = run_source_candidate_search_from_queries(
            source_discovery_queries_path=candidate_queries_path,
            output_dir=candidate_output_path,
            max_samples=source_candidate_max_samples,
            max_queries_per_sample=source_candidate_max_queries_per_sample,
            max_results_per_query=source_candidate_max_results_per_query,
            allowed_risk=source_candidate_allowed_risk,
            dry_run=source_candidate_dry_run,
            run_search=source_candidate_run_search,
            search_provider=source_candidate_provider,
            search_api_key_env=source_candidate_api_key_env,
            search_timeout_seconds=source_candidate_timeout_seconds,
        )
        summary_path = source_candidate_artifacts.get("source_candidate_summary")
        if summary_path:
            source_candidate_summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    if enable_source_candidate_review:
        review_output_path = Path(source_candidate_review_output_dir) if source_candidate_review_output_dir is not None else output_path
        candidate_results_path = None
        if source_candidate_results_path is not None:
            candidate_results_path = Path(source_candidate_results_path)
        elif source_candidate_artifacts and source_candidate_artifacts.get("source_candidate_results"):
            candidate_results_path = Path(source_candidate_artifacts["source_candidate_results"])
        elif (output_path / "source_candidate_results.jsonl").exists():
            candidate_results_path = output_path / "source_candidate_results.jsonl"
        if candidate_results_path is None:
            raise ValueError("source candidate review requires source_candidate_results.jsonl or --source-candidate-results.")
        if source_candidate_review_decisions is None:
            raise ValueError("source candidate review requires --source-candidate-review-decisions.")
        source_candidate_review_artifacts = run_source_candidate_review(
            source_candidate_results_path=candidate_results_path,
            review_decisions_path=source_candidate_review_decisions,
            output_dir=review_output_path,
            allow_manual_url_additions=source_candidate_allow_manual_url_additions,
            allow_risky_seeds=source_candidate_allow_risky_seeds,
        )
        review_path = source_candidate_review_artifacts.get("source_candidate_review")
        if review_path:
            source_candidate_review_summary = json.loads(Path(review_path).read_text(encoding="utf-8"))
    if enable_material_evidence_alignment_regression:
        material_evidence_path = Path(material_evidence_output_dir) if material_evidence_output_dir is not None else output_path
        seed_registry_path = None
        if material_evidence_source_seed_registry is not None:
            seed_registry_path = Path(material_evidence_source_seed_registry)
        elif source_candidate_review_artifacts and source_candidate_review_artifacts.get("source_seed_registry"):
            seed_registry_path = Path(source_candidate_review_artifacts["source_seed_registry"])
        elif (output_path / "source_seed_registry.jsonl").exists():
            seed_registry_path = output_path / "source_seed_registry.jsonl"
        if seed_registry_path is None:
            raise ValueError("material evidence alignment regression requires source_seed_registry.jsonl or --material-evidence-source-seed-registry.")
        approval_path = Path(material_evidence_source_text_approval) if material_evidence_source_text_approval is not None else None
        if approval_path is None:
            raise ValueError("material evidence alignment regression requires --material-evidence-source-text-approval.")
        crawl_manifest_path = None
        if material_evidence_crawl_seed_manifest is not None:
            crawl_manifest_path = Path(material_evidence_crawl_seed_manifest)
        elif source_candidate_review_artifacts and source_candidate_review_artifacts.get("crawl_seed_manifest"):
            crawl_manifest_path = Path(source_candidate_review_artifacts["crawl_seed_manifest"])
        elif (output_path / "crawl_seed_manifest.json").exists():
            crawl_manifest_path = output_path / "crawl_seed_manifest.json"
        gold_results_path = None
        if material_evidence_gold_reconstruction_results is not None:
            gold_results_path = Path(material_evidence_gold_reconstruction_results)
        elif gold_reconstruction_summary and (gold_reconstruction_summary.get("artifacts") or {}).get("gold_reconstruction_results"):
            gold_results_path = Path((gold_reconstruction_summary.get("artifacts") or {})["gold_reconstruction_results"])
        elif (output_path / "gold_reconstruction_results.jsonl").exists():
            gold_results_path = output_path / "gold_reconstruction_results.jsonl"
        material_evidence_artifacts = run_material_evidence_alignment_regression(
            output_dir=material_evidence_path,
            source_seed_registry_path=seed_registry_path,
            crawl_seed_manifest_path=crawl_manifest_path,
            source_text_evidence_approval_path=approval_path,
            source_text_manual_results_path=material_evidence_manual_source_texts,
            gold_reconstruction_results_path=gold_results_path,
            material_card_draft_path=material_evidence_material_card_draft,
            material_quality_regression_draft_path=material_evidence_quality_regression_draft,
            agent_review_feedback_normalized_path=material_evidence_agent_feedback,
            source_text_mode=material_evidence_source_text_mode,
            alignment_mode=material_evidence_alignment_mode,
            alignment_model=material_evidence_alignment_model,
            alignment_base_url=material_evidence_alignment_base_url,
            alignment_api_key_env=material_evidence_alignment_api_key_env,
            alignment_timeout_seconds=material_evidence_alignment_timeout_seconds,
            alignment_max_output_tokens=material_evidence_alignment_max_output_tokens,
        )
        source_text_path = material_evidence_artifacts.get("source_text_evidence_manifest")
        if source_text_path:
            source_text_evidence_summary = json.loads(Path(source_text_path).read_text(encoding="utf-8"))
        alignment_path = material_evidence_artifacts.get("source_gold_alignment_summary")
        if alignment_path:
            source_gold_alignment_summary = json.loads(Path(alignment_path).read_text(encoding="utf-8"))
        quality_path = material_evidence_artifacts.get("material_quality_regression_results")
        if quality_path:
            material_quality_regression_summary = json.loads(Path(quality_path).read_text(encoding="utf-8"))
    if enable_material_protocol_draft:
        material_output_path = Path(material_protocol_draft_output_dir) if material_protocol_draft_output_dir is not None else output_path
        material_protocol_draft_artifacts = run_material_protocol_draft(
            artifact_dir=output_path,
            output_dir=material_output_path,
            mode=material_protocol_draft_mode,
            model=material_protocol_draft_model,
            base_url=material_protocol_draft_base_url,
            api_key_env=material_protocol_draft_api_key_env,
            max_input_chars=material_protocol_draft_max_input_chars,
            max_output_tokens=material_protocol_draft_max_output_tokens,
            gold_reconstruction_results=(gold_reconstruction_summary.get("artifacts") or {}).get("gold_reconstruction_results") if gold_reconstruction_summary else None,
            truth_gold_regression_results=str((Path(truth_gold_output_dir) if truth_gold_output_dir is not None else output_path) / "truth_gold_regression_results.json") if truth_gold_regression_results is not None else None,
            truth_gold_split_manifest=material_protocol_draft_truth_gold_split_manifest
            or (str((Path(truth_gold_output_dir) if truth_gold_output_dir is not None else output_path) / "truth_gold_split_manifest.json") if truth_gold_split_manifest is not None else None),
            source_discovery_queries=source_discovery_artifacts.get("source_discovery_queries") if source_discovery_artifacts else None,
            material_source_profile=source_discovery_artifacts.get("material_source_profile") if source_discovery_artifacts else None,
            source_candidate_summary=source_candidate_artifacts.get("source_candidate_summary") if source_candidate_artifacts else None,
            source_candidate_review=source_candidate_review_artifacts.get("source_candidate_review") if source_candidate_review_artifacts else None,
            source_seed_registry=source_candidate_review_artifacts.get("source_seed_registry") if source_candidate_review_artifacts else None,
            crawl_seed_manifest=source_candidate_review_artifacts.get("crawl_seed_manifest") if source_candidate_review_artifacts else None,
        )
        summary_path = material_protocol_draft_artifacts.get("material_protocol_draft_input_digest")
        if summary_path:
            material_protocol_draft_summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    if enable_truth_gold_regression:
        reconstruction_path = None
        if enable_gold_reconstruction and gold_reconstruction_summary:
            reconstruction_path = (gold_reconstruction_summary.get("artifacts") or {}).get("gold_reconstruction_results")
        elif (output_path / "gold_reconstruction_results.jsonl").exists():
            reconstruction_path = output_path / "gold_reconstruction_results.jsonl"
        (
            truth_gold_split_manifest,
            truth_gold_regression_results,
            truth_gold_regression_report,
        ) = run_truth_gold_regression(
            manifest=manifest,
            samples=samples,
            source_artifact_dir=output_path,
            generated_items=load_generated_items(truth_gold_generated_items),
            gold_reconstructions=load_gold_reconstructions(reconstruction_path),
            split_seed=truth_gold_split_seed,
            train_ratio=truth_gold_train_ratio,
            dev_ratio=truth_gold_dev_ratio,
            eval_ratio=truth_gold_eval_ratio,
            insurance_ratio=truth_gold_insurance_ratio,
        )
    report = render_markdown_report(
        manifest=manifest,
        candidate_report=candidate_report,
        slot_projection=slot_projection,
        llm_probe=llm_probe,
        bootstrap_discovery=bootstrap_discovery,
        axis_confirmation=axis_confirmation,
        formal_patch_draft=formal_patch_draft,
        formal_writeback_plan=formal_writeback_plan,
        gold_reconstruction=gold_reconstruction_summary,
        truth_gold_regression=truth_gold_regression_results,
        source_discovery_preparation=source_discovery_profile,
        source_candidate_search=source_candidate_summary,
        source_candidate_review=source_candidate_review_summary,
        source_text_evidence=source_text_evidence_summary,
        source_gold_alignment=source_gold_alignment_summary,
        material_quality_regression=material_quality_regression_summary,
        material_protocol_draft=material_protocol_draft_summary,
    )

    _write_json(output_path / "manifest.json", manifest)
    _write_jsonl(output_path / "samples.jsonl", samples)
    _write_jsonl(output_path / "behavior_traces.jsonl", traces)
    _write_json(output_path / "field_candidates.json", candidate_report)
    _write_yaml(output_path / "slot_projection_draft.yaml", slot_projection)
    if llm_digest is not None:
        _write_json(output_path / "llm_safe_digest.json", llm_digest)
    if llm_probe is not None:
        _write_json(output_path / "llm_field_probe.json", llm_probe)
    if bootstrap_discovery is not None:
        _write_json(output_path / "bootstrap_discovery.json", bootstrap_discovery)
    if axis_confirmation is not None:
        _write_json(output_path / "axis_confirmation.json", axis_confirmation)
    if formal_patch_draft is not None:
        _write_json(output_path / "formal_patch_draft.json", formal_patch_draft)
    if formal_writeback_plan is not None:
        _write_json(output_path / "formal_writeback_plan.json", formal_writeback_plan)
    if formal_writeback_diff is not None:
        (output_path / "formal_writeback_diff.md").write_text(formal_writeback_diff, encoding="utf-8")
    truth_output_path = Path(truth_gold_output_dir) if truth_gold_output_dir is not None else output_path
    if enable_truth_gold_regression:
        truth_output_path.mkdir(parents=True, exist_ok=True)
    if truth_gold_split_manifest is not None:
        _write_json(truth_output_path / "truth_gold_split_manifest.json", truth_gold_split_manifest)
    if truth_gold_regression_results is not None:
        _write_json(truth_output_path / "truth_gold_regression_results.json", truth_gold_regression_results)
    if truth_gold_regression_report is not None:
        (truth_output_path / "truth_gold_regression_report.md").write_text(truth_gold_regression_report, encoding="utf-8")
    (output_path / "report.md").write_text(report, encoding="utf-8")
    artifacts = {
        "manifest": str(output_path / "manifest.json"),
        "samples": str(output_path / "samples.jsonl"),
        "behavior_traces": str(output_path / "behavior_traces.jsonl"),
        "field_candidates": str(output_path / "field_candidates.json"),
        "slot_projection_draft": str(output_path / "slot_projection_draft.yaml"),
        "report": str(output_path / "report.md"),
    }
    if llm_digest is not None:
        artifacts["llm_safe_digest"] = str(output_path / "llm_safe_digest.json")
    if llm_probe is not None:
        artifacts["llm_field_probe"] = str(output_path / "llm_field_probe.json")
    if bootstrap_discovery is not None:
        artifacts["bootstrap_discovery"] = str(output_path / "bootstrap_discovery.json")
    if axis_confirmation is not None:
        artifacts["axis_confirmation"] = str(output_path / "axis_confirmation.json")
    if formal_patch_draft is not None:
        artifacts["formal_patch_draft"] = str(output_path / "formal_patch_draft.json")
    if formal_writeback_plan is not None:
        artifacts["formal_writeback_plan"] = str(output_path / "formal_writeback_plan.json")
    if formal_writeback_diff is not None:
        artifacts["formal_writeback_diff"] = str(output_path / "formal_writeback_diff.md")
    if truth_gold_split_manifest is not None:
        artifacts["truth_gold_split_manifest"] = str(truth_output_path / "truth_gold_split_manifest.json")
    if truth_gold_regression_results is not None:
        artifacts["truth_gold_regression_results"] = str(truth_output_path / "truth_gold_regression_results.json")
    if truth_gold_regression_report is not None:
        artifacts["truth_gold_regression_report"] = str(truth_output_path / "truth_gold_regression_report.md")
    if gold_reconstruction_summary is not None:
        artifacts.update(gold_reconstruction_summary.get("artifacts") or {})
    if source_discovery_artifacts is not None:
        artifacts.update(source_discovery_artifacts)
    if source_candidate_artifacts is not None:
        artifacts.update(source_candidate_artifacts)
    if source_candidate_review_artifacts is not None:
        artifacts.update(source_candidate_review_artifacts)
    if material_evidence_artifacts is not None:
        artifacts.update(material_evidence_artifacts)
    if material_protocol_draft_artifacts is not None:
        artifacts.update(material_protocol_draft_artifacts)
    return {
        "job_id": job_id,
        "output_dir": str(output_path),
        "sample_count": len(samples),
        "field_candidate_count": len(candidate_report.get("field_candidates") or []),
        "high_confidence_count": candidate_report.get("summary", {}).get("high_confidence_count", 0),
        "schema_gap_count": len(candidate_report.get("schema_gaps") or []),
        "llm_probe_enabled": bool(enable_llm_probe),
        "llm_probe_dry_run": bool(llm_dry_run),
        "bootstrap_discovery_enabled": bool(enable_bootstrap_discovery),
        "axis_confirmation_enabled": bool(enable_axis_confirmation),
        "formal_patch_draft_enabled": bool(enable_formal_patch_draft),
        "formal_writeback_plan_enabled": bool(enable_formal_writeback_plan),
        "truth_gold_regression_enabled": bool(enable_truth_gold_regression),
        "gold_reconstruction_enabled": bool(enable_gold_reconstruction),
        "gold_reconstruction_mode": gold_reconstruction_mode if enable_gold_reconstruction else None,
        "source_discovery_prep_enabled": bool(enable_source_discovery_prep),
        "source_candidate_search_enabled": bool(enable_source_candidate_search),
        "source_candidate_review_enabled": bool(enable_source_candidate_review),
        "material_evidence_alignment_regression_enabled": bool(enable_material_evidence_alignment_regression),
        "material_protocol_draft_enabled": bool(enable_material_protocol_draft),
        "material_protocol_draft_mode": material_protocol_draft_mode if enable_material_protocol_draft else None,
        "artifacts": artifacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run leaf pre-distillation over local question packs.")
    parser.add_argument("--mother-family-id", required=True)
    parser.add_argument("--leaf-label", required=True)
    parser.add_argument("--source-file", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--child-family-id")
    parser.add_argument("--operator")
    parser.add_argument("--dirty-leaf-boundary", action="store_true")
    parser.add_argument("--enable-llm-probe", action="store_true")
    parser.add_argument("--llm-model", default=DEFAULT_MODEL)
    parser.add_argument("--llm-base-url")
    parser.add_argument("--llm-api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--llm-timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--llm-max-digest-chars", type=int, default=DEFAULT_MAX_DIGEST_CHARS)
    parser.add_argument("--llm-dry-run", action="store_true")
    parser.add_argument("--enable-bootstrap-discovery", action="store_true")
    parser.add_argument("--bootstrap-proto-family-label")
    parser.add_argument("--bootstrap-known-family-matched", choices=("true", "false", "auto"), default="auto")
    parser.add_argument("--enable-axis-confirmation", action="store_true")
    parser.add_argument("--axis-confirmation-decisions")
    parser.add_argument("--enable-formal-patch-draft", action="store_true")
    parser.add_argument("--formal-patch-targets")
    parser.add_argument("--enable-formal-writeback-plan", action="store_true")
    parser.add_argument("--writeback-plan-reviewer")
    parser.add_argument("--enable-truth-gold-regression", action="store_true")
    parser.add_argument("--truth-gold-generated-items")
    parser.add_argument("--truth-gold-split-seed", type=int, default=7)
    parser.add_argument("--truth-gold-train-ratio", type=float, default=0.4)
    parser.add_argument("--truth-gold-dev-ratio", type=float, default=0.2)
    parser.add_argument("--truth-gold-eval-ratio", type=float, default=0.2)
    parser.add_argument("--truth-gold-insurance-ratio", type=float, default=0.2)
    parser.add_argument("--truth-gold-output-dir")
    parser.add_argument("--enable-gold-reconstruction", action="store_true")
    parser.add_argument("--gold-reconstruction-mode", choices=("dry-run", "mock", "llm"), default="dry-run")
    parser.add_argument("--gold-reconstruction-model", default=DEFAULT_MODEL)
    parser.add_argument("--gold-reconstruction-base-url")
    parser.add_argument("--gold-reconstruction-api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--gold-reconstruction-timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--gold-reconstruction-max-input-chars", type=int, default=6000)
    parser.add_argument("--gold-reconstruction-max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--gold-reconstruction-output-dir")
    parser.add_argument("--enable-source-discovery-prep", action="store_true")
    parser.add_argument("--source-discovery-output-dir")
    parser.add_argument("--source-discovery-max-queries-per-sample", type=int, default=6)
    parser.add_argument("--source-discovery-min-query-chars", type=int, default=8)
    parser.add_argument("--source-discovery-use-raw-fallback", action="store_true")
    parser.add_argument("--enable-source-candidate-search", action="store_true")
    parser.add_argument("--source-candidate-queries")
    parser.add_argument("--source-candidate-output-dir")
    parser.add_argument("--source-candidate-max-samples", type=int, default=5)
    parser.add_argument("--source-candidate-max-queries-per-sample", type=int, default=3)
    parser.add_argument("--source-candidate-max-results-per-query", type=int, default=5)
    parser.add_argument("--source-candidate-allowed-risk", default="low")
    parser.add_argument("--source-candidate-dry-run", action="store_true")
    parser.add_argument("--source-candidate-run-search", action="store_true")
    parser.add_argument("--source-candidate-provider", choices=("mock", "manual", "web"), default="manual")
    parser.add_argument("--source-candidate-api-key-env", default="SOURCE_SEARCH_API_KEY")
    parser.add_argument("--source-candidate-timeout-seconds", type=int, default=20)
    parser.add_argument("--enable-source-candidate-review", action="store_true")
    parser.add_argument("--source-candidate-results")
    parser.add_argument("--source-candidate-review-decisions")
    parser.add_argument("--source-candidate-review-output-dir")
    parser.add_argument("--source-candidate-allow-manual-url-additions", action="store_true")
    parser.add_argument("--source-candidate-allow-risky-seeds", action="store_true")
    parser.add_argument("--enable-material-evidence-alignment-regression", action="store_true")
    parser.add_argument("--material-evidence-output-dir")
    parser.add_argument("--material-evidence-source-seed-registry")
    parser.add_argument("--material-evidence-crawl-seed-manifest")
    parser.add_argument("--material-evidence-source-text-approval")
    parser.add_argument("--material-evidence-manual-source-texts")
    parser.add_argument("--material-evidence-gold-reconstruction-results")
    parser.add_argument("--material-evidence-material-card-draft")
    parser.add_argument("--material-evidence-quality-regression-draft")
    parser.add_argument("--material-evidence-agent-feedback")
    parser.add_argument("--material-evidence-source-text-mode", choices=("manual", "mock"), default="mock")
    parser.add_argument("--material-evidence-alignment-mode", choices=("dry-run", "mock", "llm"), default="mock")
    parser.add_argument("--material-evidence-alignment-model", default=DEFAULT_MODEL)
    parser.add_argument("--material-evidence-alignment-base-url")
    parser.add_argument("--material-evidence-alignment-api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--material-evidence-alignment-timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--material-evidence-alignment-max-output-tokens", type=int, default=900)
    parser.add_argument("--enable-material-protocol-draft", action="store_true")
    parser.add_argument("--material-protocol-draft-mode", choices=("dry-run", "mock", "llm"), default="dry-run")
    parser.add_argument("--material-protocol-draft-model", default=DEFAULT_MODEL)
    parser.add_argument("--material-protocol-draft-base-url")
    parser.add_argument("--material-protocol-draft-api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--material-protocol-draft-max-input-chars", type=int, default=8000)
    parser.add_argument("--material-protocol-draft-max-output-tokens", type=int, default=2500)
    parser.add_argument("--material-protocol-draft-output-dir")
    parser.add_argument("--material-protocol-draft-truth-gold-split-manifest")
    args = parser.parse_args()
    summary = run_leaf_pre_distill(
        mother_family_id=args.mother_family_id,
        leaf_label=args.leaf_label,
        source_files=args.source_file,
        output_dir=args.output_dir,
        child_family_id=args.child_family_id,
        clean_leaf_boundary=not args.dirty_leaf_boundary,
        operator=args.operator,
        enable_llm_probe=args.enable_llm_probe,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        llm_api_key_env=args.llm_api_key_env,
        llm_timeout_seconds=args.llm_timeout_seconds,
        llm_max_digest_chars=args.llm_max_digest_chars,
        llm_dry_run=args.llm_dry_run,
        enable_bootstrap_discovery=args.enable_bootstrap_discovery,
        bootstrap_proto_family_label=args.bootstrap_proto_family_label,
        bootstrap_known_family_matched=_parse_optional_bool(args.bootstrap_known_family_matched),
        enable_axis_confirmation=args.enable_axis_confirmation,
        axis_confirmation_decisions=args.axis_confirmation_decisions,
        enable_formal_patch_draft=args.enable_formal_patch_draft,
        formal_patch_targets=_parse_csv(args.formal_patch_targets),
        enable_formal_writeback_plan=args.enable_formal_writeback_plan,
        writeback_plan_reviewer=args.writeback_plan_reviewer,
        enable_truth_gold_regression=args.enable_truth_gold_regression,
        truth_gold_generated_items=args.truth_gold_generated_items,
        truth_gold_split_seed=args.truth_gold_split_seed,
        truth_gold_train_ratio=args.truth_gold_train_ratio,
        truth_gold_dev_ratio=args.truth_gold_dev_ratio,
        truth_gold_eval_ratio=args.truth_gold_eval_ratio,
        truth_gold_insurance_ratio=args.truth_gold_insurance_ratio,
        truth_gold_output_dir=args.truth_gold_output_dir,
        enable_gold_reconstruction=args.enable_gold_reconstruction,
        gold_reconstruction_mode=args.gold_reconstruction_mode,
        gold_reconstruction_model=args.gold_reconstruction_model,
        gold_reconstruction_base_url=args.gold_reconstruction_base_url,
        gold_reconstruction_api_key_env=args.gold_reconstruction_api_key_env,
        gold_reconstruction_timeout_seconds=args.gold_reconstruction_timeout_seconds,
        gold_reconstruction_max_input_chars=args.gold_reconstruction_max_input_chars,
        gold_reconstruction_max_output_tokens=args.gold_reconstruction_max_output_tokens,
        gold_reconstruction_output_dir=args.gold_reconstruction_output_dir,
        enable_source_discovery_prep=args.enable_source_discovery_prep,
        source_discovery_output_dir=args.source_discovery_output_dir,
        source_discovery_max_queries_per_sample=args.source_discovery_max_queries_per_sample,
        source_discovery_min_query_chars=args.source_discovery_min_query_chars,
        source_discovery_use_raw_fallback=args.source_discovery_use_raw_fallback,
        enable_source_candidate_search=args.enable_source_candidate_search,
        source_candidate_queries_path=args.source_candidate_queries,
        source_candidate_output_dir=args.source_candidate_output_dir,
        source_candidate_max_samples=args.source_candidate_max_samples,
        source_candidate_max_queries_per_sample=args.source_candidate_max_queries_per_sample,
        source_candidate_max_results_per_query=args.source_candidate_max_results_per_query,
        source_candidate_allowed_risk=args.source_candidate_allowed_risk,
        source_candidate_dry_run=bool(args.source_candidate_dry_run or not args.source_candidate_run_search),
        source_candidate_run_search=bool(args.source_candidate_run_search),
        source_candidate_provider=args.source_candidate_provider,
        source_candidate_api_key_env=args.source_candidate_api_key_env,
        source_candidate_timeout_seconds=args.source_candidate_timeout_seconds,
        enable_source_candidate_review=args.enable_source_candidate_review,
        source_candidate_results_path=args.source_candidate_results,
        source_candidate_review_decisions=args.source_candidate_review_decisions,
        source_candidate_review_output_dir=args.source_candidate_review_output_dir,
        source_candidate_allow_manual_url_additions=args.source_candidate_allow_manual_url_additions,
        source_candidate_allow_risky_seeds=args.source_candidate_allow_risky_seeds,
        enable_material_evidence_alignment_regression=args.enable_material_evidence_alignment_regression,
        material_evidence_output_dir=args.material_evidence_output_dir,
        material_evidence_source_seed_registry=args.material_evidence_source_seed_registry,
        material_evidence_crawl_seed_manifest=args.material_evidence_crawl_seed_manifest,
        material_evidence_source_text_approval=args.material_evidence_source_text_approval,
        material_evidence_manual_source_texts=args.material_evidence_manual_source_texts,
        material_evidence_gold_reconstruction_results=args.material_evidence_gold_reconstruction_results,
        material_evidence_material_card_draft=args.material_evidence_material_card_draft,
        material_evidence_quality_regression_draft=args.material_evidence_quality_regression_draft,
        material_evidence_agent_feedback=args.material_evidence_agent_feedback,
        material_evidence_source_text_mode=args.material_evidence_source_text_mode,
        material_evidence_alignment_mode=args.material_evidence_alignment_mode,
        material_evidence_alignment_model=args.material_evidence_alignment_model,
        material_evidence_alignment_base_url=args.material_evidence_alignment_base_url,
        material_evidence_alignment_api_key_env=args.material_evidence_alignment_api_key_env,
        material_evidence_alignment_timeout_seconds=args.material_evidence_alignment_timeout_seconds,
        material_evidence_alignment_max_output_tokens=args.material_evidence_alignment_max_output_tokens,
        enable_material_protocol_draft=args.enable_material_protocol_draft,
        material_protocol_draft_mode=args.material_protocol_draft_mode,
        material_protocol_draft_model=args.material_protocol_draft_model,
        material_protocol_draft_base_url=args.material_protocol_draft_base_url,
        material_protocol_draft_api_key_env=args.material_protocol_draft_api_key_env,
        material_protocol_draft_max_input_chars=args.material_protocol_draft_max_input_chars,
        material_protocol_draft_max_output_tokens=args.material_protocol_draft_max_output_tokens,
        material_protocol_draft_output_dir=args.material_protocol_draft_output_dir,
        material_protocol_draft_truth_gold_split_manifest=args.material_protocol_draft_truth_gold_split_manifest,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    if yaml is not None:
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _job_id(*, mother_family_id: str, leaf_label: str, source_files: list[str]) -> str:
    digest = hashlib.sha256("|".join([mother_family_id, leaf_label, *source_files]).encode("utf-8")).hexdigest()[:12]
    return f"leaf_pre_distill_{digest}"


def _parse_optional_bool(value: str) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _parse_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    main()

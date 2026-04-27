from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - lean environments
    yaml = None

from tools.leaf_pre_distill.llm_field_probe import (
    ChatClient,
    OpenAICompatibleChatClient,
    _parse_chat_completion_body,
)
from tools.leaf_pre_distill.material_protocol_draft_prompt import build_material_protocol_draft_messages


DEFAULT_MODEL = "chat"
DEFAULT_API_KEY_ENV = "LEAF_PRE_DISTILL_LLM_API_KEY"
DEFAULT_MAX_INPUT_CHARS = 8000
DEFAULT_MAX_OUTPUT_TOKENS = 2500
DEFAULT_TIMEOUT_SECONDS = 30

DRAFT_ARTIFACT_NAMES = {
    "system_alignment_findings": "system_alignment_findings.json",
    "material_protocol_draft_input_digest": "material_protocol_draft_input_digest.json",
    "material_card_draft": "material_card_draft.json",
    "material_line_prompt_assets_draft": "material_line_prompt_assets_draft.json",
    "material_quality_regression_draft": "material_quality_regression_draft.json",
    "material_review_prompts": "material_review_prompts.md",
    "material_bridge_mapping_draft": "material_bridge_mapping_draft.json",
    "material_protocol_assets_draft_report": "material_protocol_assets_draft_report.md",
}

REQUIRED_ASSET_FLAGS = {
    "status": "draft_only",
    "formalized": False,
    "writeback_allowed": False,
    "requires_human_review": True,
    "requires_regression": True,
}
FORBIDDEN_TRUE_KEYS = {
    "verified",
    "verified_original_source",
    "crawl_allowed",
    "material_library_write",
    "card_specs_write",
    "promotion_allowed",
    "writeback_allowed",
}


def run_material_protocol_draft(
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
        raise ValueError("material protocol draft mode must be dry-run, mock, or llm.")
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
    findings_path = output_path / DRAFT_ARTIFACT_NAMES["system_alignment_findings"]
    digest_path = output_path / DRAFT_ARTIFACT_NAMES["material_protocol_draft_input_digest"]
    _write_json(findings_path, alignment)
    _write_json(digest_path, digest)
    artifacts["system_alignment_findings"] = str(findings_path)
    artifacts["material_protocol_draft_input_digest"] = str(digest_path)

    bundle: dict[str, Any] | None = None
    blocked_errors: list[str] = []
    if mode == "mock":
        bundle = build_mock_material_protocol_bundle(digest=digest, alignment=alignment)
    elif mode == "llm":
        bundle, blocked_errors = run_llm_material_protocol_bundle(
            digest=digest,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
            client=client,
        )

    if bundle is not None:
        errors = validate_material_protocol_bundle(bundle=bundle, digest=digest, alignment=alignment)
        if errors:
            blocked_errors.extend(errors)
            bundle = None

    if bundle is not None:
        artifacts.update(write_material_protocol_bundle(output_path=output_path, bundle=bundle))

    report = render_material_protocol_assets_draft_report(
        mode=mode,
        digest=digest,
        alignment=alignment,
        bundle=bundle,
        blocked_errors=blocked_errors,
    )
    report_path = output_path / DRAFT_ARTIFACT_NAMES["material_protocol_assets_draft_report"]
    report_path.write_text(report, encoding="utf-8")
    artifacts["material_protocol_assets_draft_report"] = str(report_path)
    return artifacts


def build_system_alignment_findings(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    checked_files: list[str] = []
    warnings: list[str] = []

    runtime_path = root / "prompt_skeleton_service" / "configs" / "question_runtime.yaml"
    runtime_config = _read_yaml_or_json(runtime_path, checked_files, warnings)
    materials_config = dict((runtime_config.get("materials") or {}) if isinstance(runtime_config, dict) else {})

    material_schema_path = root / "passage_service" / "app" / "schemas" / "material_pipeline_v2.py"
    material_schema_text = _read_text(material_schema_path, checked_files, warnings)
    bridge_path = root / "prompt_skeleton_service" / "app" / "services" / "material_bridge_v2.py"
    bridge_text = _read_text(bridge_path, checked_files, warnings)
    bridge_fields = sorted(set(re.findall(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", material_schema_text, flags=re.MULTILINE)))
    select_material_fields = sorted(set(re.findall(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*[^=]+=", bridge_text, flags=re.MULTILINE)))

    route_files = [
        root / "passage_service" / "app" / "api" / "routes" / "articles.py",
        root / "passage_service" / "app" / "api" / "routes" / "materials.py",
        root / "passage_service" / "app" / "api" / "routes" / "materials_v2.py",
        root / "passage_service" / "app" / "api" / "routes" / "crawl.py",
    ]
    entrypoints: dict[str, Any] = {}
    for path in route_files:
        text = _read_text(path, checked_files, warnings)
        if text:
            entrypoints[str(path)] = sorted(set(re.findall(r'@router\.(?:get|post|put|delete)\("([^"]+)"', text)))

    material_cards_dir = root / "card_specs" / "normalized" / "material_cards"
    card_shape = inspect_material_card_shape(material_cards_dir, checked_files, warnings)
    mapping_path = root / "card_specs" / "normalized" / "runtime_mappings" / "distill_material_card_id_mapping.yaml"
    mapping_config = _read_yaml_or_json(mapping_path, checked_files, warnings)
    governance_path = root / "passage_service" / "app" / "config" / "material_governance.yaml"
    governance_config = _read_yaml_or_json(governance_path, checked_files, warnings)

    missing_or_unknown = []
    for label, value in [
        ("question_runtime.materials", materials_config),
        ("MaterialV2SearchRequest", bridge_fields),
        ("material_card_registry", card_shape),
        ("distill_material_card_id_mapping", mapping_config),
        ("material_governance", governance_config),
    ]:
        if not value:
            missing_or_unknown.append(label)

    return {
        "alignment_version": "v1",
        "checked_files": checked_files,
        "confirmed_existing_fields": {
            "MaterialV2SearchRequest": bridge_fields,
            "MaterialBridgeV2Service.select_materials": select_material_fields,
        },
        "confirmed_existing_entrypoints": entrypoints,
        "confirmed_material_card_shape": card_shape,
        "confirmed_bridge_request_fields": {
            "target_runtime": "MaterialV2SearchRequest" if bridge_fields else "unknown",
            "fields": bridge_fields,
        },
        "confirmed_runtime_material_config": materials_config,
        "confirmed_runtime_material_mapping": summarize_runtime_mapping(mapping_config),
        "confirmed_material_governance": summarize_material_governance(governance_config),
        "missing_or_unknown": missing_or_unknown,
        "naming_mismatches": [],
        "unsupported_assumptions_from_plan_doc": [],
        "recommended_minimal_compatible_mapping": build_minimal_compatible_mapping(bridge_fields, materials_config),
        "warnings": warnings,
    }


def inspect_material_card_shape(material_cards_dir: Path, checked_files: list[str], warnings: list[str]) -> dict[str, Any]:
    if not material_cards_dir.exists():
        warnings.append(f"material cards directory not found: {material_cards_dir}")
        return {}
    files = sorted(material_cards_dir.glob("*.yaml"))
    shape: dict[str, Any] = {"file_count": len(files), "files": [str(path) for path in files[:12]], "top_level_keys": [], "card_keys": []}
    top_keys: set[str] = set()
    card_keys: set[str] = set()
    for path in files[:5]:
        payload = _read_yaml_or_json(path, checked_files, warnings)
        if isinstance(payload, dict):
            top_keys.update(str(key) for key in payload.keys())
            for card in payload.get("cards") or []:
                if isinstance(card, dict):
                    card_keys.update(str(key) for key in card.keys())
    shape["top_level_keys"] = sorted(top_keys)
    shape["card_keys"] = sorted(card_keys)
    shape["has_proto_or_draft_examples"] = any("proto" in path.name.lower() or "draft" in path.name.lower() for path in files)
    return shape


def build_minimal_compatible_mapping(fields: list[str], materials_config: dict[str, Any]) -> dict[str, Any]:
    desired = [
        "business_family_id",
        "question_card_id",
        "business_card_ids",
        "preferred_business_card_ids",
        "query_terms",
        "topic",
        "text_direction",
        "document_genre",
        "material_structure_label",
        "target_length",
        "length_tolerance",
        "structure_constraints",
        "status",
        "release_channel",
        "review_gate_mode",
    ]
    confirmed = [field for field in desired if field in fields]
    return {
        "target_runtime": "MaterialV2SearchRequest" if fields else "unknown",
        "confirmed_fields": confirmed,
        "runtime_defaults": {
            "status": materials_config.get("default_status"),
            "release_channel": materials_config.get("default_release_channel"),
            "review_gate_mode": materials_config.get("review_gate_mode"),
            "candidate_pool_size": materials_config.get("candidate_pool_size"),
            "v2_search_path": materials_config.get("v2_search_path"),
        },
    }


def summarize_runtime_mapping(mapping_config: Any) -> dict[str, Any]:
    if not isinstance(mapping_config, dict):
        return {}
    batches = mapping_config.get("batches") or {}
    return {
        "schema_version": mapping_config.get("schema_version"),
        "batch_count": len(batches) if isinstance(batches, dict) else 0,
        "mapping_layers_seen": sorted(
            {
                key
                for batch in (batches.values() if isinstance(batches, dict) else [])
                if isinstance(batch, dict)
                for key in (batch.get("runtime_row_mapping") or {}).keys()
            }
        ),
    }


def summarize_material_governance(governance_config: Any) -> dict[str, Any]:
    if not isinstance(governance_config, dict):
        return {}
    return {
        "version": governance_config.get("version"),
        "minimums": governance_config.get("minimums") or {},
        "merge": governance_config.get("merge") or {},
        "labels": governance_config.get("labels") or {},
    }


def resolve_evidence_paths(
    *,
    artifact_dir: Path,
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
) -> dict[str, str | None]:
    candidates = {
        "manifest": artifact_dir / "manifest.json",
        "gold_reconstruction_results": gold_reconstruction_results or artifact_dir / "gold_reconstruction_results.jsonl",
        "truth_gold_regression_results": truth_gold_regression_results or artifact_dir / "truth_gold_regression_results.json",
        "truth_gold_split_manifest": truth_gold_split_manifest or artifact_dir / "truth_gold_split_manifest.json",
        "source_discovery_queries": source_discovery_queries or artifact_dir / "source_discovery_queries.jsonl",
        "material_source_profile": material_source_profile or artifact_dir / "material_source_profile.json",
        "source_candidate_summary": source_candidate_summary or artifact_dir / "source_candidate_summary.json",
        "source_candidate_review": source_candidate_review or artifact_dir / "source_candidate_review.json",
        "source_seed_registry": source_seed_registry or artifact_dir / "source_seed_registry.jsonl",
        "crawl_seed_manifest": crawl_seed_manifest or artifact_dir / "crawl_seed_manifest.json",
        "initial_plan_doc": initial_plan_doc or Path("docs/material_line_initial_protocol_assets_draft_plan_2026-04-26.md"),
    }
    resolved: dict[str, str | None] = {}
    for key, value in candidates.items():
        path = Path(value)
        resolved[key] = str(path) if path.exists() else None
    return resolved


def build_material_protocol_draft_input_digest(
    *,
    artifact_dir: str | Path,
    evidence_paths: dict[str, str | None],
    system_alignment_findings: dict[str, Any],
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
) -> dict[str, Any]:
    family_context = infer_family_context(artifact_dir=artifact_dir, evidence_paths=evidence_paths)
    missing = [key for key, value in evidence_paths.items() if value is None and key != "initial_plan_doc"]
    digest = {
        "digest_version": "v1",
        "family_context": family_context,
        "evidence_paths": evidence_paths,
        "missing_evidence": missing,
        "gold_reconstruction_summary": summarize_gold_reconstruction(evidence_paths.get("gold_reconstruction_results")),
        "truth_gold_regression_summary": summarize_json_file(evidence_paths.get("truth_gold_regression_results")),
        "truth_gold_split_summary": summarize_json_file(evidence_paths.get("truth_gold_split_manifest")),
        "source_discovery_summary": summarize_source_discovery(evidence_paths.get("source_discovery_queries"), evidence_paths.get("material_source_profile")),
        "source_candidate_summary": summarize_json_file(evidence_paths.get("source_candidate_summary")),
        "source_review_summary": summarize_json_file(evidence_paths.get("source_candidate_review")),
        "seed_registry_summary": summarize_seed_registry(evidence_paths.get("source_seed_registry"), evidence_paths.get("crawl_seed_manifest")),
        "system_alignment_findings_summary": summarize_alignment(system_alignment_findings),
        "existing_system_mapping_notes": system_alignment_findings.get("recommended_minimal_compatible_mapping") or {},
        "evidence_limits": [
            "No source body fetched yet unless provided.",
            "No source/gold alignment yet unless provided.",
            "No verified original source yet unless provided.",
            "No material quality regression yet unless provided.",
        ],
        "drafting_instructions": [
            "Generate draft-only material protocol assets.",
            "Do not formalize.",
            "Do not write card_specs.",
            "Use repository-confirmed fields when available.",
            "Use proposed fields only when marked as draft/proposed.",
        ],
    }
    return _truncate_digest(digest, max_chars=max_input_chars)


def infer_family_context(*, artifact_dir: str | Path, evidence_paths: dict[str, str | None]) -> dict[str, Any]:
    manifest = {}
    manifest_path = evidence_paths.get("manifest") or str(Path(artifact_dir) / "manifest.json")
    if manifest_path and Path(manifest_path).exists():
        manifest = _read_json(Path(manifest_path)) or {}
    mother = _clean_context_value(manifest.get("mother_family_id")) or "unknown"
    child = _clean_context_value(manifest.get("child_family_id")) or _clean_context_value(manifest.get("business_subtype")) or "unknown"
    leaf = _clean_context_value(manifest.get("leaf_label")) or "unknown"
    business_subtype = _clean_context_value(manifest.get("business_subtype")) or (child if child != "unknown" else None)
    question_focus = _clean_context_value(manifest.get("question_focus")) or (mother if mother != "unknown" else None)
    child_or_leaf = child if child and child != "unknown" else leaf
    return {
        "mother_family_id": mother,
        "child_family_id": child,
        "leaf_label": leaf,
        "business_subtype": business_subtype,
        "question_focus": question_focus,
        "question_card_reference": _clean_context_value(manifest.get("question_card_reference")),
        "material_card_id_draft": f"proto.{_safe_id(mother)}.{_safe_id(child_or_leaf)}.material.v0",
    }


def build_mock_material_protocol_bundle(*, digest: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
    family = dict(digest.get("family_context") or {})
    gaps = list(digest.get("missing_evidence") or [])
    bridge_fields = list((alignment.get("confirmed_bridge_request_fields") or {}).get("fields") or [])
    confirmed_mapping = alignment.get("recommended_minimal_compatible_mapping") or {}
    dimensions = build_default_quality_dimensions(family=family, digest=digest)
    review_prompts = build_material_review_prompts_markdown(family)
    return {
        "bundle_version": "v1",
        **REQUIRED_ASSET_FLAGS,
        "material_card_draft": {
            "draft_version": "v1",
            "asset_type": "material_card_draft",
            **REQUIRED_ASSET_FLAGS,
            "material_card_id_draft": family.get("material_card_id_draft"),
            "family_binding": family,
            "evidence_refs": {key: value for key, value in (digest.get("evidence_paths") or {}).items() if value},
            "source_policy": {
                "allowed_source_uses": ["original_source_candidate", "similar_material", "domain_seed"],
                "requires_source_verification_before_formalization": True,
                "allow_question_bank_sources": False,
                "verified_original_source_required_for_original_source_claim": True,
            },
            "material_requirements": infer_material_requirements(digest),
            "cleaning_and_slicing_hypothesis": {
                "hypothesis_only": True,
                "source_body_required": True,
                "source_gold_alignment_required": True,
                "candidate_rules": [],
                "risk_notes": ["Source body and source/gold alignment are required before turning this into a material card."],
            },
            "quality_gate_draft": {
                "requires_material_quality_regression": True,
                "requires_human_material_review": True,
                "draft_dimensions": [item["dimension"] for item in dimensions],
            },
            "system_compatibility": {
                "confirmed_existing_material_card_fields_used": list((alignment.get("confirmed_material_card_shape") or {}).get("card_keys") or []),
                "proposed_fields_not_in_current_schema": ["source_policy", "evidence_refs", "quality_gate_draft"],
                "compatible_with_material_bridge_v2": bool(bridge_fields),
                "compatible_with_materials_v2_search": "MaterialV2SearchRequest" in str(alignment.get("confirmed_bridge_request_fields")),
                "compatibility_notes": ["Draft fields must be transformed through a writeback plan before touching normalized material cards."],
            },
            "evidence_gaps": gaps,
            "next_required_evidence": next_required_evidence(gaps),
            "limits": ["Draft only. No card_specs, runtime mapping, material pool, prompt, validator, or question card writeback."],
        },
        "material_line_prompt_assets_draft": build_prompt_assets_draft(family),
        "material_quality_regression_draft": {
            "draft_version": "v1",
            "asset_type": "material_quality_regression_draft",
            **REQUIRED_ASSET_FLAGS,
            "family_context": family,
            "dimensions": dimensions,
            "limits": ["Scores do not replace human review and cannot approve material writeback."],
        },
        "material_review_prompts_markdown": review_prompts,
        "material_bridge_mapping_draft": {
            "mapping_draft_version": "v1",
            "asset_type": "material_bridge_mapping_draft",
            **REQUIRED_ASSET_FLAGS,
            "target_runtime": (alignment.get("confirmed_bridge_request_fields") or {}).get("target_runtime") or "unknown",
            "draft_mapping": build_bridge_mapping_from_family(family=family, confirmed_mapping=confirmed_mapping),
            "mapping_rationale": {
                "source": "system_alignment_findings",
                "note": "Only repository-confirmed MaterialV2SearchRequest fields are treated as existing fields.",
            },
            "confirmed_repository_fields_used": list(confirmed_mapping.get("confirmed_fields") or []),
            "proposed_fields_not_confirmed": [],
            "missing_evidence": gaps,
            "requires_bridge_smoke": True,
            "system_alignment_findings_ref": "system_alignment_findings.json",
            "limits": ["Do not call /materials/v2/search or modify question_runtime.yaml from this draft."],
        },
        "evidence_gaps": gaps,
        "next_required_evidence": next_required_evidence(gaps),
        "limits": [
            "Draft only.",
            "No source verification.",
            "No material_card writeback.",
            "No prompt, validator, runtime, question_card, card_specs, or material library mutation.",
        ],
    }


def build_prompt_assets_draft(family: dict[str, Any]) -> dict[str, Any]:
    base_forbidden = [
        "confirm_original_source",
        "set_verified_true",
        "write_material_card",
        "write_card_specs",
        "modify_question_card",
        "modify_prompt_assets",
        "modify_validator_contract",
        "modify_runtime_mapping",
        "promote_material",
        "call_material_ingest",
    ]
    prompts = {}
    for key, purpose in [
        ("source_evidence_review", "Review candidate source evidence without confirming original source."),
        ("source_gold_alignment", "Suggest alignment between fetched source body and reconstructed gold."),
        ("material_transformation_hypothesis", "Hypothesize how source material becomes test material."),
        ("material_quality_review", "Review whether candidate material is suitable for this family."),
        ("material_card_draft", "Draft material-card assets from reviewed evidence."),
    ]:
        prompts[key] = {
            "purpose": purpose,
            "model_role": "cautious material-line draft assistant",
            "input_artifacts": ["family_context", "evidence_digest", "system_alignment_findings"],
            "allowed_actions": [
                "cite evidence paths",
                "summarize uncertainty",
                "propose draft-only hypotheses",
                "adapt to family_context instead of hard-coding a family",
            ],
            "forbidden_actions": base_forbidden,
            "output_contract": {"status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True},
            "uncertainty_policy": "If evidence is missing or ambiguous, mark evidence_gaps and needs_human_review.",
            "family_adaptation_notes": f"Use current family_context: {family}",
        }
    return {
        "draft_version": "v1",
        "asset_type": "material_line_prompt_assets_draft",
        **REQUIRED_ASSET_FLAGS,
        "family_context": family,
        "global_forbidden_actions": base_forbidden,
        "prompts": prompts,
        "limits": ["Draft-only prompt assets. They are not formal prompt_assets config."],
    }


def build_default_quality_dimensions(*, family: dict[str, Any], digest: dict[str, Any]) -> list[dict[str, Any]]:
    missing = set(digest.get("missing_evidence") or [])
    specs = [
        ("source_provenance_status", "Track whether material is seed, fetched, aligned, or human verified.", "metadata"),
        ("question_bank_contamination", "Detect question-bank or training-site contamination.", "heuristic"),
        ("source_gold_alignment", "Evaluate evidence overlap between source body and reconstructed gold.", "model" if "gold_reconstruction_results" not in missing else "unavailable"),
        ("material_independence", "Check whether candidate material stands as natural text outside exam wrappers.", "human"),
        ("material_sufficiency", "Check length, context, information density, and completeness.", "heuristic"),
        ("slicing_quality", "Check whether selected spans preserve necessary context.", "model"),
        ("family_fit", "Assess whether material supports the current family context.", "model"),
        ("distractor_support", "Assess whether material can support plausible distractor mechanisms.", "model"),
        ("overfit_or_copy_risk", "Detect excessive copying from gold or question-bank material.", "heuristic"),
        ("bridge_compatibility", "Check whether draft can map to repository material bridge fields.", "metadata"),
        ("insurance_holdout_performance", "Check whether material strategy generalizes beyond observed samples.", "unavailable" if "truth_gold_regression_results" in missing else "metadata"),
    ]
    return [
        {
            "dimension": name,
            "purpose": purpose,
            "method": method,
            "confidence": "low" if method == "unavailable" else "medium",
            "limitation": "This dimension cannot approve material writeback and must be reviewed by a human.",
            "requires_human_review": True,
            "requires_future_evidence": [] if method != "unavailable" else ["missing required evidence artifact"],
            "family_context_hint": family,
        }
        for name, purpose, method in specs
    ]


def infer_material_requirements(digest: dict[str, Any]) -> dict[str, Any]:
    family = digest.get("family_context") or {}
    profile = digest.get("source_discovery_summary") or {}
    source_types = profile.get("source_type_distribution") or {}
    return {
        "document_genre_candidates": [],
        "likely_source_type": sorted(source_types.keys())[:6] if isinstance(source_types, dict) else [],
        "material_structure_label_candidates": [],
        "target_length": None,
        "length_tolerance": None,
        "context_dependency": "unknown; requires source body and source/gold alignment",
        "must_contain": [],
        "must_avoid": ["question_bank_page", "answer_explanation_page", "exam_training_page"],
        "usable_for_family": family.get("mother_family_id") or "unknown",
        "usable_for_leaf": family.get("child_family_id") or family.get("leaf_label") or "unknown",
        "evidence_basis": "Derived conservatively from current material-line evidence digest.",
    }


def build_bridge_mapping_from_family(*, family: dict[str, Any], confirmed_mapping: dict[str, Any]) -> dict[str, Any]:
    runtime_defaults = confirmed_mapping.get("runtime_defaults") or {}
    fields = set(confirmed_mapping.get("confirmed_fields") or [])
    values = {
        "business_family_id": family.get("mother_family_id"),
        "question_card_id": family.get("question_card_reference"),
        "business_card_ids": [],
        "preferred_business_card_ids": [],
        "query_terms": [],
        "topic": None,
        "text_direction": None,
        "document_genre": None,
        "material_structure_label": None,
        "target_length": None,
        "length_tolerance": 120,
        "structure_constraints": {},
        "status": runtime_defaults.get("status"),
        "release_channel": runtime_defaults.get("release_channel"),
        "review_gate_mode": runtime_defaults.get("review_gate_mode"),
    }
    return {key: value for key, value in values.items() if key in fields}


def build_material_review_prompts_markdown(family: dict[str, Any]) -> str:
    family_text = json.dumps(family, ensure_ascii=False)
    return f"""# 材料线人工审核提示词草案

适用 family_context：`{family_text}`

## Source Review 人审提示词

审候选 URL 的用途，不确认它就是原文。允许 decision：`keep_as_original_source_candidate`、`keep_as_similar_material_seed`、`keep_as_domain_seed`、`reject_question_bank`、`reject_irrelevant`、`defer`。禁止输出 `verified=true`、`verified_original_source=true`、`crawl_allowed=true`。证据不足、未打开网页、疑似题库/培训站时应 defer 或 reject。

## Source Evidence Review 人审提示词

审正文证据与 reconstructed gold 的关系，不审正式材料卡。需要区分可能原文、转载/改写、相似材料、题库污染和不相关页面。允许输出 evidence decision、rationale、uncertain_points、allowed_next_step。禁止确认原文或写材料库。

## Material Quality Review 人审提示词

审候选材料是否适合当前 family_context 的材料生产。重点看自然文本程度、上下文完整性、信息密度、可出题性、污染风险、过拟合风险和是否需要清洗/切片。禁止把统计分数当作自动批准。

## Material Card Draft Review 人审提示词

审 `material_card_draft` 是否确实基于 evidence、是否错误写死某题型、是否符合仓库真实字段、是否仍有 source body/alignment/regression 缺口。允许输出 keep_draft、revise、reject、defer。禁止直接写 `card_specs`、runtime mapping、prompt、validator 或 question_card。
"""


def run_llm_material_protocol_bundle(
    *,
    digest: dict[str, Any],
    model: str,
    base_url: str | None,
    api_key_env: str,
    max_output_tokens: int,
    timeout_seconds: int,
    client: ChatClient | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        active_client = client or OpenAICompatibleChatClient(
            base_url=base_url,
            api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
        )
        raw_text = active_client.complete(
            messages=build_material_protocol_draft_messages(digest),
            model=model,
            timeout_seconds=timeout_seconds,
            temperature=0.2,
            max_tokens=max_output_tokens,
        )
        parsed = _parse_json_object(raw_text)
        return parsed, []
    except Exception as exc:
        return None, [f"llm_material_protocol_draft_failed: {exc}"]


def validate_material_protocol_bundle(*, bundle: dict[str, Any], digest: dict[str, Any], alignment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, expected in REQUIRED_ASSET_FLAGS.items():
        if bundle.get(key) != expected:
            errors.append(f"bundle.{key} must be {expected!r}")
    for path, key, value in _walk_values(bundle):
        if key in FORBIDDEN_TRUE_KEYS and value is True:
            errors.append(f"{path}.{key} must not be true")
    family = digest.get("family_context") or {}
    draft_family = ((bundle.get("material_card_draft") or {}).get("family_binding") or {})
    for key in ("mother_family_id", "child_family_id", "leaf_label"):
        if str(draft_family.get(key) or "") != str(family.get(key) or ""):
            errors.append(f"material_card_draft.family_binding.{key} must match input family_context")
    for artifact_key in ("material_card_draft", "material_line_prompt_assets_draft", "material_quality_regression_draft", "material_bridge_mapping_draft"):
        artifact = bundle.get(artifact_key) or {}
        for key, expected in REQUIRED_ASSET_FLAGS.items():
            if artifact.get(key) != expected:
                errors.append(f"{artifact_key}.{key} must be {expected!r}")
    bridge = bundle.get("material_bridge_mapping_draft") or {}
    if "system_alignment_findings" not in json.dumps(bridge, ensure_ascii=False):
        errors.append("material_bridge_mapping_draft must reference system_alignment_findings")
    dimensions = ((bundle.get("material_quality_regression_draft") or {}).get("dimensions") or [])
    for index, dimension in enumerate(dimensions):
        for key in ("method", "confidence", "limitation"):
            if key not in dimension:
                errors.append(f"material_quality_regression_draft.dimensions[{index}].{key} is required")
    return errors


def write_material_protocol_bundle(*, output_path: Path, bundle: dict[str, Any]) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    mapping = {
        "material_card_draft": bundle.get("material_card_draft") or {},
        "material_line_prompt_assets_draft": bundle.get("material_line_prompt_assets_draft") or {},
        "material_quality_regression_draft": bundle.get("material_quality_regression_draft") or {},
        "material_bridge_mapping_draft": bundle.get("material_bridge_mapping_draft") or {},
    }
    for key, payload in mapping.items():
        path = output_path / DRAFT_ARTIFACT_NAMES[key]
        _write_json(path, payload)
        artifacts[key] = str(path)
    prompts_path = output_path / DRAFT_ARTIFACT_NAMES["material_review_prompts"]
    prompts_path.write_text(str(bundle.get("material_review_prompts_markdown") or ""), encoding="utf-8")
    artifacts["material_review_prompts"] = str(prompts_path)
    return artifacts


def render_material_protocol_assets_draft_report(
    *,
    mode: str,
    digest: dict[str, Any],
    alignment: dict[str, Any],
    bundle: dict[str, Any] | None,
    blocked_errors: list[str],
) -> str:
    family = digest.get("family_context") or {}
    gaps = digest.get("missing_evidence") or []
    lines = [
        "# 材料线协议资产草案报告",
        "",
        "## 基本信息",
        "",
        f"- mode: `{mode}`",
        f"- family_context: `{json.dumps(family, ensure_ascii=False)}`",
        f"- draft_generated: `{bundle is not None}`",
        f"- evidence_gaps_count: `{len(gaps)}`",
        "",
        "## 系统对齐摘要",
        "",
        f"- checked_files: `{len(alignment.get('checked_files') or [])}`",
        f"- target_runtime: `{(alignment.get('confirmed_bridge_request_fields') or {}).get('target_runtime') or 'unknown'}`",
        f"- bridge_fields: `{(alignment.get('confirmed_bridge_request_fields') or {}).get('fields') or []}`",
        f"- runtime_material_config: `{alignment.get('confirmed_runtime_material_config') or {}}`",
        f"- material_card_shape_keys: `{(alignment.get('confirmed_material_card_shape') or {}).get('card_keys') or []}`",
        "",
        "## 产物状态",
        "",
        f"- material_card_draft: `{'ready' if bundle else 'not_generated'}`",
        f"- material_line_prompt_assets_draft: `{'ready' if bundle else 'not_generated'}`",
        f"- material_quality_regression_draft: `{'ready' if bundle else 'not_generated'}`",
        f"- material_bridge_mapping_draft: `{'ready' if bundle else 'not_generated'}`",
        "",
        "## Evidence Gaps",
        "",
    ]
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- None")
    if bundle:
        lines.extend(["", "## Next Required Evidence", ""])
        for item in bundle.get("next_required_evidence") or []:
            lines.append(f"- {item}")
    if blocked_errors:
        lines.extend(["", "## Blocked Errors", ""])
        lines.extend(f"- {error}" for error in blocked_errors)
    lines.extend(
        [
            "",
            "## 边界声明",
            "",
            "- 本报告只整理 draft-only 材料线协议资产。",
            "- 没有网络访问、正文抓取、source verification、passage_service ingest 或 material promotion。",
            "- 没有写 material_card、card_specs、runtime mapping、prompt_assets、validator、question_card。",
            "- 模型或 mock 输出不能 formalize，后续必须继续 human review 与 regression。",
        ]
    )
    return "\n".join(lines) + "\n"


def summarize_gold_reconstruction(path: str | None) -> dict[str, Any]:
    rows = _read_jsonl_if_exists(path)
    if not rows:
        return {"available": False, "sample_count": 0}
    confidence = Counter(str(((row.get("reconstruction_summary") or {}).get("confidence")) or "unknown") for row in rows)
    review_count = sum(1 for row in rows if (row.get("reconstruction_summary") or {}).get("needs_human_review"))
    family_guess = Counter(str(row.get("question_family_guess") or "unknown") for row in rows)
    return {
        "available": True,
        "sample_count": len(rows),
        "confidence_distribution": dict(confidence),
        "needs_human_review_count": review_count,
        "question_family_guess_distribution": dict(family_guess),
    }


def summarize_source_discovery(queries_path: str | None, profile_path: str | None) -> dict[str, Any]:
    rows = _read_jsonl_if_exists(queries_path)
    profile = summarize_json_file(profile_path)
    risk = Counter(str(row.get("question_bank_contamination_risk") or "unknown") for row in rows)
    return {
        "available": bool(rows or profile.get("available")),
        "query_row_count": len(rows),
        "risk_distribution": dict(risk),
        "source_type_distribution": profile.get("source_type_distribution") or {},
        "profile": profile,
    }


def summarize_seed_registry(registry_path: str | None, crawl_manifest_path: str | None) -> dict[str, Any]:
    seeds = _read_jsonl_if_exists(registry_path)
    crawl = summarize_json_file(crawl_manifest_path)
    return {
        "available": bool(seeds or crawl.get("available")),
        "seed_count": len(seeds),
        "source_use_counts": dict(Counter(str(seed.get("source_use") or "unknown") for seed in seeds)),
        "crawl_allowed": crawl.get("crawl_allowed"),
        "ready_for_material_card_draft": crawl.get("ready_for_material_card_draft"),
    }


def summarize_json_file(path: str | None) -> dict[str, Any]:
    if not path or not Path(path).exists():
        return {"available": False}
    payload = _read_json(Path(path))
    if not isinstance(payload, dict):
        return {"available": True, "type": type(payload).__name__}
    summary = {"available": True}
    for key in (
        "mode",
        "gold_source",
        "sample_count",
        "candidate_count",
        "accepted_count",
        "rejected_count",
        "deferred_count",
        "seed_count",
        "verified_original_source_count",
        "crawl_allowed",
        "ready_for_material_card_draft",
        "source_type_distribution",
    ):
        if key in payload:
            summary[key] = payload.get(key)
    return summary


def summarize_alignment(alignment: dict[str, Any]) -> dict[str, Any]:
    return {
        "checked_file_count": len(alignment.get("checked_files") or []),
        "bridge_request_fields": (alignment.get("confirmed_bridge_request_fields") or {}).get("fields") or [],
        "runtime_material_config": alignment.get("confirmed_runtime_material_config") or {},
        "material_card_shape": alignment.get("confirmed_material_card_shape") or {},
        "missing_or_unknown": alignment.get("missing_or_unknown") or [],
    }


def next_required_evidence(gaps: list[str]) -> list[str]:
    required = []
    if "source_seed_registry" in gaps:
        required.append("source_candidate_human_review and source_seed_registry")
    required.extend(
        [
            "crawl approval before body fetch",
            "source_body_fetch_results before source/gold alignment",
            "source_gold_alignment before material_card formalization",
            "material_quality_regression before writeback plan",
        ]
    )
    return required


def _truncate_digest(digest: dict[str, Any], max_chars: int) -> dict[str, Any]:
    text = json.dumps(digest, ensure_ascii=False)
    if len(text) <= max_chars:
        return digest
    truncated = dict(digest)
    truncated["truncation"] = {"truncated": True, "max_chars": max_chars}
    for key in ("gold_reconstruction_summary", "truth_gold_regression_summary", "source_discovery_summary", "source_candidate_summary"):
        if key in truncated:
            truncated[key] = {"truncated": True}
    return truncated


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = _parse_chat_completion_body(raw_text)
        choices = payload.get("choices") or []
        content = str(((choices[0] if choices else {}).get("message") or {}).get("content") or "")
        payload = json.loads(_strip_code_fence(content))
    if not isinstance(payload, dict):
        raise ValueError("LLM output must be a JSON object")
    return payload


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _walk_values(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_values(item, f"{path}.{key}")
            yield path, str(key), item
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_values(item, f"{path}[{index}]")


def _read_text(path: Path, checked_files: list[str], warnings: list[str]) -> str:
    if not path.exists():
        warnings.append(f"missing file: {path}")
        return ""
    checked_files.append(str(path))
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")


def _read_yaml_or_json(path: Path, checked_files: list[str], warnings: list[str]) -> Any:
    text = _read_text(path, checked_files, warnings)
    if not text:
        return {}
    if yaml is not None:
        try:
            return yaml.safe_load(text) or {}
        except Exception as exc:
            warnings.append(f"failed to parse yaml {path}: {exc}")
            return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        warnings.append(f"yaml unavailable and JSON parse failed: {path}")
        return {}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl_if_exists(path: str | None) -> list[dict[str, Any]]:
    if not path or not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_context_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_id(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    return text.strip("_") or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build draft-only material protocol assets from material-line evidence.")
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--mode", choices=("dry-run", "mock", "llm"), default="dry-run")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--max-input-chars", type=int, default=DEFAULT_MAX_INPUT_CHARS)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
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
    artifacts = run_material_protocol_draft(
        artifact_dir=args.artifact_dir,
        output_dir=args.output_dir,
        mode=args.mode,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        max_input_chars=args.max_input_chars,
        max_output_tokens=args.max_output_tokens,
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

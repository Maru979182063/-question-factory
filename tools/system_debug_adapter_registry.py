from __future__ import annotations

from copy import deepcopy
from typing import Any


SYSTEM_DEBUG_ADAPTER_REGISTRY_VERSION = "v1"


DEFAULT_ADAPTER_REGISTRY: list[dict[str, Any]] = [
    {
        "adapter_name": "gold_reconstruction_to_truth_gold_regression",
        "source_chain": "gold_reconstruction",
        "source_artifact_role": "gold_reconstruction_results",
        "source_artifact_patterns": ["gold_reconstruction_results.jsonl"],
        "target_chain": "truth_gold_regression",
        "target_input_role": "reconstructed_gold_reference",
        "required_fields": [
            "sample_id",
            "reconstruction_summary.confidence",
            "reconstruction_summary.needs_human_review",
            "gold_material",
            "gold_question",
        ],
        "optional_fields": [
            "answer_mechanism",
            "distractor_mechanism",
            "gold_quality_flags",
        ],
        "missing_field_strategy": "block",
        "manual_path_allowed": True,
        "contract_status": "explicit",
        "notes": "truth_gold_regression 已优先读取 gold_reconstruction_results.jsonl；缺核心 gold schema 字段时不能当作可靠 gold 输入。",
    },
    {
        "adapter_name": "source_review_seed_registry_to_material_protocol_split_pipeline",
        "source_chain": "source_discovery_review",
        "source_artifact_role": "source_seed_registry",
        "source_artifact_patterns": ["source_seed_registry.jsonl"],
        "target_chain": "material_protocol_split_pipeline",
        "target_input_role": "reviewed_source_seed_evidence",
        "required_fields": [
            "seed_id",
            "sample_id",
            "source_use",
            "status",
            "formalized",
            "verified",
            "verified_original_source",
        ],
        "optional_fields": [
            "url",
            "domain",
            "title",
            "linked_query",
            "review_rationale",
            "warnings",
        ],
        "missing_field_strategy": "block",
        "manual_path_allowed": True,
        "contract_status": "explicit",
        "notes": "material_protocol_split_pipeline 可显式接收 source_seed_registry / crawl_seed_manifest 作为 evidence；seed 仍不是 verified source。",
    },
    {
        "adapter_name": "source_review_crawl_manifest_to_material_protocol_split_pipeline",
        "source_chain": "source_discovery_review",
        "source_artifact_role": "crawl_seed_manifest",
        "source_artifact_patterns": ["crawl_seed_manifest.json"],
        "target_chain": "material_protocol_split_pipeline",
        "target_input_role": "crawl_boundary_evidence",
        "required_fields": [
            "crawl_allowed",
            "requires_explicit_crawl_approval",
            "ready_for_material_card_draft",
        ],
        "optional_fields": [
            "seed_count",
            "domain_counts",
            "priority_counts",
            "recommended_limits",
        ],
        "missing_field_strategy": "warn",
        "manual_path_allowed": True,
        "contract_status": "explicit",
        "notes": "该连接只提供 crawl 边界证据，不批准抓正文。",
    },
    {
        "adapter_name": "source_review_to_material_cleaning_slicing_chain",
        "source_chain": "source_discovery_review",
        "source_artifact_role": "source_seed_registry",
        "source_artifact_patterns": ["source_seed_registry.jsonl"],
        "target_chain": "material_cleaning_slicing_chain",
        "target_input_role": "seed_for_future_body_fetch_and_cleaning",
        "required_fields": [
            "seed_id",
            "url",
            "source_use",
            "status",
        ],
        "optional_fields": [
            "crawl_priority",
            "negative_patterns",
            "verification_status",
            "review_rationale",
        ],
        "missing_field_strategy": "manual_fill",
        "manual_path_allowed": True,
        "contract_status": "manual_only",
        "notes": "清洗/选段链尚未实现；source seed 只能作为未来 crawl approval/body fetch 的人工输入线索。",
    },
    {
        "adapter_name": "material_protocol_split_to_question_generation_runtime",
        "source_chain": "material_protocol_split_pipeline",
        "source_artifact_role": "material_bridge_mapping_draft",
        "source_artifact_patterns": [
            "06_material_bridge_mapping_draft.json",
            "material_bridge_mapping_draft.json",
        ],
        "target_chain": "question_generation_runtime",
        "target_input_role": "material_bridge_mapping_candidate",
        "required_fields": [
            "asset_type",
            "status",
            "formalized",
            "writeback_allowed",
        ],
        "optional_fields": [
            "draft_mapping",
            "confirmed_repository_fields_used",
            "requires_bridge_smoke",
            "limits",
        ],
        "missing_field_strategy": "manual_fill",
        "manual_path_allowed": True,
        "contract_status": "manual_only",
        "notes": "材料协议草案不能直接驱动生题主链；必须经过人审、回归、写回计划和受控写回。",
    },
    {
        "adapter_name": "question_protocol_patch_to_question_generation_runtime",
        "source_chain": "question_protocol_patch_chain",
        "source_artifact_role": "formal_writeback_manifest",
        "source_artifact_patterns": [
            "formal_writeback_manifest.json",
            "formal_patch_draft.json",
            "formal_writeback_plan.json",
        ],
        "target_chain": "question_generation_runtime",
        "target_input_role": "guarded_proto_config_candidate",
        "required_fields": [
            "formalized",
            "writeback_allowed",
        ],
        "optional_fields": [
            "approved_targets",
            "written_files",
            "rollback_patch_path",
            "regression_report_path",
        ],
        "missing_field_strategy": "manual_fill",
        "manual_path_allowed": True,
        "contract_status": "inferred",
        "notes": "题卡/协议 patch 与生题主链的连接取决于是否经过 guarded executor 写入 allowlist proto 文件；当前总控台只登记关系。",
    },
    {
        "adapter_name": "question_generation_to_difficulty_control",
        "source_chain": "question_generation_runtime",
        "source_artifact_role": "generation_trial_result",
        "source_artifact_patterns": [
            "generation_trial_result.json",
            "distill_run_generation_snapshot.json",
            "distill_run_detail.json",
        ],
        "target_chain": "difficulty_control_chain",
        "target_input_role": "generated_item_for_difficulty_assessment",
        "required_fields": [
            "request_snapshot",
            "sample_results",
        ],
        "optional_fields": [
            "item_preview",
            "fit_summary",
            "item_ids",
        ],
        "missing_field_strategy": "degrade",
        "manual_path_allowed": True,
        "contract_status": "inferred",
        "notes": "生题输出可进入难度评估，但 durable artifact 形态尚未统一；缺字段时只能降级为人工抽取。",
    },
    {
        "adapter_name": "truth_gold_regression_to_difficulty_control",
        "source_chain": "truth_gold_regression",
        "source_artifact_role": "truth_gold_regression_results",
        "source_artifact_patterns": ["truth_gold_regression_results.json"],
        "target_chain": "difficulty_control_chain",
        "target_input_role": "gold_difficulty_reference",
        "required_fields": [
            "regression_version",
            "gold_source",
            "summary",
        ],
        "optional_fields": [
            "split_scores",
            "dimensions",
            "sample_results",
        ],
        "missing_field_strategy": "warn",
        "manual_path_allowed": True,
        "contract_status": "inferred",
        "notes": "truth gold 回归能提供 gold reference 和 split 信息，但当前难度 backtest runner 还没有统一接入。",
    },
    {
        "adapter_name": "question_generation_to_distillation_workbench",
        "source_chain": "question_generation_runtime",
        "source_artifact_role": "distill_run_detail",
        "source_artifact_patterns": [
            "distill_run_detail.json",
            "generation_trial_result.json",
        ],
        "target_chain": "distillation_runtime_workbench",
        "target_input_role": "distill_trial_generation_result",
        "required_fields": [
            "run_id",
            "status",
            "request_snapshot",
            "sample_results",
        ],
        "optional_fields": [
            "fit_summary",
            "item_preview",
            "item_ids",
            "error",
        ],
        "missing_field_strategy": "block",
        "manual_path_allowed": True,
        "contract_status": "explicit",
        "notes": "distill workbench trial 本身调用生题 runner 并保存 run detail；缺 run/request/sample 结构时不能进入 review/patch/promotion。",
    },
    {
        "adapter_name": "difficulty_control_to_distillation_workbench",
        "source_chain": "difficulty_control_chain",
        "source_artifact_role": "difficulty_diff",
        "source_artifact_patterns": [
            "difficulty_diff.json",
            "difficulty_calibration_patch.json",
            "difficulty_backtest_report.md",
        ],
        "target_chain": "distillation_runtime_workbench",
        "target_input_role": "difficulty_fit_evidence",
        "required_fields": [
            "fit_result",
            "axis_diff",
        ],
        "optional_fields": [
            "patch_candidates",
            "promotion_recommendation",
            "validator_status",
        ],
        "missing_field_strategy": "degrade",
        "manual_path_allowed": True,
        "contract_status": "inferred",
        "notes": "难度链可作为 distill review/promotion 的 evidence；当前不是 workbench 的强自动输入。",
    },
]


VALID_CONTRACT_STATUSES = {"explicit", "inferred", "manual_only"}
VALID_MISSING_FIELD_STRATEGIES = {"block", "warn", "degrade", "manual_fill"}


def default_adapter_registry() -> list[dict[str, Any]]:
    return deepcopy(DEFAULT_ADAPTER_REGISTRY)


def validate_adapter_registry(adapters: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required_keys = {
        "adapter_name",
        "source_chain",
        "source_artifact_role",
        "target_chain",
        "target_input_role",
        "required_fields",
        "optional_fields",
        "missing_field_strategy",
        "manual_path_allowed",
        "contract_status",
        "notes",
    }
    names: set[str] = set()
    for index, adapter in enumerate(adapters):
        missing = sorted(required_keys - set(adapter))
        if missing:
            errors.append(f"adapter[{index}] missing keys: {', '.join(missing)}")
        name = str(adapter.get("adapter_name") or "")
        if not name:
            errors.append(f"adapter[{index}] has empty adapter_name")
        elif name in names:
            errors.append(f"duplicate adapter_name: {name}")
        names.add(name)
        if adapter.get("contract_status") not in VALID_CONTRACT_STATUSES:
            errors.append(f"{name} has invalid contract_status: {adapter.get('contract_status')}")
        if adapter.get("missing_field_strategy") not in VALID_MISSING_FIELD_STRATEGIES:
            errors.append(f"{name} has invalid missing_field_strategy: {adapter.get('missing_field_strategy')}")
        for field_key in ("required_fields", "optional_fields"):
            if not isinstance(adapter.get(field_key), list):
                errors.append(f"{name} {field_key} must be a list")
    return errors


def build_adapter_registry_artifact(
    *,
    adapters: list[dict[str, Any]] | None = None,
    resolutions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    entries = default_adapter_registry() if adapters is None else deepcopy(adapters)
    validation_errors = validate_adapter_registry(entries)
    status_counts: dict[str, int] = {}
    for adapter in entries:
        status = str(adapter.get("contract_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    artifact = {
        "adapter_registry_version": SYSTEM_DEBUG_ADAPTER_REGISTRY_VERSION,
        "read_only": True,
        "auto_execute": False,
        "writeback_allowed": False,
        "adapter_count": len(entries),
        "contract_status_counts": status_counts,
        "adapters": entries,
        "validation_errors": validation_errors,
        "limits": [
            "Adapter entries describe connection semantics only.",
            "They do not execute chains, call LLMs, promote patches, crawl pages, or write formal configs.",
        ],
    }
    if resolutions is not None:
        artifact["resolutions"] = deepcopy(resolutions)
    return artifact


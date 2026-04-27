from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_adapters(
    *,
    adapters: list[dict[str, Any]],
    artifact_index: dict[str, Any],
    chain_reports: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    chain_status = {
        str(chain.get("chain_name")): str(chain.get("current_status") or "")
        for chain in (chain_reports or [])
    }
    resolutions: list[dict[str, Any]] = []
    for adapter in adapters:
        source_artifact = find_adapter_source_artifact(adapter=adapter, artifact_index=artifact_index)
        missing_fields: list[str] = []
        field_check_status = "not_checked"
        if source_artifact is not None:
            payload = _load_artifact_payload(Path(source_artifact["path"]))
            missing_fields = missing_required_fields(payload, adapter.get("required_fields") or [])
            field_check_status = "ok" if not missing_fields else "missing_required_fields"
        resolution_status = infer_resolution_status(
            adapter=adapter,
            source_artifact=source_artifact,
            missing_fields=missing_fields,
            chain_status=chain_status,
        )
        manual_bridge_required = adapter.get("contract_status") == "manual_only" or resolution_status == "manual_required"
        ready_to_connect = (
            resolution_status in {"ready", "ready_with_warning", "degraded"}
            and adapter.get("contract_status") != "manual_only"
            and chain_status.get(str(adapter.get("target_chain"))) != "registered_only"
        )
        resolutions.append(
            {
                "adapter_name": adapter.get("adapter_name"),
                "source_chain": adapter.get("source_chain"),
                "target_chain": adapter.get("target_chain"),
                "contract_status": adapter.get("contract_status"),
                "missing_field_strategy": adapter.get("missing_field_strategy"),
                "manual_path_allowed": bool(adapter.get("manual_path_allowed")),
                "source_artifact": source_artifact,
                "field_check_status": field_check_status,
                "missing_required_fields": missing_fields,
                "resolution_status": resolution_status,
                "ready_to_connect": ready_to_connect,
                "manual_bridge_required": manual_bridge_required,
                "degrade_path": build_degrade_path(adapter, resolution_status),
                "notes": adapter.get("notes") or "",
            }
        )
    return resolutions


def find_adapter_source_artifact(*, adapter: dict[str, Any], artifact_index: dict[str, Any]) -> dict[str, Any] | None:
    patterns = [str(pattern).replace("\\", "/") for pattern in adapter.get("source_artifact_patterns") or []]
    candidates: list[dict[str, Any]] = []
    for artifact in artifact_index.get("artifacts") or []:
        path = str(artifact.get("path") or "").replace("\\", "/")
        filename = str(artifact.get("filename") or "")
        if any(filename == pattern or path.endswith(pattern) for pattern in patterns):
            candidates.append(artifact)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.get("modified_at") or "", reverse=True)[0]


def missing_required_fields(payload: Any, required_fields: list[str]) -> list[str]:
    if payload is None:
        return list(required_fields)
    return [field for field in required_fields if not _has_field(payload, field)]


def infer_resolution_status(
    *,
    adapter: dict[str, Any],
    source_artifact: dict[str, Any] | None,
    missing_fields: list[str],
    chain_status: dict[str, str],
) -> str:
    if chain_status.get(str(adapter.get("source_chain"))) == "registered_only" and source_artifact is None:
        return "source_registered_only"
    if chain_status.get(str(adapter.get("target_chain"))) == "registered_only":
        if source_artifact is None:
            return "target_registered_only"
    if source_artifact is None:
        return "manual_required" if adapter.get("manual_path_allowed") else "blocked"
    if adapter.get("contract_status") == "manual_only":
        return "manual_required"
    if missing_fields:
        strategy = adapter.get("missing_field_strategy")
        if strategy == "block":
            return "blocked"
        if strategy == "warn":
            return "ready_with_warning"
        if strategy == "degrade":
            return "degraded"
        if strategy == "manual_fill":
            return "manual_required"
        return "blocked"
    return "ready"


def build_degrade_path(adapter: dict[str, Any], resolution_status: str) -> str:
    strategy = str(adapter.get("missing_field_strategy") or "")
    if resolution_status == "ready":
        return "none"
    if resolution_status == "ready_with_warning":
        return "continue_with_warning_and_human_review"
    if resolution_status == "degraded":
        return "degrade_to_manual_evidence_review"
    if resolution_status == "manual_required":
        return "manual_path_or_manual_field_fill_required"
    if resolution_status == "source_registered_only":
        return "source_chain_artifact_not_available"
    if resolution_status == "target_registered_only":
        return "target_chain_registered_but_not_artifact_ready"
    if strategy == "block":
        return "block_until_required_fields_exist"
    return "blocked"


def adapter_coverage_summary(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    contract_counts: dict[str, int] = {}
    ready_count = 0
    manual_count = 0
    blocked_count = 0
    for item in resolutions:
        status = str(item.get("resolution_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        contract = str(item.get("contract_status") or "unknown")
        contract_counts[contract] = contract_counts.get(contract, 0) + 1
        if item.get("ready_to_connect"):
            ready_count += 1
        if item.get("manual_bridge_required"):
            manual_count += 1
        if status in {"blocked", "source_registered_only", "target_registered_only"}:
            blocked_count += 1
    return {
        "adapter_count": len(resolutions),
        "ready_to_connect_count": ready_count,
        "manual_bridge_required_count": manual_count,
        "blocked_or_registered_only_count": blocked_count,
        "resolution_status_counts": status_counts,
        "contract_status_counts": contract_counts,
    }


def adapters_by_chain(resolutions: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    by_chain: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in resolutions:
        source = str(item.get("source_chain") or "")
        target = str(item.get("target_chain") or "")
        by_chain.setdefault(source, {"outbound": [], "inbound": []})["outbound"].append(item)
        by_chain.setdefault(target, {"outbound": [], "inbound": []})["inbound"].append(item)
    return by_chain


def _load_artifact_payload(path: Path) -> Any:
    try:
        if path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    return json.loads(line)
            return None
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _has_field(payload: Any, field_path: str) -> bool:
    if isinstance(payload, list):
        return bool(payload) and _has_field(payload[0], field_path)
    current = payload
    for part in str(field_path).split("."):
        if isinstance(current, list):
            if not current:
                return False
            current = current[0]
        if not isinstance(current, dict) or part not in current:
            return False
        current = current.get(part)
    return current is not None


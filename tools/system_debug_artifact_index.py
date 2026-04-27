from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_artifact_index(
    *,
    artifact_root: str | Path,
    chain_registry: list[dict[str, Any]],
    explicit_artifacts: list[str | Path] | None = None,
    extra_artifact_patterns: list[str] | None = None,
    max_files: int = 5000,
) -> dict[str, Any]:
    root = Path(artifact_root).resolve()
    candidates = _collect_candidate_paths(root, explicit_artifacts=explicit_artifacts, max_files=max_files)
    chain_patterns = {
        str(chain.get("chain_name")): {str(pattern) for pattern in chain.get("artifact_patterns") or []}
        for chain in chain_registry
    }
    extra_patterns = {str(pattern).replace("\\", "/") for pattern in extra_artifact_patterns or []}
    entries: list[dict[str, Any]] = []
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        matches = _match_chains(path, chain_patterns)
        extra_match = _matches_any_pattern(path, extra_patterns)
        if not matches and not extra_match:
            continue
        stat = path.stat()
        entries.append(
            {
                "path": str(path),
                "relative_path": _safe_relative(path, root),
                "filename": path.name,
                "suffix": path.suffix,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "matched_chains": matches,
                "matched_by_adapter_pattern": bool(extra_match and not matches),
                "artifact_role": _infer_artifact_role(path.name),
                "status_hint": _read_status_hint(path),
            }
        )
    entries.sort(key=lambda item: ((item["matched_chains"] or ["__adapter_source__"])[0], item["relative_path"]))
    return {
        "index_version": "v1",
        "artifact_root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(entries),
        "artifacts": entries,
        "chain_artifact_counts": _count_by_chain(entries),
        "read_only": True,
        "limits": [
            "This artifact index only reads existing files.",
            "It does not execute chains, call LLMs, verify sources, or write formal configs.",
        ],
    }


def artifacts_for_chain(index: dict[str, Any], chain_name: str) -> list[dict[str, Any]]:
    return [
        artifact
        for artifact in index.get("artifacts") or []
        if chain_name in (artifact.get("matched_chains") or [])
    ]


def latest_artifact_for_chain(index: dict[str, Any], chain_name: str) -> dict[str, Any] | None:
    artifacts = artifacts_for_chain(index, chain_name)
    if not artifacts:
        return None
    return sorted(artifacts, key=lambda item: item.get("modified_at") or "", reverse=True)[0]


def _collect_candidate_paths(
    root: Path,
    *,
    explicit_artifacts: list[str | Path] | None,
    max_files: int,
) -> list[Path]:
    paths: list[Path] = []
    if root.exists():
        for index, path in enumerate(root.rglob("*")):
            if index >= max_files:
                break
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md"}:
                paths.append(path.resolve())
    for item in explicit_artifacts or []:
        paths.append(Path(item).resolve())
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).lower()
        if key not in seen:
            deduped.append(path)
            seen.add(key)
    return deduped


def _match_chains(path: Path, chain_patterns: dict[str, set[str]]) -> list[str]:
    normalized = str(path).replace("\\", "/")
    matches: list[str] = []
    for chain_name, patterns in chain_patterns.items():
        for pattern in patterns:
            pattern_norm = pattern.replace("\\", "/")
            if path.name == pattern_norm or normalized.endswith(pattern_norm):
                matches.append(chain_name)
                break
    return matches


def _matches_any_pattern(path: Path, patterns: set[str]) -> bool:
    normalized = str(path).replace("\\", "/")
    return any(path.name == pattern or normalized.endswith(pattern) for pattern in patterns)


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _infer_artifact_role(filename: str) -> str:
    name = filename.lower()
    if "state" in name:
        return "state"
    if "report" in name:
        return "report"
    if "bundle" in name:
        return "bundle"
    if "patch" in name:
        return "patch"
    if "manifest" in name:
        return "manifest"
    if "review" in name:
        return "review"
    if "diff" in name:
        return "diff"
    if name.endswith(".jsonl"):
        return "records"
    return "artifact"


def _read_status_hint(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"parse_error": True}
    hint: dict[str, Any] = {}
    for key in (
        "status",
        "pipeline_complete",
        "blocked",
        "crawl_allowed",
        "ready_for_material_card_draft",
        "verified_original_source_count",
    ):
        if key in payload:
            hint[key] = payload.get(key)
    if "stages" in payload and isinstance(payload["stages"], dict):
        hint["stage_status_counts"] = _stage_status_counts(payload["stages"])
    if "status_counts" in payload:
        hint["status_counts"] = payload.get("status_counts")
    return hint


def _stage_status_counts(stages: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in stages.values():
        status = str((item or {}).get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _count_by_chain(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        for chain_name in entry.get("matched_chains") or []:
            counts[chain_name] = counts.get(chain_name, 0) + 1
    return counts

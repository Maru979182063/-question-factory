from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def build_system_debug_run_manifest(
    *,
    artifact_root: str | Path,
    chain_registry: list[dict[str, Any]],
    artifact_index: dict[str, Any],
    system_debug_run_id: str | None = None,
) -> dict[str, Any]:
    run_id = system_debug_run_id or f"system_debug_{uuid4().hex[:12]}"
    chain_counts = artifact_index.get("chain_artifact_counts") or {}
    chain_rows = []
    for chain in chain_registry:
        name = str(chain.get("chain_name"))
        chain_rows.append(
            {
                "chain_name": name,
                "category": chain.get("category"),
                "maturity_level": chain.get("maturity_level"),
                "registered": True,
                "artifact_count": int(chain_counts.get(name) or 0),
                "dependency_on": list(chain.get("dependency_on") or []),
                "blocked_by": list(chain.get("blocked_by") or []),
            }
        )
    return {
        "manifest_version": "v1",
        "system_debug_run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact_root": str(Path(artifact_root).resolve()),
        "read_only": True,
        "auto_execute": False,
        "llm_calls_allowed": False,
        "writeback_allowed": False,
        "chains": chain_rows,
        "dependency_edges": build_dependency_edges(chain_registry),
        "limits": [
            "This manifest registers chain status for debug control-plane visibility only.",
            "It does not execute generation, distillation, material crawling, validation, promotion, or writeback.",
        ],
    }


def build_dependency_edges(chain_registry: list[dict[str, Any]]) -> list[dict[str, str]]:
    known = {str(chain.get("chain_name")) for chain in chain_registry}
    edges: list[dict[str, str]] = []
    for chain in chain_registry:
        target = str(chain.get("chain_name"))
        for source in chain.get("dependency_on") or []:
            dependency_type = "explicit" if source in known else "external_or_registered_later"
            edges.append(
                {
                    "from": str(source),
                    "to": target,
                    "dependency_type": dependency_type,
                }
            )
    return edges


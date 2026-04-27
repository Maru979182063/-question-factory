from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGE_ORDER = [
    ("material_evidence_map", "01_material_evidence_map.json"),
    ("material_semantic_requirements_draft", "02_material_semantic_requirements_draft.json"),
    ("material_card_draft", "03_material_card_draft.json"),
    ("material_line_prompt_assets_draft", "04_material_line_prompt_assets_draft.json"),
    ("material_quality_regression_draft", "05_material_quality_regression_draft.json"),
    ("material_bridge_mapping_draft", "06_material_bridge_mapping_draft.json"),
]
STAGE_FILE_BY_KEY = dict(STAGE_ORDER)


def initial_pipeline_state(*, mode: str, output_dir: str | Path) -> dict[str, Any]:
    return {
        "state_version": "v1",
        "mode": mode,
        "output_dir": str(output_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "stages": {
            key: {
                "stage": key,
                "status": "pending",
                "output_path": None,
                "error_summary": "",
                "retry_count": 0,
                "duration_seconds": 0.0,
                "attempts": [],
            }
            for key, _ in STAGE_ORDER
        },
    }


def load_or_init_pipeline_state(*, state_path: str | Path, mode: str, output_dir: str | Path, resume: bool) -> dict[str, Any]:
    path = Path(state_path)
    if resume and path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        for key, _ in STAGE_ORDER:
            state.setdefault("stages", {}).setdefault(
                key,
                {
                    "stage": key,
                    "status": "pending",
                    "output_path": None,
                    "error_summary": "",
                    "retry_count": 0,
                    "duration_seconds": 0.0,
                    "attempts": [],
                },
            )
        return state
    return initial_pipeline_state(mode=mode, output_dir=output_dir)


def save_pipeline_state(state_path: str | Path, state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    Path(state_path).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def update_stage_state(
    state: dict[str, Any],
    *,
    stage_key: str,
    status: str,
    output_path: str | Path | None = None,
    error_summary: str = "",
    retry_count: int | None = None,
    duration_seconds: float | None = None,
    attempt: dict[str, Any] | None = None,
) -> None:
    stage = state.setdefault("stages", {}).setdefault(stage_key, {"stage": stage_key})
    stage["status"] = status
    if output_path is not None:
        stage["output_path"] = str(output_path)
    if error_summary:
        stage["error_summary"] = error_summary
    elif status in {"success", "skipped"}:
        stage["error_summary"] = ""
    if retry_count is not None:
        stage["retry_count"] = retry_count
    if duration_seconds is not None:
        stage["duration_seconds"] = round(float(duration_seconds), 3)
    if attempt is not None:
        stage.setdefault("attempts", []).append(attempt)


def stage_succeeded(state: dict[str, Any], stage_key: str) -> bool:
    stage = (state.get("stages") or {}).get(stage_key) or {}
    output_path = stage.get("output_path")
    return stage.get("status") == "success" and bool(output_path) and Path(output_path).exists()

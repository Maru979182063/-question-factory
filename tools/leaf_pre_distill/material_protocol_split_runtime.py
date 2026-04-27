from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from tools.leaf_pre_distill.material_protocol_split_state import (
    STAGE_FILE_BY_KEY,
    STAGE_ORDER,
    load_or_init_pipeline_state,
    save_pipeline_state,
    stage_succeeded,
    update_stage_state,
)
from tools.leaf_pre_distill.material_protocol_split_stage_report import write_pipeline_stage_reports


class StageProviderError(RuntimeError):
    pass


class StageValidationError(RuntimeError):
    pass


StageBuilder = Callable[[str, dict[str, Any]], dict[str, Any]]
StageValidator = Callable[[dict[str, dict[str, Any]]], list[str]]


def execute_split_stages(
    *,
    output_dir: str | Path,
    mode: str,
    stage_builder: StageBuilder,
    stage_validator: StageValidator,
    resume: bool = False,
    max_retries: int = 1,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, str]]:
    output_path = Path(output_dir)
    stages_dir = output_path / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_path / "pipeline_state.json"
    state = load_or_init_pipeline_state(state_path=state_path, mode=mode, output_dir=output_path, resume=resume)
    artifacts: dict[str, str] = {"pipeline_state": str(state_path)}
    completed: dict[str, dict[str, Any]] = {}

    for stage_key, filename in STAGE_ORDER:
        stage_path = stages_dir / filename
        if resume and stage_succeeded(state, stage_key):
            completed[stage_key] = json.loads(Path(state["stages"][stage_key]["output_path"]).read_text(encoding="utf-8"))
            update_stage_state(state, stage_key=stage_key, status="skipped", output_path=state["stages"][stage_key]["output_path"])
            save_pipeline_state(state_path, state)
            continue

        retry_count = 0
        start = time.monotonic()
        while True:
            attempt_start = time.monotonic()
            try:
                payload = stage_builder(stage_key, completed)
                candidate = dict(completed)
                candidate[stage_key] = payload
                errors = stage_validator(candidate)
                stage_errors = [error for error in errors if stage_key in error or "missing stage" not in error]
                if stage_errors:
                    raise StageValidationError("; ".join(stage_errors))
                stage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                completed[stage_key] = payload
                update_stage_state(
                    state,
                    stage_key=stage_key,
                    status="success",
                    output_path=stage_path,
                    retry_count=retry_count,
                    duration_seconds=time.monotonic() - start,
                    attempt={
                        "status": "success",
                        "duration_seconds": round(time.monotonic() - attempt_start, 3),
                    },
                )
                artifacts[stage_key] = str(stage_path)
                save_pipeline_state(state_path, state)
                break
            except StageValidationError as exc:
                update_stage_state(
                    state,
                    stage_key=stage_key,
                    status="validation_error",
                    error_summary=str(exc),
                    retry_count=retry_count,
                    duration_seconds=time.monotonic() - start,
                    attempt={
                        "status": "validation_error",
                        "error": str(exc),
                        "duration_seconds": round(time.monotonic() - attempt_start, 3),
                    },
                )
                save_pipeline_state(state_path, state)
                reports = write_pipeline_stage_reports(output_dir=output_path, state=state)
                artifacts.update(reports)
                return completed, state, artifacts
            except Exception as exc:
                if retry_count < max_retries:
                    retry_count += 1
                    update_stage_state(
                        state,
                        stage_key=stage_key,
                        status="retrying",
                        error_summary=str(exc),
                        retry_count=retry_count,
                        duration_seconds=time.monotonic() - start,
                        attempt={
                            "status": "provider_error",
                            "error": str(exc),
                            "duration_seconds": round(time.monotonic() - attempt_start, 3),
                        },
                    )
                    save_pipeline_state(state_path, state)
                    continue
                update_stage_state(
                    state,
                    stage_key=stage_key,
                    status="provider_error",
                    error_summary=str(exc),
                    retry_count=retry_count,
                    duration_seconds=time.monotonic() - start,
                    attempt={
                        "status": "provider_error",
                        "error": str(exc),
                        "duration_seconds": round(time.monotonic() - attempt_start, 3),
                    },
                )
                save_pipeline_state(state_path, state)
                reports = write_pipeline_stage_reports(output_dir=output_path, state=state)
                artifacts.update(reports)
                return completed, state, artifacts

    reports = write_pipeline_stage_reports(output_dir=output_path, state=state)
    artifacts.update(reports)
    return completed, state, artifacts

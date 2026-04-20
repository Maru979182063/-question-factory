from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import time
from typing import Any


class RuntimeTrace:
    def __init__(self, *, request_id: str, path: str, client_id: str | None = None) -> None:
        self.request_id = request_id
        self.path = path
        self.client_id = client_id
        self.started_at = time.perf_counter()
        self.stage_timings_ms: dict[str, float] = {}
        self.metadata: dict[str, Any] = {}

    @contextmanager
    def stage(self, name: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self.stage_timings_ms[name] = round(self.stage_timings_ms.get(name, 0.0) + elapsed_ms, 2)

    def note(self, **values: Any) -> None:
        for key, value in values.items():
            if value is not None:
                self.metadata[key] = value

    def snapshot(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "path": self.path,
            "client_id": self.client_id,
            "duration_ms": round((time.perf_counter() - self.started_at) * 1000, 2),
            "stage_timings": dict(self.stage_timings_ms),
            **self.metadata,
        }


_CURRENT_TRACE: ContextVar[RuntimeTrace | None] = ContextVar("prompt_runtime_trace", default=None)


def begin_request_trace(*, request_id: str, path: str, client_id: str | None = None) -> RuntimeTrace:
    trace = RuntimeTrace(request_id=request_id, path=path, client_id=client_id)
    _CURRENT_TRACE.set(trace)
    return trace


def clear_request_trace() -> None:
    _CURRENT_TRACE.set(None)


def get_current_trace() -> RuntimeTrace | None:
    return _CURRENT_TRACE.get()


@contextmanager
def trace_stage(name: str):
    trace = get_current_trace()
    if trace is None:
        yield
        return
    with trace.stage(name):
        yield


def note_trace_metadata(**values: Any) -> None:
    trace = get_current_trace()
    if trace is None:
        return
    trace.note(**values)


def persist_runtime_event(
    *,
    event_type: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    task_id: str | None = None,
    path: str | None = None,
    client_id: str | None = None,
) -> dict[str, Any]:
    trace = get_current_trace()
    effective_request_id = request_id or (trace.request_id if trace else None)
    effective_path = path or (trace.path if trace else None)
    effective_client_id = client_id or (trace.client_id if trace else None)
    merged_details = dict(details or {})
    if trace is not None and not merged_details.get("stage_timings"):
        merged_details["stage_timings"] = dict(trace.stage_timings_ms)
    from app.core.dependencies import get_question_repository

    return get_question_repository().save_runtime_event(
        event_type=event_type,
        severity=severity,
        message=message,
        details=merged_details,
        request_id=effective_request_id,
        task_id=task_id,
        path=effective_path,
        client_id=effective_client_id,
    )

from __future__ import annotations

import logging
from threading import Event, Thread
from uuid import uuid4

from app.core.dependencies import (
    get_prompt_template_registry,
    get_question_repository,
    get_registry,
    get_runtime_registry,
)
from app.core.exceptions import DomainError
from app.core.settings import get_settings
from app.schemas.question import QuestionGenerateRequest
from app.services.prompt_orchestrator import PromptOrchestratorService
from app.services.question_generation import QuestionGenerationService
from app.services.runtime_observer import begin_request_trace, clear_request_trace, note_trace_metadata, persist_runtime_event, trace_stage


logger = logging.getLogger(__name__)


class AsyncGenerationQueueService:
    def __init__(self) -> None:
        self._stop_event = Event()
        self._threads: list[Thread] = []

    def start(self) -> None:
        settings = get_settings().async_tasks
        if not settings.enabled or settings.worker_count <= 0 or self._threads:
            return
        self._stop_event.clear()
        for index in range(settings.worker_count):
            worker_id = f"prompt-worker-{index + 1}"
            thread = Thread(target=self._worker_loop, args=(worker_id,), name=worker_id, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop_event.set()
        for thread in list(self._threads):
            thread.join(timeout=2)
        self._threads.clear()

    def submit(self, request: QuestionGenerateRequest, *, client_id: str | None = None) -> dict:
        request_id = str(uuid4())
        task = get_question_repository().enqueue_async_generation_task(
            payload=request.model_dump(mode="json"),
            request_id=request_id,
            client_id=client_id,
        )
        persist_runtime_event(
            event_type="async_task_enqueued",
            severity="info",
            message="Async generation task queued.",
            request_id=request_id,
            task_id=task.get("task_id"),
            client_id=client_id,
            details={"generation_mode": request.generation_mode, "question_focus": request.question_focus},
        )
        return task

    def get_task(self, task_id: str) -> dict | None:
        return get_question_repository().get_async_generation_task(task_id)

    def list_tasks(self, *, status: str | None = None, limit: int | None = None) -> list[dict]:
        history_limit = limit or get_settings().async_tasks.history_limit
        return get_question_repository().list_async_generation_tasks(status=status, limit=history_limit)

    def summary(self) -> dict:
        return get_question_repository().get_async_generation_task_summary(
            history_limit=get_settings().async_tasks.history_limit
        )

    def _worker_loop(self, worker_id: str) -> None:
        settings = get_settings().async_tasks
        repository = get_question_repository()
        while not self._stop_event.is_set():
            task = repository.claim_next_async_generation_task(worker_id=worker_id, lease_seconds=settings.lease_seconds)
            if task is None:
                self._stop_event.wait(settings.poll_interval_seconds)
                continue
            self._process_task(worker_id=worker_id, task=task)

    def _process_task(self, *, worker_id: str, task: dict) -> None:
        task_id = str(task.get("task_id"))
        request_id = str(task.get("request_id") or uuid4())
        begin_request_trace(request_id=request_id, path="/api/v1/questions/generate-async", client_id=task.get("client_id"))
        try:
            note_trace_metadata(async_task_id=task_id, worker_id=worker_id)
            with trace_stage("task_decode"):
                request = QuestionGenerateRequest.model_validate(task.get("request") or {})
            with trace_stage("task_generate"):
                result = self._build_generation_service().generate(request)
            batch_id = result.get("batch_id") if isinstance(result, dict) else None
            note_trace_metadata(batch_id=batch_id, task_status="succeeded")
            get_question_repository().mark_async_generation_task_succeeded(
                task_id=task_id,
                result=result,
                batch_id=batch_id,
                request_id=request_id,
            )
            persist_runtime_event(
                event_type="async_task_succeeded",
                severity="info",
                message="Async generation task completed.",
                task_id=task_id,
                details={"batch_id": batch_id},
            )
        except DomainError as exc:
            note_trace_metadata(task_status="failed", error_status_code=exc.status_code)
            error_payload = {
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
            }
            get_question_repository().mark_async_generation_task_failed(
                task_id=task_id,
                error=error_payload,
                request_id=request_id,
            )
            persist_runtime_event(
                event_type="async_task_failed",
                severity="warning" if exc.status_code < 500 else "error",
                message=exc.message,
                task_id=task_id,
                details=error_payload,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("async_generation_task_failed task_id=%s worker_id=%s", task_id, worker_id)
            note_trace_metadata(task_status="failed", error_type=type(exc).__name__)
            error_payload = {
                "message": "Unexpected async generation error.",
                "exception_type": type(exc).__name__,
                "details": {"reason": str(exc)},
            }
            get_question_repository().mark_async_generation_task_failed(
                task_id=task_id,
                error=error_payload,
                request_id=request_id,
            )
            persist_runtime_event(
                event_type="async_task_failed",
                severity="error",
                message="Unexpected async generation error.",
                task_id=task_id,
                details=error_payload,
            )
        finally:
            clear_request_trace()

    @staticmethod
    def _build_generation_service() -> QuestionGenerationService:
        registry = get_registry()
        runtime_registry = get_runtime_registry()
        prompt_template_registry = get_prompt_template_registry()
        repository = get_question_repository()
        return QuestionGenerationService(
            orchestrator=PromptOrchestratorService(registry),
            runtime_config=runtime_registry.get(),
            repository=repository,
            prompt_template_registry=prompt_template_registry,
        )


_ASYNC_QUEUE: AsyncGenerationQueueService | None = None


def get_async_generation_queue() -> AsyncGenerationQueueService:
    global _ASYNC_QUEUE
    if _ASYNC_QUEUE is None:
        _ASYNC_QUEUE = AsyncGenerationQueueService()
    return _ASYNC_QUEUE

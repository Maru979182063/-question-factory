import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

try:
    from fastapi.exceptions import RequestValidationError
except Exception:  # pragma: no cover - test stub compatibility
    class RequestValidationError(Exception):
        def errors(self) -> list[dict]:
            return []

from app.services.runtime_observer import note_trace_metadata, persist_runtime_event


class DomainError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        client_identity = (getattr(request.state, "client_identity", {}) or {}).get("client_id")
        details = {**exc.details, "request_id": request_id}
        if request.url.path.endswith("/generate") and details.get("reason") in {"queue_full", "queue_timeout"}:
            details.setdefault("async_submit_path", "/api/v1/questions/generate-async")
            details.setdefault("task_poll_prefix", "/api/v1/questions/generate-async/tasks/")
        note_trace_metadata(error_status_code=exc.status_code, error_message=exc.message, error_details=details)
        persist_runtime_event(
            event_type="domain_error",
            severity="warning" if exc.status_code < 500 else "error",
            message=exc.message,
            details=details,
            request_id=request_id,
            path=request.url.path,
            client_id=client_identity,
        )
        logger.warning(
            "domain_error request_id=%s method=%s path=%s status=%s message=%s details=%s",
            request_id,
            request.method,
            request.url.path,
            exc.status_code,
            exc.message,
            exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "details": details,
                }
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        details = {"errors": exc.errors(), "request_id": request_id}
        note_trace_metadata(error_status_code=422, validation_errors=exc.errors())
        persist_runtime_event(
            event_type="request_validation_error",
            severity="warning",
            message="Request validation failed.",
            details=details,
            request_id=request_id,
            path=request.url.path,
            client_id=(getattr(request.state, "client_identity", {}) or {}).get("client_id"),
        )
        logger.warning(
            "request_validation_error request_id=%s method=%s path=%s errors=%s",
            request_id,
            request.method,
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": "Request validation failed.",
                    "details": details,
                }
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        details = {"request_id": request_id, "reason": str(exc)}
        note_trace_metadata(error_status_code=500, error_type=type(exc).__name__)
        persist_runtime_event(
            event_type="unexpected_error",
            severity="error",
            message="Unexpected server error.",
            details={**details, "exception_type": type(exc).__name__},
            request_id=request_id,
            path=request.url.path,
            client_id=(getattr(request.state, "client_identity", {}) or {}).get("client_id"),
        )
        logger.exception(
            "unexpected_error request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Unexpected server error.",
                    "details": details,
                }
            },
            headers={"X-Request-ID": request_id} if request_id else {},
        )

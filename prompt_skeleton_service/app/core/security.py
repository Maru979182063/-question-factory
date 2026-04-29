from __future__ import annotations

import hashlib
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.settings import get_settings
from app.services.runtime_observer import begin_request_trace, clear_request_trace, note_trace_metadata, persist_runtime_event
from app.services.shared_state import get_shared_state_backend


logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/healthz", "/readyz", "/docs", "/openapi.json", "/redoc"}
    EXEMPT_PREFIXES = ("/docs/oauth2-redirect", "/demo", "/demo-static", "/api/v1/distill/access")
    PUBLIC_DEMO_BLOCKED_PREFIXES = ("/api/v1/admin", "/api/v1/diagnostics")

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        client_identity = self._resolve_client_identity(request, settings.security)
        request.state.client_identity = client_identity
        begin_request_trace(request_id=request_id, path=request.url.path, client_id=client_identity["client_id"])
        start = time.perf_counter()

        try:
            if settings.public_demo_mode and self._is_public_demo_blocked_path(request.url.path):
                return JSONResponse(
                    status_code=404,
                    content={"error": {"message": "Not found.", "details": {"request_id": request_id}}},
                    headers={"X-Request-ID": request_id},
                )
            if settings.public_demo_mode and self._is_public_demo_distill_api_path(request.url.path):
                distill_response = self._check_public_demo_distill_access(request, request_id)
                if distill_response is not None:
                    return distill_response
            if self._should_protect(request.url.path):
                auth_response = self._check_auth(request, request_id, settings.security.enabled, settings.security.api_token)
                if auth_response is not None:
                    return auth_response
                rate_response = self._check_rate_limit(
                    request,
                    request_id,
                    client_identity=client_identity,
                    limit=settings.security.rate_limit_per_minute,
                )
                if rate_response is not None:
                    return rate_response

            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            self._attach_generation_gate_headers(request, response)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            note_trace_metadata(
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_identity=client_identity,
                queue_wait_seconds=getattr(request.state, "generation_gate", {}).get("wait_seconds")
                if isinstance(getattr(request.state, "generation_gate", None), dict)
                else None,
            )
            persist_runtime_event(
                event_type="request_complete",
                severity="info",
                message="Request completed.",
                details={
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_identity": client_identity,
                    "queue_wait_seconds": getattr(request.state, "generation_gate", {}).get("wait_seconds")
                    if isinstance(getattr(request.state, "generation_gate", None), dict)
                    else None,
                },
            )
            logger.info(
                "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s client_id=%s",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                client_identity["client_id"],
            )
            return response
        finally:
            clear_request_trace()

    def _should_protect(self, path: str) -> bool:
        if path in self.EXEMPT_PATHS:
            return False
        return not any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES)

    def _is_public_demo_blocked_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.PUBLIC_DEMO_BLOCKED_PREFIXES)

    def _is_public_demo_distill_api_path(self, path: str) -> bool:
        return path.startswith("/api/v1/distill") and not path.startswith("/api/v1/distill/access")

    def _check_public_demo_distill_access(self, request: Request, request_id: str) -> JSONResponse | None:
        from app.core.dependencies import get_runtime_registry

        config = get_runtime_registry().get().ui.distill_access
        if not config.enabled:
            return None

        expected_key = str(config.key or "").strip()
        if not expected_key:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "message": "Distill access is not configured for public demo.",
                        "details": {"request_id": request_id},
                    }
                },
                headers={"X-Request-ID": request_id},
            )

        expected_cookie = hashlib.sha256(expected_key.encode("utf-8")).hexdigest()
        provided_cookie = request.cookies.get(config.cookie_name)
        if provided_cookie == expected_cookie:
            return None

        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Distill access key is required.",
                    "details": {"request_id": request_id},
                }
            },
            headers={"X-Request-ID": request_id},
        )

    def _check_auth(
        self,
        request: Request,
        request_id: str,
        enabled: bool,
        api_token: str | None,
    ) -> JSONResponse | None:
        if not enabled:
            return None

        expected = f"Bearer {api_token}" if api_token else None
        provided = request.headers.get("Authorization")
        if expected and provided == expected:
            return None

        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Unauthorized request.",
                    "details": {"request_id": request_id},
                }
            },
            headers={"X-Request-ID": request_id},
        )

    def _check_rate_limit(
        self,
        request: Request,
        request_id: str,
        *,
        client_identity: dict[str, str],
        limit: int,
    ) -> JSONResponse | None:
        key = f"{client_identity['client_id']}:{request.url.path}"
        decision = get_shared_state_backend().allow_rate_limit(key=key, limit=limit)
        if decision.allowed:
            note_trace_metadata(
                rate_limit={
                    "limit": limit,
                    "remaining": decision.remaining,
                    "backend": decision.backend,
                }
            )
            return None
        persist_runtime_event(
            event_type="rate_limited",
            severity="warning",
            message="Request rejected by rate limiter.",
            request_id=request_id,
            path=request.url.path,
            client_id=client_identity["client_id"],
            details={
                "limit": limit,
                "retry_after_seconds": decision.retry_after_seconds,
                "backend": decision.backend,
                "client_identity": client_identity,
            },
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": "Too many requests.",
                    "details": {
                        "request_id": request_id,
                        "retry_after_seconds": decision.retry_after_seconds,
                        "client_identity": client_identity["client_id"],
                    },
                }
            },
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-Request-ID": request_id,
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(decision.remaining),
            },
        )

    def _resolve_client_identity(self, request: Request, security_settings) -> dict[str, str]:
        fallback_ip = request.client.host if request.client else "unknown"
        chosen_ip = fallback_ip
        source = "request.client"
        if security_settings.trust_forwarded_headers:
            for header_name in security_settings.client_ip_header_priority:
                raw_value = request.headers.get(header_name)
                if not raw_value:
                    continue
                if header_name == "x-forwarded-for":
                    parts = [part.strip() for part in raw_value.split(",") if part.strip()]
                    if parts:
                        index = min(len(parts) - 1, max(0, security_settings.forwarded_for_index))
                        chosen_ip = parts[index]
                        source = header_name
                        break
                else:
                    chosen_ip = raw_value.strip()
                    source = header_name
                    break
        token_fingerprint = request.headers.get("Authorization")
        identity_parts = [chosen_ip]
        if token_fingerprint:
            identity_parts.append(token_fingerprint[-12:])
        client_id = "|".join(identity_parts)
        return {
            "client_ip": chosen_ip,
            "client_id": client_id,
            "source": source,
        }

    def _attach_generation_gate_headers(self, request: Request, response: JSONResponse) -> None:
        gate_state = getattr(request.state, "generation_gate", None)
        if not isinstance(gate_state, dict):
            return

        header_mapping = {
            "queue_position": "X-Generation-Queue-Position",
            "wait_seconds": "X-Generation-Wait-Seconds",
            "active_requests": "X-Generation-Active",
            "waiting_requests": "X-Generation-Waiting",
            "max_concurrent": "X-Generation-Max-Concurrent",
            "max_waiting": "X-Generation-Max-Waiting",
        }
        for key, header_name in header_mapping.items():
            value = gate_state.get(key)
            if value is None:
                continue
            response.headers[header_name] = str(value)


def install_security_middleware(app: FastAPI) -> None:
    app.add_middleware(SecurityMiddleware)

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import httpx

from app.core.dependencies import (
    get_prompt_template_registry,
    get_question_repository,
    get_registry,
    get_runtime_registry,
)
from app.core.settings import get_settings
from app.services.generation_gate import get_generation_gate


def build_prompt_diagnostics() -> dict[str, Any]:
    settings = get_settings()
    runtime = _safe_load_runtime()
    checks = [
        _path_check("config_dir", settings.config_dir, critical=True),
        _path_check("runtime_config_path", settings.runtime_config_path, critical=True),
        _path_check("prompt_template_config_path", settings.prompt_template_config_path, critical=True),
        _question_repository_check(settings.question_db_path),
        _config_registry_check(),
        _prompt_template_check(),
        _runtime_registry_check(runtime),
        _passage_service_check(runtime),
        _single_passage_endpoint_check(
            name="shadow_passage_service",
            base_url=getattr(getattr(runtime, "materials", None), "shadow_base_url", None),
            search_path=getattr(getattr(runtime, "materials", None), "shadow_v2_search_path", None),
        ),
    ]
    return {
        "service": "prompt_skeleton_service",
        "status": _overall_status(checks),
        "checks": checks,
        "settings": {
            "config_dir": str(settings.config_dir),
            "runtime_config_path": str(settings.runtime_config_path),
            "prompt_template_config_path": str(settings.prompt_template_config_path),
            "question_db_path": str(settings.question_db_path),
            "generation_queue": {
                "max_concurrent": settings.generation_queue.max_concurrent,
                "max_waiting": settings.generation_queue.max_waiting,
                "acquire_timeout_seconds": settings.generation_queue.acquire_timeout_seconds,
            },
        },
        "runtime_state": {"generation_queue": get_generation_gate().snapshot()},
    }


def _safe_load_runtime() -> Any:
    try:
        return get_runtime_registry().get()
    except Exception:
        return None


def _path_check(name: str, path: Path, *, critical: bool) -> dict[str, Any]:
    exists = path.exists()
    return {
        "name": name,
        "status": "ok" if exists else "error",
        "critical": critical,
        "details": {
            "path": str(path),
            "exists": exists,
            "kind": "dir" if path.is_dir() else "file",
        },
    }


def _question_repository_check(db_path: Path) -> dict[str, Any]:
    details: dict[str, Any] = {"path": str(db_path), "exists": db_path.exists()}
    try:
        repository = get_question_repository()
        details["repository_initialized"] = True
        with sqlite3.connect(repository.db_path) as conn:
            conn.execute("SELECT 1").fetchone()
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        details["reason"] = str(exc)
    return {
        "name": "question_repository",
        "status": status,
        "critical": True,
        "details": details,
    }


def _config_registry_check() -> dict[str, Any]:
    details: dict[str, Any] = {}
    try:
        registry = get_registry()
        types = registry.list_types()
        details["loaded_types"] = len(types)
        details["warnings"] = list(getattr(registry, "_warnings", []))
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        details["reason"] = str(exc)
    return {
        "name": "config_registry",
        "status": status,
        "critical": True,
        "details": details,
    }


def _prompt_template_check() -> dict[str, Any]:
    details: dict[str, Any] = {}
    try:
        registry = get_prompt_template_registry()
        templates = registry.list_templates()
        details["active_templates"] = len(templates)
        status = "ok"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        details["reason"] = str(exc)
    return {
        "name": "prompt_template_registry",
        "status": status,
        "critical": True,
        "details": details,
    }


def _runtime_registry_check(runtime: Any) -> dict[str, Any]:
    details: dict[str, Any] = {}
    if runtime is None:
        return {
            "name": "runtime_registry",
            "status": "error",
            "critical": True,
            "details": {"reason": "Runtime config could not be loaded."},
        }
    details["materials_base_url"] = runtime.materials.base_url
    details["materials_v2_search_path"] = runtime.materials.v2_search_path
    details["shadow_base_url"] = runtime.materials.shadow_base_url
    details["shadow_v2_search_path"] = runtime.materials.shadow_v2_search_path
    details["llm_provider"] = runtime.llm.active_provider
    return {
        "name": "runtime_registry",
        "status": "ok",
        "critical": True,
        "details": details,
    }


def _passage_service_check(runtime: Any) -> dict[str, Any]:
    if runtime is None:
        return {
            "name": "passage_service",
            "status": "error",
            "critical": True,
            "details": {"reason": "Runtime config unavailable."},
        }
    bridge_mode = getattr(getattr(runtime, "materials", None), "bridge_mode", "legacy_only")
    base_url = runtime.materials.base_url.rstrip("/")
    health_url = f"{base_url}/healthz"
    ready_url = f"{base_url}/readyz"
    details: dict[str, Any] = {
        "base_url": base_url,
        "health_url": health_url,
        "ready_url": ready_url,
        "bridge_mode": bridge_mode,
    }
    try:
        with httpx.Client(timeout=3.0, trust_env=False) as client:
            response = client.get(ready_url)
            if response.status_code == 404:
                response = client.get(health_url)
                payload = None
            else:
                payload = response.json() if "application/json" in response.headers.get("content-type", "") else None
        details["status_code"] = response.status_code
        details["reachable"] = response.is_success
        if isinstance(payload, dict):
            details["service_status"] = payload.get("status")
            details["service_name"] = payload.get("service")
            settings_payload = payload.get("settings") or {}
            if isinstance(settings_payload, dict):
                for key in (
                    "database_url",
                    "resolved_database_url",
                    "resolved_database_path",
                    "database_mode",
                    "allow_non_primary_database",
                    "expected_primary_database_name",
                ):
                    if key in settings_payload:
                        details[key] = settings_payload[key]
            database_check = next(
                (
                    check.get("details") or {}
                    for check in (payload.get("checks") or [])
                    if check.get("name") == "database"
                ),
                {},
            )
            if isinstance(database_check, dict):
                for key in (
                    "material_span_count",
                    "primary_material_count",
                    "v2_indexed_primary_count",
                    "database_exists",
                    "db_pool_size",
                    "db_max_overflow",
                    "db_pool_timeout_seconds",
                    "db_pool_recycle_seconds",
                ):
                    if key in database_check:
                        details[key] = database_check[key]
        status = "ok" if response.is_success else "error"
    except Exception as exc:  # noqa: BLE001
        status = "warning" if bridge_mode == "leaf_only" else "error"
        details["reachable"] = False
        details["reason"] = str(exc)
    return {
        "name": "passage_service",
        "status": status,
        "critical": bridge_mode != "leaf_only",
        "details": details,
    }


def _single_passage_endpoint_check(*, name: str, base_url: str | None, search_path: str | None = None) -> dict[str, Any]:
    normalized = str(base_url or "").rstrip("/")
    if not normalized:
        return {
            "name": name,
            "status": "warning",
            "critical": False,
            "details": {"reason": "Not configured."},
        }
    health_url = f"{normalized}/healthz"
    ready_url = f"{normalized}/readyz"
    details: dict[str, Any] = {
        "base_url": normalized,
        "health_url": health_url,
        "ready_url": ready_url,
    }
    if search_path:
        details["search_path"] = search_path
    try:
        with httpx.Client(timeout=3.0, trust_env=False) as client:
            response = client.get(ready_url)
            if response.status_code == 404:
                response = client.get(health_url)
                payload = None
            else:
                payload = response.json() if "application/json" in response.headers.get("content-type", "") else None
        details["status_code"] = response.status_code
        details["reachable"] = response.is_success
        if isinstance(payload, dict):
            details["service_status"] = payload.get("status")
            settings_payload = payload.get("settings") or {}
            if isinstance(settings_payload, dict):
                for key in ("resolved_database_path", "database_mode", "allow_non_primary_database"):
                    if key in settings_payload:
                        details[key] = settings_payload[key]
        status = "ok" if response.is_success else "error"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        details["reachable"] = False
        details["reason"] = str(exc)
    return {
        "name": name,
        "status": status,
        "critical": False,
        "details": details,
    }


def _overall_status(checks: list[dict[str, Any]]) -> str:
    if any(check["critical"] and check["status"] != "ok" for check in checks):
        return "not_ready"
    if any(check["status"] != "ok" for check in checks):
        return "degraded"
    return "ready"

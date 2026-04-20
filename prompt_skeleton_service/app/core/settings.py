from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel


class SecuritySettings(BaseModel):
    enabled: bool = False
    api_token: str | None = None
    rate_limit_per_minute: int = 120
    trust_forwarded_headers: bool = True
    forwarded_for_index: int = 0
    client_ip_header_priority: list[str] = ["cf-connecting-ip", "true-client-ip", "x-forwarded-for", "x-real-ip"]


class GenerationQueueSettings(BaseModel):
    max_concurrent: int = 2
    max_waiting: int = 12
    acquire_timeout_seconds: int = 240


class SharedStateSettings(BaseModel):
    backend: str = "sqlite"


class AsyncTaskSettings(BaseModel):
    enabled: bool = True
    worker_count: int = 1
    poll_interval_seconds: float = 1.0
    lease_seconds: int = 900
    history_limit: int = 100


class AppSettings(BaseModel):
    base_dir: Path
    config_dir: Path
    runtime_config_path: Path
    prompt_template_config_path: Path
    data_dir: Path
    question_db_path: Path
    security: SecuritySettings
    generation_queue: GenerationQueueSettings
    shared_state: SharedStateSettings
    async_tasks: AsyncTaskSettings


def _read_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path_env(name: str, *, base_dir: Path, default: Path) -> Path:
    raw = os.getenv(name)
    if not raw:
        return default
    path = Path(raw)
    if not path.is_absolute():
        path = base_dir / path
    return path


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = _resolve_path_env("PROMPT_DATA_DIR", base_dir=base_dir, default=base_dir / "data")
    api_token = os.getenv("PROMPT_SERVICE_API_TOKEN")
    security_enabled = _read_bool_env("PROMPT_SERVICE_SECURITY_ENABLED", default=bool(api_token))
    rate_limit_per_minute = int(os.getenv("PROMPT_SERVICE_RATE_LIMIT_PER_MINUTE", "120"))
    return AppSettings(
        base_dir=base_dir,
        config_dir=_resolve_path_env("PROMPT_CONFIG_DIR", base_dir=base_dir, default=base_dir / "configs" / "types"),
        runtime_config_path=_resolve_path_env(
            "PROMPT_RUNTIME_CONFIG_PATH",
            base_dir=base_dir,
            default=base_dir / "configs" / "question_runtime.yaml",
        ),
        prompt_template_config_path=_resolve_path_env(
            "PROMPT_TEMPLATE_CONFIG_PATH",
            base_dir=base_dir,
            default=base_dir / "configs" / "prompt_templates.yaml",
        ),
        data_dir=data_dir,
        question_db_path=_resolve_path_env(
            "PROMPT_QUESTION_DB_PATH",
            base_dir=base_dir,
            default=data_dir / "question_workbench.db",
        ),
        security=SecuritySettings(
            enabled=security_enabled,
            api_token=api_token,
            rate_limit_per_minute=rate_limit_per_minute,
            trust_forwarded_headers=_read_bool_env("PROMPT_TRUST_FORWARDED_HEADERS", default=True),
            forwarded_for_index=max(0, int(os.getenv("PROMPT_FORWARDED_FOR_INDEX", "0"))),
            client_ip_header_priority=[
                item.strip().lower()
                for item in os.getenv(
                    "PROMPT_CLIENT_IP_HEADER_PRIORITY",
                    "cf-connecting-ip,true-client-ip,x-forwarded-for,x-real-ip",
                ).split(",")
                if item.strip()
            ],
        ),
        generation_queue=GenerationQueueSettings(
            max_concurrent=max(1, int(os.getenv("PROMPT_GENERATION_MAX_CONCURRENT", "2"))),
            max_waiting=max(0, int(os.getenv("PROMPT_GENERATION_MAX_QUEUE", "12"))),
            acquire_timeout_seconds=max(1, int(os.getenv("PROMPT_GENERATION_ACQUIRE_TIMEOUT_SECONDS", "240"))),
        ),
        shared_state=SharedStateSettings(
            backend=(os.getenv("PROMPT_SHARED_STATE_BACKEND", "sqlite") or "sqlite").strip().lower(),
        ),
        async_tasks=AsyncTaskSettings(
            enabled=_read_bool_env("PROMPT_ASYNC_QUEUE_ENABLED", default=True),
            worker_count=max(0, int(os.getenv("PROMPT_ASYNC_QUEUE_WORKERS", "1"))),
            poll_interval_seconds=max(0.1, float(os.getenv("PROMPT_ASYNC_QUEUE_POLL_INTERVAL_SECONDS", "1.0"))),
            lease_seconds=max(30, int(os.getenv("PROMPT_ASYNC_QUEUE_LEASE_SECONDS", "900"))),
            history_limit=max(10, int(os.getenv("PROMPT_ASYNC_QUEUE_HISTORY_LIMIT", "100"))),
        ),
    )

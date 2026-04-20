from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
import time

from app.core.dependencies import get_question_repository
from app.core.settings import get_settings


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    remaining: int
    backend: str


class InMemorySharedStateBackend:
    def __init__(self) -> None:
        self.name = "memory"
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow_rate_limit(self, *, key: str, limit: int, window_seconds: int = 60) -> RateLimitDecision:
        if limit <= 0:
            return RateLimitDecision(True, 0, 0, self.name)
        now = time.time()
        with self._lock:
            queue = self._hits[key]
            while queue and queue[0] <= now - window_seconds:
                queue.popleft()
            if len(queue) >= limit:
                retry_after = max(1, int(window_seconds - (now - queue[0])))
                return RateLimitDecision(False, retry_after, 0, self.name)
            queue.append(now)
            remaining = max(0, limit - len(queue))
        return RateLimitDecision(True, 0, remaining, self.name)

    def snapshot(self) -> dict[str, str]:
        return {"backend": self.name}


class SQLiteSharedStateBackend:
    def __init__(self) -> None:
        self.name = "sqlite"

    def allow_rate_limit(self, *, key: str, limit: int, window_seconds: int = 60) -> RateLimitDecision:
        allowed, retry_after, remaining = get_question_repository().allow_rate_limit(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )
        return RateLimitDecision(allowed, retry_after, remaining, self.name)

    def snapshot(self) -> dict[str, str]:
        return {"backend": self.name}


_BACKEND = None


def get_shared_state_backend():
    global _BACKEND
    if _BACKEND is None:
        backend_name = get_settings().shared_state.backend
        if backend_name == "memory":
            _BACKEND = InMemorySharedStateBackend()
        else:
            _BACKEND = SQLiteSharedStateBackend()
    return _BACKEND

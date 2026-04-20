from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_question_repository
from app.services.diagnostics import build_prompt_diagnostics
from app.services.question_repository import QuestionRepository


router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


@router.get("/dependencies")
def prompt_dependency_diagnostics() -> dict:
    return build_prompt_diagnostics()


@router.get("/runtime-events")
def runtime_events(
    limit: int = 100,
    severity: str | None = None,
    event_type: str | None = None,
    repository: QuestionRepository = Depends(get_question_repository),
) -> dict:
    items = repository.list_runtime_events(limit=limit, severity=severity, event_type=event_type)
    return {"count": len(items), "items": items}

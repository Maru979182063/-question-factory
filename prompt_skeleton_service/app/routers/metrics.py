from fastapi import APIRouter, Depends

from app.core.dependencies import get_question_repository
from app.schemas.evaluation import ReviewMetricsSummaryResponse
from app.services.question_repository import QuestionRepository

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/review-summary", response_model=ReviewMetricsSummaryResponse)
def get_review_summary(
    question_type: str | None = None,
    target_difficulty: str | None = None,
    document_genre: str | None = None,
    latest_action: str | None = None,
    repository: QuestionRepository = Depends(get_question_repository),
) -> ReviewMetricsSummaryResponse:
    return ReviewMetricsSummaryResponse.model_validate(
        repository.get_review_metrics_summary(
            question_type=question_type,
            target_difficulty=target_difficulty,
            document_genre=document_genre,
            latest_action=latest_action,
        )
    )


@router.get("/runtime-summary")
def get_runtime_summary(
    window_hours: int = 24,
    sample_limit: int = 500,
    repository: QuestionRepository = Depends(get_question_repository),
) -> dict:
    return repository.get_runtime_event_summary(window_hours=window_hours, limit=sample_limit)

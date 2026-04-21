from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import get_prompt_template_registry, get_question_repository, get_registry, get_runtime_registry
from app.schemas.distill import (
    DistillDatasetCreateRequest,
    DistillDatasetDetail,
    DistillDatasetListResponse,
    DistillPromotionRequest,
    DistillRunDetail,
    DistillRunPatchRequest,
    DistillRunReviewRequest,
    DistillSessionCreateRequest,
    DistillSessionDetail,
    DistillSessionListResponse,
    DistillTrialRequest,
)
from app.schemas.distillation import BehaviorDistillationExtractRequest, BehaviorDistillationPacket
from app.services.config_registry import ConfigRegistry
from app.services.distillation_behavior_service import DistillationBehaviorService
from app.services.distill_workbench import DistillWorkbenchService
from app.services.generation_gate import acquire_generation_slot
from app.services.prompt_orchestrator import PromptOrchestratorService
from app.services.prompt_template_registry import PromptTemplateRegistry
from app.services.question_generation import QuestionGenerationService
from app.services.question_repository import QuestionRepository
from app.services.runtime_registry import RuntimeConfigRegistry

router = APIRouter(prefix="/api/v1/distill", tags=["distill"])


def _build_workbench_service(
    *,
    registry: ConfigRegistry,
    runtime_registry: RuntimeConfigRegistry,
    prompt_template_registry: PromptTemplateRegistry,
    repository: QuestionRepository,
) -> DistillWorkbenchService:
    orchestrator = PromptOrchestratorService(registry)
    generation_service = QuestionGenerationService(
        orchestrator=orchestrator,
        runtime_config=runtime_registry.get(),
        repository=repository,
        prompt_template_registry=prompt_template_registry,
    )
    return DistillWorkbenchService(repository, generation_service)


@router.get("/datasets", response_model=DistillDatasetListResponse)
def list_distill_datasets(
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillDatasetListResponse:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    items = service.list_datasets(limit=limit, status=status)
    return DistillDatasetListResponse(count=len(items), items=items)


@router.post("/datasets", response_model=DistillDatasetDetail)
def create_distill_dataset(
    request: DistillDatasetCreateRequest,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillDatasetDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.create_dataset(request)


@router.get("/datasets/{dataset_id}", response_model=DistillDatasetDetail)
def get_distill_dataset(
    dataset_id: str,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillDatasetDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.get_dataset(dataset_id)


@router.get("/sessions", response_model=DistillSessionListResponse)
def list_distill_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillSessionListResponse:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    items = service.list_sessions(limit=limit, status=status)
    return DistillSessionListResponse(count=len(items), items=items)


@router.post("/sessions", response_model=DistillSessionDetail)
def create_distill_session(
    request: DistillSessionCreateRequest,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillSessionDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.create_session(request)


@router.get("/sessions/{session_id}", response_model=DistillSessionDetail)
def get_distill_session(
    session_id: str,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillSessionDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.get_session(session_id)


@router.get("/runs/{run_id}", response_model=DistillRunDetail)
def get_distill_run(
    run_id: str,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillRunDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.get_run(run_id)


@router.post("/sessions/{session_id}/trials", response_model=DistillRunDetail)
def run_distill_trial(
    session_id: str,
    request: DistillTrialRequest,
    http_request: Request,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillRunDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    with acquire_generation_slot() as gate_state:
        http_request.state.generation_gate = gate_state
        return service.run_trial(session_id, request)


@router.post("/runs/{run_id}/review", response_model=DistillRunDetail)
def review_distill_run(
    run_id: str,
    request: DistillRunReviewRequest,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillRunDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.review_run(run_id, request)


@router.post("/runs/{run_id}/patches", response_model=DistillRunDetail)
def add_distill_run_patch(
    run_id: str,
    request: DistillRunPatchRequest,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillRunDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.add_run_patch(run_id, request)


@router.post("/runs/{run_id}/promote", response_model=DistillRunDetail)
def promote_distill_run(
    run_id: str,
    request: DistillPromotionRequest,
    repository: QuestionRepository = Depends(get_question_repository),
    registry: ConfigRegistry = Depends(get_registry),
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
    prompt_template_registry: PromptTemplateRegistry = Depends(get_prompt_template_registry),
) -> DistillRunDetail:
    service = _build_workbench_service(
        registry=registry,
        runtime_registry=runtime_registry,
        prompt_template_registry=prompt_template_registry,
        repository=repository,
    )
    return service.promote_run(run_id, request)


@router.post("/behavior/packets", response_model=BehaviorDistillationPacket)
def build_behavior_distillation_packet(
    request: BehaviorDistillationExtractRequest,
    repository: QuestionRepository = Depends(get_question_repository),
) -> BehaviorDistillationPacket:
    service = DistillationBehaviorService(repository)
    return service.build_packet(request)

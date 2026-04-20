from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.services.material_pipeline_v2_service import MaterialPipelineV2Service
from app.schemas.material_pipeline_v2 import MaterialV2SearchRequest


router = APIRouter()


class MaterialV2PrecomputeRequest(BaseModel):
    material_ids: list[str] = Field(default_factory=list)
    article_ids: list[str] = Field(default_factory=list)
    status: str | None = None
    release_channel: str | None = None
    primary_only: bool = True
    limit: int | None = Field(default=None, ge=1, le=5000)


class MaterialV2ObservabilityRequest(BaseModel):
    business_family_id: str | None = None
    status: str | None = "promoted"
    release_channel: str | None = "stable"
    review_gate_mode: str = "stable_relaxed"
    shadow_child_family_ids: list[str] = Field(default_factory=list)
    shadow_selected_leaf_ids: list[str] = Field(default_factory=list)
    shadow_ready: bool | None = None
    fallback_to_business_card: bool | None = None
    shadow_sample_limit: int = Field(default=3, ge=1, le=20)
    limit: int = Field(default=10000, ge=1, le=50000)


@router.post("/materials/v2/search")
def search_materials_v2(payload: MaterialV2SearchRequest, db: Session = Depends(get_db)) -> dict:
    return MaterialPipelineV2Service(db).search(payload.model_dump(exclude_none=True))


@router.post("/materials/v2/shadow-search")
def search_materials_v2_shadow(payload: MaterialV2SearchRequest, db: Session = Depends(get_db)) -> dict:
    return MaterialPipelineV2Service(db).shadow_search(payload.model_dump(exclude_none=True))


@router.post("/materials/v2/precompute")
def precompute_materials_v2(payload: MaterialV2PrecomputeRequest, db: Session = Depends(get_db)) -> dict:
    return MaterialPipelineV2Service(db).precompute(payload.model_dump(exclude_none=True))


@router.post("/materials/v2/observability")
def observability_materials_v2(payload: MaterialV2ObservabilityRequest, db: Session = Depends(get_db)) -> dict:
    return MaterialPipelineV2Service(db).observability(payload.model_dump(exclude_none=True))

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.difficulty import (
    DifficultyBand,
    DifficultyFitResult,
    DifficultyProjection,
    DifficultyTargetProfile,
)


class PromptBuildRequest(BaseModel):
    question_type: str
    business_subtype: str | None = None
    pattern_id: str | None = None
    difficulty_target: DifficultyBand
    topic: str | None = None
    count: int = Field(default=1, ge=1, le=20)
    passage_style: str | None = None
    use_fewshot: bool = True
    fewshot_mode: str = "structure_only"
    type_slots: dict[str, Any] = Field(default_factory=dict)
    extra_constraints: dict[str, Any] | None = None


class SlotResolveRequest(BaseModel):
    question_type: str
    business_subtype: str | None = None
    pattern_id: str | None = None
    difficulty_target: DifficultyBand
    type_slots: dict[str, Any] = Field(default_factory=dict)


class TypeListItem(BaseModel):
    type_id: str
    display_name: str
    aliases: list[str]
    enabled_patterns: list[str]


class PatternSummary(BaseModel):
    pattern_id: str
    pattern_name: str
    enabled: bool
    match_rules: dict[str, Any] = Field(default_factory=dict)


class BusinessSubtypeSummary(BaseModel):
    subtype_id: str
    display_name: str
    description: str
    preferred_patterns: list[str] = Field(default_factory=list)


class TypeSchemaResponse(BaseModel):
    type_id: str
    display_name: str
    task_definition: str | None = None
    aliases: list[str]
    skeleton: dict[str, Any]
    slot_schema: dict[str, Any]
    default_slots: dict[str, Any]
    default_pattern_id: str | None = None
    available_patterns: list[PatternSummary]
    business_subtypes: list[BusinessSubtypeSummary] = Field(default_factory=list)
    fewshot_policy: dict[str, Any]


class PatternSelectionReason(BaseModel):
    requested_pattern_id: str | None = None
    selected_pattern_id: str
    selection_mode: Literal["direct", "auto_match", "configured_default"]
    matched_fields: list[str] = Field(default_factory=list)
    score: float
    fallback_used: bool = False
    fallback_reason: str | None = None


class ResolveResult(BaseModel):
    question_type: str
    business_subtype: str | None = None
    selected_pattern: str
    resolved_slots: dict[str, Any]
    skeleton: dict[str, Any]
    difficulty_projection: DifficultyProjection
    difficulty_target_profile: DifficultyTargetProfile
    difficulty_fit: DifficultyFitResult
    control_logic: dict[str, Any]
    generation_logic: dict[str, Any]
    pattern_selection_reason: PatternSelectionReason
    warnings: list[str] = Field(default_factory=list)


class PromptPackage(BaseModel):
    system_prompt: str
    user_prompt: str
    fewshot_examples: list[dict[str, Any]] = Field(default_factory=list)
    merged_prompt: str


class ReloadConfigResponse(BaseModel):
    loaded_types: int
    loaded_patterns: int
    warnings: list[str] = Field(default_factory=list)


DifficultyTarget = DifficultyBand
DifficultyFit = DifficultyFitResult

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


DifficultyBand = Literal["easy", "medium", "hard"]
DifficultyFitLabel = Literal["under_target", "on_target", "over_target", "gold_mismatch", "unknown"]


class DifficultyRange(BaseModel):
    min: float
    max: float

    @model_validator(mode="after")
    def validate_range(self) -> "DifficultyRange":
        if self.min > self.max:
            raise ValueError("difficulty range min cannot be greater than max")
        return self

    def midpoint(self) -> float:
        return round((self.min + self.max) / 2.0, 4)


class DifficultyTargetProfile(BaseModel):
    complexity: DifficultyRange
    ambiguity: DifficultyRange
    reasoning_depth: DifficultyRange
    distractor_similarity: DifficultyRange


class DifficultyDeviation(BaseModel):
    metric: str
    target_min: float
    target_max: float
    actual: float


class DifficultyTarget(BaseModel):
    question_type: str
    business_subtype: str | None = None
    target_difficulty: DifficultyBand
    family: str | None = None
    axis_targets: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class DifficultyProjection(BaseModel):
    target_difficulty: DifficultyBand
    projected_difficulty: DifficultyBand | None = None
    complexity: float
    ambiguity: float
    reasoning_depth: float
    distractor_similarity: float
    axis_projection: dict[str, float] = Field(default_factory=dict)
    prompt_contract: dict[str, Any] = Field(default_factory=dict)
    validator_contract: dict[str, Any] = Field(default_factory=dict)
    structural_changes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ActualDifficultyAssessment(BaseModel):
    target_difficulty: DifficultyBand
    actual_difficulty: DifficultyBand
    axis_scores: dict[str, float] = Field(default_factory=dict)
    metric_scores: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    structural_changes: list[str] = Field(default_factory=list)
    validator_status: str | None = None
    notes: list[str] = Field(default_factory=list)


class DifficultyFitResult(BaseModel):
    target_difficulty: DifficultyBand
    actual_difficulty: DifficultyBand | None = None
    gold_difficulty: DifficultyBand | None = None
    fit_result: DifficultyFitLabel = "unknown"
    axis_diff: dict[str, Any] = Field(default_factory=dict)
    structural_changes: list[str] = Field(default_factory=list)
    validator_status: str | None = None
    review_delta: dict[str, Any] = Field(default_factory=dict)
    promotion_recommendation: str | None = None
    in_range: bool = True
    deviations: list[DifficultyDeviation] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DifficultyCalibrationPatch(BaseModel):
    patch_target: Literal["question_card", "prompt_assets", "validator"]
    patch_scope: str
    title: str
    summary: str | None = None
    patch_candidate: dict[str, Any] = Field(default_factory=dict)
    target_difficulty: DifficultyBand
    actual_difficulty: DifficultyBand | None = None
    gold_difficulty: DifficultyBand | None = None
    fit_result: DifficultyFitLabel = "unknown"
    axis_diff: dict[str, Any] = Field(default_factory=dict)
    structural_changes: list[str] = Field(default_factory=list)
    validator_status: str | None = None
    review_delta: dict[str, Any] = Field(default_factory=dict)
    promotion_recommendation: str | None = None
    notes: list[str] = Field(default_factory=list)

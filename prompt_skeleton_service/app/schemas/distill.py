from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.question import QuestionGenerateRequest, QuestionGenerationItem, SourceQuestionPayload

DistillSessionMode = Literal["new_card", "card_tuning", "material_tuning"]
DistillDatasetSplit = Literal["train", "dev", "test"]
DistillDatasetSplitMode = Literal["manual", "hash"]
DistillHumanVerdict = Literal["approved", "rejected", "revise"]
DistillPromotionTarget = Literal[
    "question_card",
    "business_feature_card",
    "material_card",
    "signal_layer",
    "runtime_mapping",
    "prompt_assets",
    "validator_contract",
    "material_mapping",
    "leaf_pre_distill_report",
    "schema_gap_report",
]

_DISTILL_TARGET_ALIASES = {
    "prompt_config": "prompt_assets",
    "material_strategy": "material_mapping",
}


def normalize_distill_target(value: str) -> str:
    normalized = str(value or "").strip()
    return _DISTILL_TARGET_ALIASES.get(normalized, normalized)


def normalize_distill_targets(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    ordered: list[str] = []
    for value in values:
        normalized = normalize_distill_target(str(value))
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered


class DistillDatasetSampleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str | None = None
    sample_key: str | None = None
    title: str | None = None
    question_card_id: str | None = None
    truth_source_question: SourceQuestionPayload
    generation_request: QuestionGenerateRequest | None = None
    split: DistillDatasetSplit | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DistillDatasetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    question_card_id: str | None = None
    question_type: str | None = None
    business_subtype: str | None = None
    split_mode: DistillDatasetSplitMode = "manual"
    train_ratio: float = 0.6
    dev_ratio: float = 0.2
    test_ratio: float = 0.2
    tags: list[str] = Field(default_factory=list)
    samples: list[DistillDatasetSampleInput] = Field(default_factory=list)
    operator: str | None = None

    @model_validator(mode="after")
    def validate_split_strategy(self) -> "DistillDatasetCreateRequest":
        if not self.samples:
            raise ValueError("distill dataset requires at least one sample.")
        if self.split_mode == "manual":
            if any(sample.split is None for sample in self.samples):
                raise ValueError("manual split_mode requires every sample to provide split.")
        else:
            total = round(self.train_ratio + self.dev_ratio + self.test_ratio, 6)
            if total <= 0:
                raise ValueError("hash split ratios must sum to a positive value.")
        return self


class DistillDatasetSampleSummary(BaseModel):
    sample_id: str
    sample_key: str | None = None
    title: str | None = None
    split: DistillDatasetSplit
    question_card_id: str | None = None
    question_type: str | None = None
    business_subtype: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    truth_source_question: SourceQuestionPayload
    generation_request: QuestionGenerateRequest | None = None
    created_at: str
    updated_at: str


class DistillDatasetSummary(BaseModel):
    dataset_id: str
    title: str
    status: str
    description: str | None = None
    question_card_id: str | None = None
    question_type: str | None = None
    business_subtype: str | None = None
    split_mode: DistillDatasetSplitMode = "manual"
    sample_count: int = 0
    split_counts: dict[str, int] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class DistillDatasetDetail(DistillDatasetSummary):
    tags: list[str] = Field(default_factory=list)
    samples: list[DistillDatasetSampleSummary] = Field(default_factory=list)


class DistillDatasetListResponse(BaseModel):
    count: int
    items: list[DistillDatasetSummary] = Field(default_factory=list)


class DistillSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    mode: DistillSessionMode = "card_tuning"
    goal: str | None = None
    dataset_id: str | None = None
    question_card_id: str | None = None
    question_type: str | None = None
    business_subtype: str | None = None
    truth_source_question: SourceQuestionPayload | None = None
    baseline_request: QuestionGenerateRequest | None = None
    notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    operator: str | None = None


class DistillSessionSummary(BaseModel):
    session_id: str
    title: str
    mode: DistillSessionMode = "card_tuning"
    status: str
    goal: str | None = None
    dataset_id: str | None = None
    question_card_id: str | None = None
    question_type: str | None = None
    business_subtype: str | None = None
    run_count: int = 0
    latest_run_at: str | None = None
    created_at: str
    updated_at: str


class DistillTrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: QuestionGenerateRequest | None = None
    label: str | None = None
    hypothesis: str | None = None
    notes: list[str] = Field(default_factory=list)
    compare_to_truth: bool = True
    split: DistillDatasetSplit = "dev"
    sample_id: str | None = None
    sample_limit: int = Field(default=1, ge=1, le=50)
    operator: str | None = None


class DistillTruthFitSummary(BaseModel):
    truth_available: bool
    question_type_match: bool | None = None
    business_subtype_match: bool | None = None
    answer_match: bool | None = None
    stem_similarity: float | None = None
    analysis_similarity: float | None = None
    option_overlap: float | None = None
    material_similarity: float | None = None
    fit_band: Literal["high", "medium", "low", "unknown"] = "unknown"
    notes: list[str] = Field(default_factory=list)


class DistillRunReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: DistillHumanVerdict
    summary: str | None = None
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    allow_promote: bool = False
    promotion_targets: list[DistillPromotionTarget] = Field(default_factory=list)
    reviewer: str | None = None

    @field_validator("promotion_targets", mode="before")
    @classmethod
    def normalize_promotion_targets(cls, value: Any) -> list[str]:
        return normalize_distill_targets(value)

    @model_validator(mode="after")
    def validate_review(self) -> "DistillRunReviewRequest":
        has_comment = bool(str(self.summary or "").strip() or str(self.reason or "").strip())
        if self.verdict in {"rejected", "revise"} and not has_comment:
            raise ValueError("rejected/revise review requires summary or reason.")
        if self.allow_promote and self.verdict != "approved":
            raise ValueError("only approved review can allow promote.")
        if self.allow_promote and not self.promotion_targets:
            raise ValueError("allow_promote requires at least one promotion_target.")
        if self.promotion_targets and not self.allow_promote:
            raise ValueError("promotion_targets require allow_promote=true.")
        return self


class DistillRunReviewSummary(BaseModel):
    review_id: str
    run_id: str
    session_id: str
    verdict: DistillHumanVerdict
    summary: str | None = None
    reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    allow_promote: bool = False
    promotion_targets: list[DistillPromotionTarget] = Field(default_factory=list)
    reviewer: str | None = None
    created_at: str
    updated_at: str

    @field_validator("promotion_targets", mode="before")
    @classmethod
    def normalize_promotion_targets(cls, value: Any) -> list[str]:
        return normalize_distill_targets(value)


class DistillRunPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: DistillPromotionTarget
    title: str
    summary: str | None = None
    scope_key: str | None = None
    patch: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    author: str | None = None

    @field_validator("target", mode="before")
    @classmethod
    def normalize_target(cls, value: Any) -> str:
        return normalize_distill_target(str(value))

    @model_validator(mode="after")
    def validate_patch(self) -> "DistillRunPatchRequest":
        if not str(self.title or "").strip():
            raise ValueError("patch title is required.")
        has_summary = bool(str(self.summary or "").strip())
        if not self.patch and not has_summary:
            raise ValueError("patch requires patch payload or summary.")
        return self


class DistillRunPatchSummary(BaseModel):
    patch_id: str
    run_id: str
    session_id: str
    target: DistillPromotionTarget
    title: str
    summary: str | None = None
    scope_key: str | None = None
    patch: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    author: str | None = None
    created_at: str
    updated_at: str

    @field_validator("target", mode="before")
    @classmethod
    def normalize_target(cls, value: Any) -> str:
        return normalize_distill_target(str(value))


class DistillPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: list[DistillPromotionTarget] = Field(default_factory=list)
    summary: str | None = None
    notes: list[str] = Field(default_factory=list)
    promoter: str | None = None

    @field_validator("targets", mode="before")
    @classmethod
    def normalize_targets(cls, value: Any) -> list[str]:
        return normalize_distill_targets(value)

    @model_validator(mode="after")
    def validate_promotion(self) -> "DistillPromotionRequest":
        if not self.targets:
            raise ValueError("promotion requires at least one target.")
        return self


class DistillPromotionSummary(BaseModel):
    promotion_id: str
    run_id: str
    session_id: str
    status: str
    targets: list[DistillPromotionTarget] = Field(default_factory=list)
    summary: str | None = None
    notes: list[str] = Field(default_factory=list)
    promoter: str | None = None
    patch_ids: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
    created_at: str
    updated_at: str

    @field_validator("targets", mode="before")
    @classmethod
    def normalize_targets(cls, value: Any) -> list[str]:
        return normalize_distill_targets(value)


class DistillSampleRunResult(BaseModel):
    sample_id: str | None = None
    split: DistillDatasetSplit | None = None
    batch_id: str | None = None
    item_ids: list[str] = Field(default_factory=list)
    request_snapshot: dict[str, Any] = Field(default_factory=dict)
    fit_summary: DistillTruthFitSummary
    item_preview: QuestionGenerationItem | None = None
    error: dict[str, Any] | None = None


class DistillRunSummary(BaseModel):
    run_id: str
    session_id: str
    run_no: int
    status: str
    label: str | None = None
    hypothesis: str | None = None
    dataset_id: str | None = None
    split: DistillDatasetSplit | None = None
    sample_ids: list[str] = Field(default_factory=list)
    batch_id: str | None = None
    batch_ids: list[str] = Field(default_factory=list)
    item_ids: list[str] = Field(default_factory=list)
    fit_summary: DistillTruthFitSummary
    patch_count: int = 0
    promotion_count: int = 0
    review_count: int = 0
    latest_promotion: DistillPromotionSummary | None = None
    latest_review: DistillRunReviewSummary | None = None
    error: dict[str, Any] | None = None
    created_at: str
    updated_at: str


class DistillRunDetail(DistillRunSummary):
    request_snapshot: dict[str, Any] = Field(default_factory=dict)
    item_preview: QuestionGenerationItem | None = None
    sample_results: list[DistillSampleRunResult] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    patches: list[DistillRunPatchSummary] = Field(default_factory=list)
    reviews: list[DistillRunReviewSummary] = Field(default_factory=list)
    promotions: list[DistillPromotionSummary] = Field(default_factory=list)


class DistillSessionDetail(DistillSessionSummary):
    truth_source_question: SourceQuestionPayload | None = None
    baseline_request: QuestionGenerateRequest | None = None
    notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    runs: list[DistillRunSummary] = Field(default_factory=list)
    dataset: DistillDatasetSummary | None = None


class DistillSessionListResponse(BaseModel):
    count: int
    items: list[DistillSessionSummary] = Field(default_factory=list)

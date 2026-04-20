from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.question import SourceQuestionPayload


DistillationFamilyId = Literal["sentence_fill"]
PatchTarget = Literal["question_card", "prompt_assets", "validator_contract", "material_mapping"]
PatchPriority = Literal["high", "medium", "low"]
DifficultyDimension = Literal[
    "local_binding_complexity",
    "global_context_dependency",
    "distractor_similarity",
    "blank_function_ambiguity",
]
FitStatus = Literal["matched", "under_target", "over_target"]


def _default_patch_targets() -> list[PatchTarget]:
    return ["question_card", "prompt_assets", "validator_contract", "material_mapping"]


class SentenceFillConstraintSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blank_position: str | None = None
    function_type: str | None = None
    logic_relation: str | None = None
    context_dependency: str | None = None
    bidirectional_validation: str | None = None
    reference_dependency: str | None = None
    semantic_scope: str | None = None
    distractor_strength: str | None = None
    reference_anchor: str | None = None


class SentenceFillDifficultyObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_binding_complexity: float = Field(ge=0.0, le=1.0)
    global_context_dependency: float = Field(ge=0.0, le=1.0)
    distractor_similarity: float = Field(ge=0.0, le=1.0)
    blank_function_ambiguity: float = Field(ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class DistillationTruthSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str | None = None
    source_question: SourceQuestionPayload
    question_card_id: str | None = None
    canonical_constraints: SentenceFillConstraintSnapshot = Field(default_factory=SentenceFillConstraintSnapshot)
    target_difficulty: SentenceFillDifficultyObservation | None = None
    rationale_summary: str | None = None


class HistoricalThreadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    recurring_issues: list[str] = Field(default_factory=list)
    working_hypotheses: list[str] = Field(default_factory=list)
    rejected_hypotheses: list[str] = Field(default_factory=list)
    operator_notes: list[str] = Field(default_factory=list)


class DistillationMetricSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    value: float | str | bool
    note: str | None = None


class GeneratedQuestionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stem: str | None = None
    options: dict[str, str] = Field(default_factory=dict)
    answer: str | None = None
    analysis: str | None = None


class DistillationTestResultSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["pass", "mixed", "fail"]
    observed_constraints: SentenceFillConstraintSnapshot = Field(default_factory=SentenceFillConstraintSnapshot)
    actual_difficulty: SentenceFillDifficultyObservation | None = None
    generated_question: GeneratedQuestionSnapshot | None = None
    fit_signals: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    metrics: list[DistillationMetricSnapshot] = Field(default_factory=list)
    summary: str | None = None


class DistillationRuntimeState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_card_id: str | None = None
    question_card_snapshot: dict[str, Any] = Field(default_factory=dict)
    prompt_asset_snapshot: dict[str, Any] = Field(default_factory=dict)
    validator_contract_snapshot: dict[str, Any] = Field(default_factory=dict)
    material_mapping_snapshot: dict[str, Any] = Field(default_factory=dict)


class DistillationInputPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    packet_id: str = Field(default_factory=lambda: f"distill_input_{uuid4().hex[:12]}")
    round_id: str | None = None
    family_id: DistillationFamilyId = "sentence_fill"
    truth_sample: DistillationTruthSample
    historical_thread_summary: HistoricalThreadSummary
    test_result_snapshot: DistillationTestResultSnapshot
    runtime_state: DistillationRuntimeState = Field(default_factory=DistillationRuntimeState)
    requested_patch_targets: list[PatchTarget] = Field(default_factory=_default_patch_targets)
    notes: list[str] = Field(default_factory=list)

    @field_validator("requested_patch_targets")
    @classmethod
    def dedupe_patch_targets(cls, value: list[PatchTarget]) -> list[PatchTarget]:
        ordered: list[PatchTarget] = []
        for item in value:
            if item not in ordered:
                ordered.append(item)
        return ordered or _default_patch_targets()


class DistillationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DifficultyFitEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: DifficultyDimension
    target: float = Field(ge=0.0, le=1.0)
    actual: float = Field(ge=0.0, le=1.0)
    delta: float = Field(ge=-1.0, le=1.0)
    fit_status: FitStatus
    note: str | None = None


class CandidatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch_id: str
    target: PatchTarget
    dimension: DifficultyDimension
    direction: Literal["raise", "lower"]
    priority: PatchPriority
    summary: str
    rationale: str
    proposed_change: dict[str, Any] = Field(default_factory=dict)
    expected_effect: str
    evidence: list[DistillationEvidence] = Field(default_factory=list)


class AgentAdjustmentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_label: str
    selected_patch_ids: list[str] = Field(default_factory=list)
    instruction_summary: str
    evaluation_focus: list[DifficultyDimension] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)


class DistillationNormalizedView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    truth_constraints: SentenceFillConstraintSnapshot
    observed_constraints: SentenceFillConstraintSnapshot
    thread_focus: list[str] = Field(default_factory=list)
    failure_focus: list[str] = Field(default_factory=list)
    runtime_focus: list[str] = Field(default_factory=list)


class DistillationResultPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str = Field(default_factory=lambda: f"distill_result_{uuid4().hex[:12]}")
    packet_id: str
    family_id: DistillationFamilyId
    normalized_view: DistillationNormalizedView
    target_difficulty: SentenceFillDifficultyObservation
    actual_difficulty: SentenceFillDifficultyObservation
    difficulty_fit: list[DifficultyFitEntry] = Field(default_factory=list)
    overall_fit_status: Literal["good", "adjust", "poor"]
    candidate_patches: list[CandidatePatch] = Field(default_factory=list)
    selected_agent_adjustment: AgentAdjustmentPlan
    structured_summary: dict[str, Any] = Field(default_factory=dict)


class PromotionPatchBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: PatchTarget
    patches: list[CandidatePatch] = Field(default_factory=list)


class DistillationPromotionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    promotion_id: str = Field(default_factory=lambda: f"distill_promotion_{uuid4().hex[:12]}")
    packet_id: str
    result_id: str
    family_id: DistillationFamilyId
    bundle_mode: Literal["candidate_only"] = "candidate_only"
    patch_bundles: list[PromotionPatchBundle] = Field(default_factory=list)
    selected_agent_adjustment: AgentAdjustmentPlan
    handoff_notes: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class PatchDiffEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch_id: str
    target: PatchTarget
    current_excerpt: dict[str, Any] = Field(default_factory=dict)
    proposed_excerpt: dict[str, Any] = Field(default_factory=dict)
    semantic_change: str
    risk_note: str | None = None


class DistillationDiffReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(default_factory=lambda: f"distill_diff_{uuid4().hex[:12]}")
    packet_id: str
    result_id: str
    family_id: DistillationFamilyId
    overall_fit_status: Literal["good", "adjust", "poor"]
    difficulty_diffs: list[DifficultyFitEntry] = Field(default_factory=list)
    patch_diffs: list[PatchDiffEntry] = Field(default_factory=list)
    test_report: dict[str, Any] = Field(default_factory=dict)
    recommended_next_step: str

    @model_validator(mode="after")
    def require_structured_diff(self) -> "DistillationDiffReport":
        if not self.difficulty_diffs:
            raise ValueError("difficulty_diffs cannot be empty")
        return self

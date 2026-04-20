from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from app.core.exceptions import DomainError
from app.schemas.distill import (
    DistillDatasetCreateRequest,
    DistillDatasetDetail,
    DistillDatasetSampleSummary,
    DistillDatasetSummary,
    DistillPromotionRequest,
    DistillPromotionSummary,
    DistillRunDetail,
    DistillRunPatchRequest,
    DistillRunReviewRequest,
    DistillRunSummary,
    DistillSampleRunResult,
    DistillSessionCreateRequest,
    DistillSessionDetail,
    DistillSessionSummary,
    DistillTrialRequest,
    DistillTruthFitSummary,
)
from app.schemas.question import QuestionGenerateRequest, QuestionGenerationItem, SourceQuestionPayload
from app.services.question_repository import QuestionRepository


class _GenerationRunner(Protocol):
    def generate(self, request: QuestionGenerateRequest) -> dict[str, Any]:
        ...


class DistillWorkbenchService:
    def __init__(self, repository: QuestionRepository, generation_runner: _GenerationRunner) -> None:
        self.repository = repository
        self.generation_runner = generation_runner

    def create_dataset(self, request: DistillDatasetCreateRequest) -> DistillDatasetDetail:
        now = self._utc_now()
        dataset_id = str(uuid4())
        samples = self._materialize_dataset_samples(dataset_id=dataset_id, request=request, now=now)
        payload = {
            "dataset_id": dataset_id,
            "title": request.title,
            "status": "active",
            "description": request.description,
            "question_card_id": request.question_card_id,
            "question_type": request.question_type,
            "business_subtype": request.business_subtype,
            "split_mode": request.split_mode,
            "tags": list(request.tags),
            "created_at": now,
            "updated_at": now,
        }
        self.repository.save_distill_dataset(dataset_id, payload)
        self.repository.save_distill_dataset_samples(dataset_id, samples)
        return self.get_dataset(dataset_id)

    def list_datasets(self, *, limit: int = 100, status: str | None = None) -> list[DistillDatasetSummary]:
        return [DistillDatasetSummary.model_validate(item) for item in self.repository.list_distill_datasets(limit=limit, status=status)]

    def get_dataset(self, dataset_id: str) -> DistillDatasetDetail:
        payload = self.repository.get_distill_dataset(dataset_id)
        if payload is None:
            raise DomainError("Distill dataset not found.", status_code=404, details={"dataset_id": dataset_id})
        return DistillDatasetDetail.model_validate(payload)

    def create_session(self, request: DistillSessionCreateRequest) -> DistillSessionDetail:
        now = self._utc_now()
        session_id = str(uuid4())
        dataset = self.get_dataset(request.dataset_id) if request.dataset_id else None
        self._validate_session_request(request=request, dataset=dataset)

        baseline_question_type = self._question_type_from_request(request.baseline_request)
        payload = {
            "session_id": session_id,
            "title": request.title,
            "mode": request.mode,
            "status": "active",
            "goal": request.goal,
            "dataset_id": request.dataset_id,
            "question_card_id": request.question_card_id
            or (request.baseline_request.question_card_id if request.baseline_request else None)
            or (dataset.question_card_id if dataset else None),
            "question_type": request.question_type or baseline_question_type or (dataset.question_type if dataset else None),
            "business_subtype": request.business_subtype
            or (request.baseline_request.business_subtype if request.baseline_request else None)
            or (dataset.business_subtype if dataset else None),
            "truth_source_question": request.truth_source_question.model_dump() if request.truth_source_question else None,
            "baseline_request": request.baseline_request.model_dump(by_alias=True) if request.baseline_request else None,
            "notes": list(request.notes),
            "tags": list(request.tags),
            "operator": request.operator,
            "created_at": now,
            "updated_at": now,
        }
        self.repository.save_distill_session(session_id, payload)
        return self.get_session(session_id)

    def list_sessions(self, *, limit: int = 100, status: str | None = None) -> list[DistillSessionSummary]:
        return [DistillSessionSummary.model_validate(item) for item in self.repository.list_distill_sessions(limit=limit, status=status)]

    def get_session(self, session_id: str) -> DistillSessionDetail:
        payload = self.repository.get_distill_session(session_id)
        if payload is None:
            raise DomainError("Distill session not found.", status_code=404, details={"session_id": session_id})
        runs = [DistillRunSummary.model_validate(item) for item in self.repository.list_distill_runs(session_id, limit=200)]
        payload["runs"] = [run.model_dump() for run in runs]
        dataset_id = payload.get("dataset_id")
        payload["dataset"] = self.get_dataset(dataset_id).model_dump() if dataset_id else None
        return DistillSessionDetail.model_validate(payload)

    def get_run(self, run_id: str) -> DistillRunDetail:
        payload = self.repository.get_distill_run(run_id)
        if payload is None:
            raise DomainError("Distill run not found.", status_code=404, details={"run_id": run_id})
        payload["patches"] = self.repository.list_distill_run_patches(run_id, limit=200)
        payload["reviews"] = self.repository.list_distill_run_reviews(run_id, limit=200)
        payload["promotions"] = self.repository.list_distill_promotions(run_id, limit=200)
        return DistillRunDetail.model_validate(payload)

    def run_trial(self, session_id: str, request: DistillTrialRequest) -> DistillRunDetail:
        session = self.get_session(session_id)
        samples = self._resolve_trial_samples(session=session, request=request)
        if not samples:
            raise DomainError(
                "Distill trial resolved no samples.",
                status_code=422,
                details={"session_id": session_id, "split": request.split, "sample_id": request.sample_id},
            )

        run_no = session.run_count + 1
        run_id = str(uuid4())
        started_at = self._utc_now()
        sample_results: list[DistillSampleRunResult] = []
        batch_ids: list[str] = []
        item_ids: list[str] = []
        sample_ids: list[str] = []
        first_item_preview: QuestionGenerationItem | None = None

        for sample in samples:
            sample_id = sample.get("sample_id")
            if sample_id:
                sample_ids.append(str(sample_id))
            effective_request = self._resolve_effective_request(session=session, request=request, sample=sample)
            try:
                batch_payload = self.generation_runner.generate(effective_request)
                item_preview = self._safe_item_preview(batch_payload.get("items") or [])
                fit_summary = self._build_truth_fit_summary(
                    truth_source_question=self._sample_truth_source_question(sample),
                    expected_question_type=session.question_type or sample.get("question_type"),
                    expected_business_subtype=session.business_subtype or sample.get("business_subtype"),
                    item=item_preview,
                    compare_to_truth=request.compare_to_truth,
                )
                result_item_ids = [
                    str(item.get("item_id") or "")
                    for item in (batch_payload.get("items") or [])
                    if str(item.get("item_id") or "").strip()
                ]
                result_batch_id = batch_payload.get("batch_id")
                if result_batch_id:
                    batch_ids.append(str(result_batch_id))
                item_ids.extend(result_item_ids)
                if first_item_preview is None and item_preview is not None:
                    first_item_preview = item_preview
                sample_results.append(
                    DistillSampleRunResult(
                        sample_id=str(sample_id) if sample_id else None,
                        split=sample.get("split"),
                        batch_id=str(result_batch_id) if result_batch_id else None,
                        item_ids=result_item_ids,
                        request_snapshot=effective_request.model_dump(by_alias=True),
                        fit_summary=fit_summary,
                        item_preview=item_preview,
                        error=None,
                    )
                )
            except DomainError as exc:
                sample_results.append(
                    DistillSampleRunResult(
                        sample_id=str(sample_id) if sample_id else None,
                        split=sample.get("split"),
                        batch_id=None,
                        item_ids=[],
                        request_snapshot=effective_request.model_dump(by_alias=True),
                        fit_summary=self._empty_fit_summary(
                            truth_available=bool(self._sample_truth_source_question(sample))
                        ),
                        item_preview=None,
                        error={
                            "message": str(exc),
                            "status_code": exc.status_code,
                            "details": exc.details,
                        },
                    )
                )

        fit_summary = self._aggregate_fit_summaries([result.fit_summary for result in sample_results])
        success_count = sum(1 for result in sample_results if result.error is None)
        if success_count == len(sample_results):
            status = "completed"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial_failed"

        payload = {
            "run_id": run_id,
            "session_id": session_id,
            "run_no": run_no,
            "status": status,
            "label": request.label,
            "hypothesis": request.hypothesis,
            "dataset_id": session.dataset_id,
            "split": request.split if session.dataset_id else None,
            "sample_ids": sample_ids,
            "batch_id": batch_ids[0] if batch_ids else None,
            "batch_ids": batch_ids,
            "item_ids": item_ids,
            "fit_summary": fit_summary.model_dump(),
            "request_snapshot": self._trial_request_snapshot(session=session, request=request),
            "item_preview": first_item_preview.model_dump() if first_item_preview else None,
            "sample_results": [result.model_dump() for result in sample_results],
            "notes": list(request.notes),
            "error": None if success_count > 0 else self._first_error_payload(sample_results),
            "created_at": started_at,
            "updated_at": self._utc_now(),
        }
        self.repository.save_distill_run(run_id, payload)
        return DistillRunDetail.model_validate(payload)

    def review_run(self, run_id: str, request: DistillRunReviewRequest) -> DistillRunDetail:
        run = self.get_run(run_id)
        if request.verdict == "approved" and run.status != "completed":
            raise DomainError(
                "Only completed distill runs can be approved.",
                status_code=422,
                details={"run_id": run_id, "status": run.status},
            )

        now = self._utc_now()
        review_id = str(uuid4())
        payload = {
            "review_id": review_id,
            "run_id": run.run_id,
            "session_id": run.session_id,
            "verdict": request.verdict,
            "summary": request.summary,
            "reason": request.reason,
            "notes": list(request.notes),
            "allow_promote": request.allow_promote,
            "promotion_targets": list(request.promotion_targets),
            "reviewer": request.reviewer,
            "created_at": now,
            "updated_at": now,
        }
        self.repository.save_distill_run_review(review_id, payload)
        return self.get_run(run_id)

    def add_run_patch(self, run_id: str, request: DistillRunPatchRequest) -> DistillRunDetail:
        run = self.get_run(run_id)
        now = self._utc_now()
        patch_id = str(uuid4())
        payload = {
            "patch_id": patch_id,
            "run_id": run.run_id,
            "session_id": run.session_id,
            "target": request.target,
            "title": request.title,
            "summary": request.summary,
            "scope_key": request.scope_key,
            "patch": dict(request.patch),
            "notes": list(request.notes),
            "author": request.author,
            "created_at": now,
            "updated_at": now,
        }
        self.repository.save_distill_run_patch(patch_id, payload)
        return self.get_run(run_id)

    def promote_run(self, run_id: str, request: DistillPromotionRequest) -> DistillRunDetail:
        run = self.get_run(run_id)
        latest_review = run.latest_review
        if latest_review is None:
            raise DomainError(
                "Distill run requires human review before promotion.",
                status_code=422,
                details={"run_id": run_id},
            )
        if latest_review.verdict != "approved" or not latest_review.allow_promote:
            raise DomainError(
                "Only approved review with allow_promote can promote run.",
                status_code=422,
                details={
                    "run_id": run_id,
                    "latest_verdict": latest_review.verdict,
                    "allow_promote": latest_review.allow_promote,
                },
            )

        allowed_targets = set(latest_review.promotion_targets)
        requested_targets = set(request.targets)
        if not requested_targets.issubset(allowed_targets):
            raise DomainError(
                "Promotion targets must be approved by latest review.",
                status_code=422,
                details={
                    "run_id": run_id,
                    "requested_targets": sorted(requested_targets),
                    "allowed_targets": sorted(allowed_targets),
                },
            )

        matching_patches = [patch for patch in run.patches if patch.target in requested_targets]
        patch_targets = {patch.target for patch in matching_patches}
        missing_targets = sorted(requested_targets - patch_targets)
        if missing_targets:
            raise DomainError(
                "Promotion requires explicit patches for every target.",
                status_code=422,
                details={
                    "run_id": run_id,
                    "missing_targets": missing_targets,
                },
            )

        now = self._utc_now()
        promotion_id = str(uuid4())
        bundle = self._build_promotion_bundle(
            promotion_id=promotion_id,
            run=run,
            review=latest_review.model_dump(),
            targets=sorted(requested_targets),
            patches=[patch.model_dump() for patch in matching_patches],
            summary=request.summary,
            notes=list(request.notes),
            promoter=request.promoter,
            created_at=now,
        )
        artifact_path = self._write_promotion_bundle(promotion_id, bundle)
        payload = {
            "promotion_id": promotion_id,
            "run_id": run.run_id,
            "session_id": run.session_id,
            "status": "ready",
            "targets": sorted(requested_targets),
            "summary": request.summary,
            "notes": list(request.notes),
            "promoter": request.promoter,
            "patch_ids": [patch["patch_id"] for patch in bundle["patches"]],
            "artifact_path": str(artifact_path),
            "created_at": now,
            "updated_at": now,
        }
        self.repository.save_distill_promotion(promotion_id, payload)
        return self.get_run(run_id)

    def _validate_session_request(
        self,
        *,
        request: DistillSessionCreateRequest,
        dataset: DistillDatasetDetail | None,
    ) -> None:
        if request.mode == "new_card" and request.baseline_request is None:
            raise DomainError(
                "new_card mode requires baseline_request.",
                status_code=422,
                details={"mode": request.mode},
            )
        if request.mode in {"card_tuning", "material_tuning"} and request.dataset_id is None and request.truth_source_question is None:
            raise DomainError(
                "card_tuning/material_tuning mode requires dataset_id or truth_source_question.",
                status_code=422,
                details={"mode": request.mode},
            )
        if dataset is not None and request.question_type and dataset.question_type and request.question_type != dataset.question_type:
            raise DomainError(
                "session question_type conflicts with dataset question_type.",
                status_code=422,
                details={
                    "session_question_type": request.question_type,
                    "dataset_question_type": dataset.question_type,
                },
            )

    def _build_promotion_bundle(
        self,
        *,
        promotion_id: str,
        run: DistillRunDetail,
        review: dict[str, Any],
        targets: list[str],
        patches: list[dict[str, Any]],
        summary: str | None,
        notes: list[str],
        promoter: str | None,
        created_at: str,
    ) -> dict[str, Any]:
        return {
            "promotion_id": promotion_id,
            "run_id": run.run_id,
            "session_id": run.session_id,
            "status": "ready",
            "targets": targets,
            "summary": summary,
            "notes": notes,
            "promoter": promoter,
            "created_at": created_at,
            "review": review,
            "run_snapshot": {
                "run_id": run.run_id,
                "run_no": run.run_no,
                "status": run.status,
                "label": run.label,
                "hypothesis": run.hypothesis,
                "dataset_id": run.dataset_id,
                "split": run.split,
                "fit_summary": run.fit_summary.model_dump(),
                "request_snapshot": run.request_snapshot,
                "item_ids": list(run.item_ids),
                "sample_ids": list(run.sample_ids),
            },
            "patches": patches,
        }

    def _write_promotion_bundle(self, promotion_id: str, bundle: dict[str, Any]) -> Path:
        output_dir = self.repository.db_path.parent / "distill_promotions"
        output_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_dir / f"{promotion_id}.json"
        artifact_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        return artifact_path

    def _materialize_dataset_samples(
        self,
        *,
        dataset_id: str,
        request: DistillDatasetCreateRequest,
        now: str,
    ) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        for index, sample in enumerate(request.samples, start=1):
            sample_id = str(sample.sample_id or uuid4())
            split = sample.split if request.split_mode == "manual" else self._hash_split(
                sample_key=self._sample_hash_key(sample=sample, fallback_index=index),
                train_ratio=request.train_ratio,
                dev_ratio=request.dev_ratio,
                test_ratio=request.test_ratio,
            )
            generation_request = sample.generation_request
            question_type = self._question_type_from_request(generation_request) or request.question_type
            business_subtype = (
                generation_request.business_subtype if generation_request and generation_request.business_subtype else request.business_subtype
            )
            payload = {
                "sample_id": sample_id,
                "dataset_id": dataset_id,
                "sample_key": sample.sample_key,
                "title": sample.title,
                "split": split,
                "question_card_id": sample.question_card_id or request.question_card_id,
                "question_type": question_type,
                "business_subtype": business_subtype,
                "truth_source_question": sample.truth_source_question.model_dump(),
                "generation_request": generation_request.model_dump(by_alias=True) if generation_request else None,
                "tags": list(sample.tags),
                "metadata": dict(sample.metadata),
                "created_at": now,
                "updated_at": now,
            }
            samples.append(payload)
        return samples

    def _resolve_trial_samples(
        self,
        *,
        session: DistillSessionDetail,
        request: DistillTrialRequest,
    ) -> list[dict[str, Any]]:
        if session.dataset_id:
            samples = self.repository.list_distill_dataset_samples(
                session.dataset_id,
                split=(None if request.sample_id else request.split),
                limit=max(request.sample_limit, 1000 if request.sample_id else request.sample_limit),
            )
            if request.sample_id:
                filtered = [sample for sample in samples if str(sample.get("sample_id") or "") == str(request.sample_id)]
                if not filtered:
                    raise DomainError(
                        "Requested distill sample_id was not found in dataset.",
                        status_code=404,
                        details={"dataset_id": session.dataset_id, "sample_id": request.sample_id},
                    )
                return filtered[:1]
            return samples[: request.sample_limit]

        sample = {
            "sample_id": None,
            "split": request.split,
            "question_card_id": session.question_card_id,
            "question_type": session.question_type,
            "business_subtype": session.business_subtype,
            "truth_source_question": session.truth_source_question.model_dump() if session.truth_source_question else None,
            "generation_request": session.baseline_request.model_dump(by_alias=True) if session.baseline_request else None,
            "title": session.title,
            "metadata": {"origin": "session_inline_truth"},
        }
        return [sample]

    def _resolve_effective_request(
        self,
        *,
        session: DistillSessionDetail,
        request: DistillTrialRequest,
        sample: dict[str, Any],
    ) -> QuestionGenerateRequest:
        if request.request is not None:
            effective = request.request
        elif sample.get("generation_request") is not None:
            effective = QuestionGenerateRequest.model_validate(sample.get("generation_request"))
        elif session.baseline_request is not None:
            effective = session.baseline_request
        else:
            raise DomainError(
                "Distill trial requires request, sample.generation_request, or session.baseline_request.",
                status_code=422,
                details={"session_id": session.session_id, "sample_id": sample.get("sample_id")},
            )

        update_payload: dict[str, Any] = {}
        if not effective.question_card_id and (sample.get("question_card_id") or session.question_card_id):
            update_payload["question_card_id"] = sample.get("question_card_id") or session.question_card_id
        if effective.source_question is None and self._sample_truth_source_question(sample) is not None:
            update_payload["source_question"] = self._sample_truth_source_question(sample)
        return effective.model_copy(update=update_payload) if update_payload else effective

    def _build_truth_fit_summary(
        self,
        *,
        truth_source_question: SourceQuestionPayload | None,
        expected_question_type: str | None,
        expected_business_subtype: str | None,
        item: QuestionGenerationItem | None,
        compare_to_truth: bool,
    ) -> DistillTruthFitSummary:
        if truth_source_question is None or not compare_to_truth or item is None:
            return self._empty_fit_summary(truth_available=bool(truth_source_question))

        generated_question = item.generated_question or {}
        material_text = item.material_text or (item.material_selection.text if item.material_selection else "") or ""
        truth_options = truth_source_question.options or {}
        generated_options = generated_question.options or {}

        answer_match = None
        if truth_source_question.answer:
            answer_match = str(truth_source_question.answer).strip().upper() == str(generated_question.answer or "").strip().upper()

        stem_similarity = self._similarity(truth_source_question.stem, generated_question.stem or "")
        analysis_similarity = self._similarity(truth_source_question.analysis or "", generated_question.analysis or "")
        material_similarity = self._similarity(truth_source_question.passage or "", material_text)
        option_overlap = self._option_overlap(truth_options, generated_options)

        notes: list[str] = []
        if answer_match is False:
            notes.append("truth_answer_not_matched")
        if stem_similarity is not None and stem_similarity < 0.45:
            notes.append("stem_style_gap_visible")
        if option_overlap is not None and option_overlap < 0.35:
            notes.append("option_distribution_far_from_truth")
        if material_similarity is not None and material_similarity < 0.4:
            notes.append("material_alignment_looks_weak")

        signals = [
            score
            for score in (stem_similarity, analysis_similarity, option_overlap, material_similarity)
            if score is not None
        ]
        if answer_match is True:
            signals.append(1.0)
        elif answer_match is False:
            signals.append(0.0)
        avg_signal = sum(signals) / len(signals) if signals else None
        fit_band = self._fit_band_from_score(avg_signal)

        return DistillTruthFitSummary(
            truth_available=True,
            question_type_match=(item.question_type == expected_question_type if expected_question_type else None),
            business_subtype_match=(item.business_subtype == expected_business_subtype if expected_business_subtype is not None else None),
            answer_match=answer_match,
            stem_similarity=stem_similarity,
            analysis_similarity=analysis_similarity,
            option_overlap=option_overlap,
            material_similarity=material_similarity,
            fit_band=fit_band,
            notes=notes,
        )

    def _aggregate_fit_summaries(self, summaries: list[DistillTruthFitSummary]) -> DistillTruthFitSummary:
        if not summaries:
            return self._empty_fit_summary(truth_available=False)

        truth_available = any(summary.truth_available for summary in summaries)
        question_type_match = self._collapse_bool([summary.question_type_match for summary in summaries])
        business_subtype_match = self._collapse_bool([summary.business_subtype_match for summary in summaries])
        answer_match = self._collapse_bool([summary.answer_match for summary in summaries])
        stem_similarity = self._average_optional([summary.stem_similarity for summary in summaries])
        analysis_similarity = self._average_optional([summary.analysis_similarity for summary in summaries])
        option_overlap = self._average_optional([summary.option_overlap for summary in summaries])
        material_similarity = self._average_optional([summary.material_similarity for summary in summaries])
        fit_score = self._average_optional([stem_similarity, analysis_similarity, option_overlap, material_similarity])
        notes = sorted({note for summary in summaries for note in summary.notes})

        return DistillTruthFitSummary(
            truth_available=truth_available,
            question_type_match=question_type_match,
            business_subtype_match=business_subtype_match,
            answer_match=answer_match,
            stem_similarity=stem_similarity,
            analysis_similarity=analysis_similarity,
            option_overlap=option_overlap,
            material_similarity=material_similarity,
            fit_band=self._fit_band_from_score(fit_score),
            notes=notes,
        )

    @staticmethod
    def _safe_item_preview(items: list[dict[str, Any]]) -> QuestionGenerationItem | None:
        if not items:
            return None
        try:
            return QuestionGenerationItem.model_validate(items[0])
        except Exception:
            return None

    @staticmethod
    def _empty_fit_summary(*, truth_available: bool) -> DistillTruthFitSummary:
        return DistillTruthFitSummary(truth_available=truth_available, fit_band="unknown", notes=[])

    @staticmethod
    def _question_type_from_request(request: QuestionGenerateRequest | None) -> str | None:
        if request is None:
            return None
        focus = str(request.question_focus or "").strip()
        if focus == "sentence_fill":
            return "sentence_fill"
        if focus == "sentence_order":
            return "sentence_order"
        if focus in {"center_understanding", "main_idea"}:
            return "main_idea"
        return None

    @staticmethod
    def _sample_truth_source_question(sample: dict[str, Any]) -> SourceQuestionPayload | None:
        payload = sample.get("truth_source_question")
        if payload is None:
            return None
        return SourceQuestionPayload.model_validate(payload)

    @staticmethod
    def _sample_hash_key(*, sample, fallback_index: int) -> str:
        truth = sample.truth_source_question
        base = "|".join(
            [
                sample.sample_key or "",
                truth.stem or "",
                truth.passage or "",
                str(fallback_index),
            ]
        )
        return base

    @staticmethod
    def _hash_split(*, sample_key: str, train_ratio: float, dev_ratio: float, test_ratio: float) -> str:
        normalized_total = train_ratio + dev_ratio + test_ratio
        if normalized_total <= 0:
            return "train"
        train_cutoff = train_ratio / normalized_total
        dev_cutoff = (train_ratio + dev_ratio) / normalized_total
        digest = hashlib.sha256(sample_key.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) / 0xFFFFFFFF
        if bucket < train_cutoff:
            return "train"
        if bucket < dev_cutoff:
            return "dev"
        return "test"

    @staticmethod
    def _trial_request_snapshot(
        *,
        session: DistillSessionDetail,
        request: DistillTrialRequest,
    ) -> dict[str, Any]:
        return {
            "mode": session.mode,
            "dataset_id": session.dataset_id,
            "split": request.split if session.dataset_id else None,
            "sample_id": request.sample_id,
            "sample_limit": request.sample_limit,
            "explicit_request": request.request.model_dump(by_alias=True) if request.request else None,
        }

    @staticmethod
    def _first_error_payload(sample_results: list[DistillSampleRunResult]) -> dict[str, Any] | None:
        for result in sample_results:
            if result.error:
                return result.error
        return None

    @staticmethod
    def _average_optional(values: list[float | None]) -> float | None:
        valid = [float(value) for value in values if value is not None]
        if not valid:
            return None
        return round(sum(valid) / len(valid), 4)

    @staticmethod
    def _collapse_bool(values: list[bool | None]) -> bool | None:
        filtered = [value for value in values if value is not None]
        if not filtered:
            return None
        return all(filtered)

    @staticmethod
    def _fit_band_from_score(score: float | None) -> str:
        if score is None:
            return "unknown"
        if score >= 0.75:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _similarity(left: str, right: str) -> float | None:
        normalized_left = DistillWorkbenchService._normalize_text(left)
        normalized_right = DistillWorkbenchService._normalize_text(right)
        if not normalized_left or not normalized_right:
            return None
        return round(SequenceMatcher(None, normalized_left, normalized_right).ratio(), 4)

    @staticmethod
    def _option_overlap(left: dict[str, str], right: dict[str, str]) -> float | None:
        left_values = [DistillWorkbenchService._normalize_text(value) for _, value in sorted(left.items()) if DistillWorkbenchService._normalize_text(value)]
        right_values = [DistillWorkbenchService._normalize_text(value) for _, value in sorted(right.items()) if DistillWorkbenchService._normalize_text(value)]
        if not left_values or not right_values:
            return None
        scores: list[float] = []
        for candidate in left_values:
            scores.append(max(SequenceMatcher(None, candidate, target).ratio() for target in right_values))
        return round(sum(scores) / len(scores), 4) if scores else None

    @staticmethod
    def _normalize_text(text: str) -> str:
        return "".join(str(text or "").split()).strip()

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

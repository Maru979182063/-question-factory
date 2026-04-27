from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.core.exceptions import DomainError
from app.schemas.distill import (
    DistillDatasetCreateRequest,
    DistillDatasetSampleInput,
    DistillPromotionRequest,
    DistillRunPatchRequest,
    DistillRunReviewRequest,
    DistillSessionCreateRequest,
    DistillTrialRequest,
)
from app.schemas.question import QuestionGenerateRequest, SourceQuestionPayload
from app.services.distill_workbench import DistillWorkbenchService
from app.services.question_repository import QuestionRepository


class _StubGenerationRunner:
    def generate(self, request: QuestionGenerateRequest) -> dict:
        source_question = request.source_question or SourceQuestionPayload(
            passage="The passage argues that modern governance must balance efficiency, fairness, and execution.",
            stem="Which option best states the main idea of the passage?",
            options={
                "A": "Modern governance must balance efficiency and fairness.",
                "B": "Technology is the only solution for governance problems.",
                "C": "Governance only needs more investment.",
                "D": "Governance reform should be left entirely to the market.",
            },
            answer="A",
            analysis="The passage stresses balancing efficiency, fairness, and execution instead of choosing only one side.",
        )
        topic = request.topic or "distill"
        return {
            "batch_id": f"batch-{topic}",
            "items": [
                {
                    "item_id": f"item-{topic}",
                    "batch_id": f"batch-{topic}",
                    "question_type": "main_idea",
                    "business_subtype": "center_understanding",
                    "pattern_id": "whole_passage_integration",
                    "selected_pattern": "whole_passage_integration",
                    "resolved_slots": {},
                    "skeleton": {},
                    "difficulty_target": "medium",
                    "control_logic": {},
                    "generation_logic": {},
                    "prompt_package": {
                        "system_prompt": "system",
                        "user_prompt": "user",
                        "fewshot_examples": [],
                        "merged_prompt": "system\nuser",
                    },
                    "generated_question": {
                        "question_type": "main_idea",
                        "business_subtype": "center_understanding",
                        "pattern_id": "whole_passage_integration",
                        "stem": source_question.stem,
                        "options": dict(source_question.options),
                        "answer": source_question.answer or "A",
                        "analysis": source_question.analysis or "analysis",
                    },
                    "material_selection": {
                        "material_id": f"mat-{topic}",
                        "article_id": f"art-{topic}",
                        "text": source_question.passage or "",
                        "source": {"source_name": "stub"},
                        "selection_reason": "stub",
                    },
                    "material_text": source_question.passage or "",
                    "material_source": {"source_name": "stub"},
                    "statuses": {
                        "build_status": "success",
                        "review_status": "waiting_review",
                        "generation_status": "success",
                        "validation_status": "passed",
                    },
                    "validation_result": {"passed": True, "validation_status": "passed"},
                    "request_snapshot": request.model_dump(by_alias=True),
                    "current_version_no": 1,
                    "current_status": "pending_review",
                }
            ],
        }


class _FailingGenerationRunner:
    def generate(self, request: QuestionGenerateRequest) -> dict:
        raise DomainError("generation failed", status_code=422, details={"reason": "stub_failure"})


class DistillWorkbenchTest(TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.repository = QuestionRepository(Path(self.tempdir.name) / "distill_workbench.db")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _baseline_request(self, *, topic: str = "governance") -> QuestionGenerateRequest:
        return QuestionGenerateRequest(
            question_focus="center_understanding",
            business_subtype="center_understanding",
            difficulty_level="medium",
            count=1,
            topic=topic,
        )

    def _truth_source_question(self, *, topic: str = "governance") -> SourceQuestionPayload:
        return SourceQuestionPayload(
            passage=f"The passage argues that {topic} must balance efficiency, fairness, and execution.",
            stem="Which option best states the main idea of the passage?",
            options={
                "A": f"{topic.title()} must balance efficiency and fairness.",
                "B": "Technology is the only solution for governance problems.",
                "C": "Governance only needs more investment.",
                "D": "Governance reform should be left entirely to the market.",
            },
            answer="A",
            analysis=f"The passage stresses that {topic} should balance efficiency, fairness, and execution.",
        )

    def test_create_manual_dataset_and_run_trial_on_dev_split(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="manual dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-train",
                        split="train",
                        truth_source_question=self._truth_source_question(topic="governance"),
                        generation_request=self._baseline_request(topic="governance"),
                    ),
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(topic="public policy"),
                        generation_request=self._baseline_request(topic="public policy"),
                    ),
                ],
            )
        )

        self.assertEqual(dataset.sample_count, 2)
        self.assertEqual(dataset.split_counts["train"], 1)
        self.assertEqual(dataset.split_counts["dev"], 1)

        session = service.create_session(
            DistillSessionCreateRequest(
                title="card tuning",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
                baseline_request=self._baseline_request(),
            )
        )

        run = service.run_trial(
            session.session_id,
            DistillTrialRequest(
                split="dev",
                sample_limit=1,
                hypothesis="check dev fit",
            ),
        )

        self.assertEqual(run.status, "completed")
        self.assertEqual(run.split, "dev")
        self.assertEqual(len(run.sample_results), 1)
        self.assertEqual(run.sample_results[0].split, "dev")
        self.assertEqual(run.fit_summary.answer_match, True)
        self.assertEqual(run.fit_summary.question_type_match, True)

    def test_hash_dataset_auto_assigns_splits(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="hash dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="hash",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key=f"sample-{index}",
                        truth_source_question=self._truth_source_question(topic=f"topic {index}"),
                        generation_request=self._baseline_request(topic=f"topic {index}"),
                    )
                    for index in range(1, 7)
                ],
            )
        )

        self.assertEqual(dataset.sample_count, 6)
        self.assertEqual(sum(dataset.split_counts.values()), 6)
        self.assertTrue(any(count > 0 for count in dataset.split_counts.values()))

    def test_new_card_mode_requires_baseline_request(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        with self.assertRaises(DomainError):
            service.create_session(
                DistillSessionCreateRequest(
                    title="new card",
                    mode="new_card",
                )
            )

    def test_failed_trial_is_persisted_without_throwing(self) -> None:
        service = DistillWorkbenchService(self.repository, _FailingGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="failed dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="failed trace",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )

        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))

        self.assertEqual(run.status, "failed")
        self.assertIsNotNone(run.error)
        self.assertEqual(run.error["details"]["reason"], "stub_failure")
        runs = self.repository.list_distill_runs(session.session_id, limit=10)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "failed")

    def test_completed_run_can_be_human_approved_for_promotion(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="review-ready dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="review flow",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )
        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))

        reviewed_run = service.review_run(
            run.run_id,
            DistillRunReviewRequest(
                verdict="approved",
                summary="dev split looks stable against truth and can be promoted",
                allow_promote=True,
                promotion_targets=["question_card", "prompt_config"],
                reviewer="qa_lead",
            ),
        )

        self.assertEqual(reviewed_run.review_count, 1)
        self.assertIsNotNone(reviewed_run.latest_review)
        self.assertEqual(reviewed_run.latest_review.verdict, "approved")
        self.assertEqual(reviewed_run.latest_review.reviewer, "qa_lead")
        self.assertEqual(reviewed_run.latest_review.promotion_targets, ["question_card", "prompt_assets"])
        self.assertEqual(len(reviewed_run.reviews), 1)
        self.assertTrue(reviewed_run.reviews[0].allow_promote)

    def test_failed_run_cannot_be_approved(self) -> None:
        service = DistillWorkbenchService(self.repository, _FailingGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="failed review dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="failed run review",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )
        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))

        with self.assertRaises(DomainError):
            service.review_run(
                run.run_id,
                DistillRunReviewRequest(
                    verdict="approved",
                    summary="should not be approved",
                    allow_promote=True,
                    promotion_targets=["question_card"],
                ),
            )

    def test_patch_and_promotion_bundle_are_persisted(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="promotion dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="promotion flow",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )
        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))
        reviewed_run = service.review_run(
            run.run_id,
            DistillRunReviewRequest(
                verdict="approved",
                summary="ready to promote",
                allow_promote=True,
                promotion_targets=["question_card", "prompt_config"],
                reviewer="qa_lead",
            ),
        )
        patched_run = service.add_run_patch(
            reviewed_run.run_id,
            DistillRunPatchRequest(
                target="question_card",
                title="adjust card slots",
                summary="align card control slots with truth",
                patch={"card_patch": {"slot_mode": "truth_aligned"}},
                author="agent",
            ),
        )
        patched_run = service.add_run_patch(
            patched_run.run_id,
            DistillRunPatchRequest(
                target="prompt_assets",
                title="tighten prompt wording",
                summary="reduce option drift on dev split",
                patch={"prompt_patch": {"instruction": "prefer closer option wording"}},
                author="agent",
            ),
        )

        promoted_run = service.promote_run(
            patched_run.run_id,
            DistillPromotionRequest(
                targets=["question_card", "prompt_config"],
                summary="promote approved tuning bundle",
                promoter="maru",
            ),
        )

        self.assertEqual(promoted_run.patch_count, 2)
        self.assertEqual(promoted_run.promotion_count, 1)
        self.assertIsNotNone(promoted_run.latest_promotion)
        self.assertEqual(promoted_run.latest_promotion.targets, ["prompt_assets", "question_card"])
        self.assertEqual({patch.target for patch in promoted_run.patches}, {"question_card", "prompt_assets"})
        artifact_path = Path(promoted_run.latest_promotion.artifact_path)
        self.assertTrue(artifact_path.exists())
        self.assertIn(str(self.repository.db_path.parent), str(artifact_path))
        self.assertEqual(len(promoted_run.promotions), 1)

    def test_leaf_pre_distill_evidence_targets_can_be_promoted(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="leaf pre-distill evidence dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="leaf pre-distill evidence flow",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )
        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))
        reviewed_run = service.review_run(
            run.run_id,
            DistillRunReviewRequest(
                verdict="approved",
                summary="offline artifacts are ready for evidence promotion",
                allow_promote=True,
                promotion_targets=["leaf_pre_distill_report", "schema_gap_report"],
                reviewer="qa_lead",
            ),
        )
        patched_run = service.add_run_patch(
            reviewed_run.run_id,
            DistillRunPatchRequest(
                target="leaf_pre_distill_report",
                title="attach leaf pre-distill report",
                summary="save offline artifact paths as promotion evidence",
                patch={
                    "artifact_type": "leaf_pre_distill_report",
                    "artifact_path": "data/leaf_pre_distill/demo/report.md",
                    "field_candidates_path": "data/leaf_pre_distill/demo/field_candidates.json",
                    "slot_projection_draft_path": "data/leaf_pre_distill/demo/slot_projection_draft.yaml",
                    "axis_confirmation_path": "data/leaf_pre_distill/demo/axis_confirmation.json",
                    "formal_patch_draft_path": "data/leaf_pre_distill/demo/formal_patch_draft.json",
                },
                author="agent",
            ),
        )
        patched_run = service.add_run_patch(
            patched_run.run_id,
            DistillRunPatchRequest(
                target="schema_gap_report",
                title="attach schema gap notes",
                summary="save schema gap evidence without changing schema",
                patch={
                    "artifact_type": "schema_gap_report",
                    "artifact_path": "data/leaf_pre_distill/demo/report.md#schema-gaps",
                },
                author="agent",
            ),
        )

        promoted_run = service.promote_run(
            patched_run.run_id,
            DistillPromotionRequest(
                targets=["schema_gap_report", "leaf_pre_distill_report"],
                summary="promote offline artifacts as evidence targets",
                promoter="maru",
            ),
        )

        self.assertIsNotNone(promoted_run.latest_promotion)
        self.assertEqual(promoted_run.latest_promotion.targets, ["leaf_pre_distill_report", "schema_gap_report"])
        artifact_path = Path(promoted_run.latest_promotion.artifact_path)
        bundle = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(bundle["targets"], ["leaf_pre_distill_report", "schema_gap_report"])
        patches_by_target = {patch["target"]: patch["patch"] for patch in bundle["patches"]}
        self.assertEqual(
            patches_by_target["leaf_pre_distill_report"]["slot_projection_draft_path"],
            "data/leaf_pre_distill/demo/slot_projection_draft.yaml",
        )
        self.assertEqual(
            patches_by_target["leaf_pre_distill_report"]["field_candidates_path"],
            "data/leaf_pre_distill/demo/field_candidates.json",
        )
        self.assertEqual(
            patches_by_target["leaf_pre_distill_report"]["axis_confirmation_path"],
            "data/leaf_pre_distill/demo/axis_confirmation.json",
        )
        self.assertEqual(
            patches_by_target["leaf_pre_distill_report"]["formal_patch_draft_path"],
            "data/leaf_pre_distill/demo/formal_patch_draft.json",
        )
        self.assertEqual(
            patches_by_target["schema_gap_report"]["artifact_path"],
            "data/leaf_pre_distill/demo/report.md#schema-gaps",
        )

    def test_leaf_pre_distill_evidence_promotion_requires_patch_for_each_target(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="leaf evidence guard dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="leaf evidence guard flow",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )
        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))
        reviewed_run = service.review_run(
            run.run_id,
            DistillRunReviewRequest(
                verdict="approved",
                summary="two evidence targets are allowed",
                allow_promote=True,
                promotion_targets=["leaf_pre_distill_report", "schema_gap_report"],
            ),
        )
        patched_run = service.add_run_patch(
            reviewed_run.run_id,
            DistillRunPatchRequest(
                target="leaf_pre_distill_report",
                title="attach report only",
                patch={
                    "artifact_type": "leaf_pre_distill_report",
                    "artifact_path": "data/leaf_pre_distill/demo/report.md",
                },
            ),
        )

        with self.assertRaises(DomainError):
            service.promote_run(
                patched_run.run_id,
                DistillPromotionRequest(
                    targets=["leaf_pre_distill_report", "schema_gap_report"],
                    summary="should fail because schema gap patch is missing",
                ),
            )

    def test_promotion_requires_matching_patch_for_each_target(self) -> None:
        service = DistillWorkbenchService(self.repository, _StubGenerationRunner())
        dataset = service.create_dataset(
            DistillDatasetCreateRequest(
                title="promotion guard dataset",
                question_type="main_idea",
                business_subtype="center_understanding",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="sample-dev",
                        split="dev",
                        truth_source_question=self._truth_source_question(),
                        generation_request=self._baseline_request(),
                    )
                ],
            )
        )
        session = service.create_session(
            DistillSessionCreateRequest(
                title="promotion guard flow",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
            )
        )
        run = service.run_trial(session.session_id, DistillTrialRequest(split="dev"))
        service.review_run(
            run.run_id,
            DistillRunReviewRequest(
                verdict="approved",
                summary="allowed in principle",
                allow_promote=True,
                promotion_targets=["question_card"],
            ),
        )

        with self.assertRaises(DomainError):
            service.promote_run(
                run.run_id,
                DistillPromotionRequest(
                    targets=["question_card"],
                    summary="should fail because no patch exists",
                ),
            )

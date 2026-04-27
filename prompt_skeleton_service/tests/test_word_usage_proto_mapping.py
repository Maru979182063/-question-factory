from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from app.core.exceptions import DomainError
from app.schemas.distill import (
    DistillDatasetCreateRequest,
    DistillDatasetSampleInput,
    DistillSessionCreateRequest,
    DistillTrialRequest,
)
from app.schemas.question import QuestionGenerateRequest, SourceQuestionPayload
from app.services.config_registry import ConfigRegistry
from app.services.distill_workbench import DistillWorkbenchService
from app.services.input_decoder import InputDecoderService
from app.services.prompt_orchestrator import PromptOrchestratorService
from app.services.question_generation import QuestionGenerationService
from app.services.question_repository import QuestionRepository


class WordUsageProtoMappingTest(TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.repository = QuestionRepository(Path(self.tempdir.name) / "word_usage_proto.db")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _generation_service(self) -> QuestionGenerationService:
        service = QuestionGenerationService.__new__(QuestionGenerationService)
        service.repository = self.repository
        service.source_question_parser = Mock()
        service.orchestrator = PromptOrchestratorService(
            ConfigRegistry(Path(__file__).resolve().parents[1] / "configs" / "types")
        )
        return service

    def _source_question(self) -> SourceQuestionPayload:
        return SourceQuestionPayload(
            passage="这些信息一旦泄露了，就是“裸奔”，这里的“裸奔”指的是（    ）。",
            stem="这里的“裸奔”指的是（    ）。",
            options={
                "A": "个人信息泄露",
                "B": "人脸识别错误",
                "C": "手机失去信号",
                "D": "防控措施不当",
            },
            answer="A",
            analysis="全文围绕个人信息泄露论述，故“裸奔”指的是个人信息泄露，A项当选。",
        )

    def _proto_request(self, *, enable_flag: bool = True, subtype: str = "word_usage_content_word") -> QuestionGenerateRequest:
        extra_constraints = {"experimental_proto_route": True} if enable_flag else {}
        return QuestionGenerateRequest(
            question_focus="word_usage",
            business_subtype=subtype,
            difficulty_level="medium",
            count=1,
            topic="word usage proto",
            source_question=self._source_question(),
            extra_constraints=extra_constraints,
        )

    def test_word_usage_content_word_proto_generation_trial_completes(self) -> None:
        generation_service = self._generation_service()
        workbench = DistillWorkbenchService(self.repository, generation_service)
        dataset = workbench.create_dataset(
            DistillDatasetCreateRequest(
                title="word usage proto dataset",
                question_type="word_usage",
                business_subtype="word_usage_content_word",
                split_mode="manual",
                samples=[
                    DistillDatasetSampleInput(
                        sample_key="word-usage-dev",
                        split="dev",
                        truth_source_question=self._source_question(),
                        generation_request=self._proto_request(),
                        tags=["new_leaf", "bootstrap_discovery", "proto"],
                    )
                ],
            )
        )
        session = workbench.create_session(
            DistillSessionCreateRequest(
                title="word usage proto session",
                mode="card_tuning",
                dataset_id=dataset.dataset_id,
                baseline_request=self._proto_request(),
            )
        )

        run = workbench.run_trial(
            session.session_id,
            DistillTrialRequest(split="dev", sample_limit=1, hypothesis="proto mapping smoke"),
        )

        self.assertEqual(run.status, "completed")
        self.assertEqual(run.sample_results[0].error, None)
        self.assertEqual(run.item_preview.question_type, "word_usage")
        self.assertEqual(run.item_preview.business_subtype, "word_usage_content_word")
        metadata = run.item_preview.generated_question.metadata
        self.assertEqual(metadata["experimental"], True)
        self.assertEqual(metadata["proto_family"], "word_usage")
        self.assertEqual(metadata["proto_child_family"], "word_usage_content_word")
        self.assertEqual(metadata["formalized"], False)
        self.assertIn("proto_minimal_json_shape_only", run.item_preview.validation_result.warnings)

    def test_missing_proto_flag_still_uses_original_unmapped_guard(self) -> None:
        generation_service = self._generation_service()

        with self.assertRaises(DomainError) as ctx:
            generation_service.generate(self._proto_request(enable_flag=False))

        self.assertEqual(str(ctx.exception), "Selected business_subtype is not mapped yet.")
        self.assertEqual(ctx.exception.details["business_subtype"], "word_usage_content_word")

    def test_unknown_subtype_does_not_fall_back_to_proto_route(self) -> None:
        generation_service = self._generation_service()

        with self.assertRaises(DomainError) as ctx:
            generation_service.generate(self._proto_request(subtype="word_usage_unknown"))

        self.assertEqual(str(ctx.exception), "Selected business_subtype is not mapped yet.")
        self.assertEqual(ctx.exception.details["business_subtype"], "word_usage_unknown")

    def test_existing_three_family_decoder_targets_are_unchanged(self) -> None:
        decoder = InputDecoderService()
        cases = [
            ("sentence_order", "sentence_order_selection", "sentence_order", None),
            ("sentence_fill", "sentence_fill_selection", "sentence_fill", None),
            ("center_understanding", "center_understanding", "main_idea", "center_understanding"),
        ]

        for question_focus, business_subtype, expected_type, expected_subtype in cases:
            request = QuestionGenerateRequest(
                question_focus=question_focus,
                business_subtype=business_subtype,
                difficulty_level="medium",
                count=1,
            )
            decoded = decoder.decode(request.to_dify_form_input())
            standard_request = decoded["standard_request"]
            self.assertEqual(standard_request["question_type"], expected_type)
            self.assertEqual(standard_request["business_subtype"], expected_subtype)


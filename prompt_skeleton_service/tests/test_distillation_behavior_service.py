from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.schemas.distillation import BehaviorDistillationExtractRequest
from app.services.distillation_behavior_service import DistillationBehaviorService
from app.services.question_repository import QuestionRepository


def _base_item(*, item_id: str, question_card_id: str, revision_count: int = 1) -> dict:
    return {
        "item_id": item_id,
        "batch_id": "batch-1",
        "question_type": "sentence_fill",
        "business_subtype": "sentence_fill",
        "pattern_id": "bridge_transition",
        "difficulty_target": "medium",
        "generated_question": {
            "stem": "Fill in the blank with the most suitable sentence.",
            "options": {
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D",
            },
            "answer": "A",
            "analysis": "analysis",
        },
        "material_selection": {
            "material_id": "mat-1",
            "article_id": "art-1",
            "question_card_id": question_card_id,
            "text": "material",
            "source": {"site": "demo"},
            "selection_reason": "selected",
        },
        "material_text": "material",
        "material_source": {"site": "demo"},
        "request_snapshot": {
            "question_card_id": question_card_id,
            "type_slots": {"blank_position": "middle", "function_type": "bridge"},
        },
        "statuses": {
            "review_status": "approved",
            "generation_status": "success",
            "validation_status": "passed",
        },
        "validation_result": {"passed": True, "validation_status": "passed"},
        "current_version_no": 2,
        "current_status": "approved",
        "revision_count": revision_count,
        "latest_action": "manual_edit" if revision_count else "confirm",
    }


def _version_payload(*, item_id: str, version_no: int, parent_version_no: int | None, source_action: str, stem: str, options: dict, analysis: str) -> dict:
    return {
        "version_id": f"{item_id}:v{version_no}",
        "item_id": item_id,
        "version_no": version_no,
        "parent_version_no": parent_version_no,
        "source_action": source_action,
        "target_difficulty": "medium",
        "material_id": "mat-1",
        "prompt_template_name": "default",
        "prompt_template_version": "v1",
        "stem": stem,
        "options": options,
        "answer": "A",
        "analysis": analysis,
        "prompt_package": {"system_prompt": "s", "user_prompt": "u"},
        "prompt_render_snapshot": {"rendered": True},
        "raw_model_output": {"raw": True},
        "parsed_structured_output": {"stem": stem, "options": options, "analysis": analysis},
        "parse_error": None,
        "validation_result": {"passed": True},
        "evaluation_result": {"overall_score": 82},
        "runtime_snapshot": {
            "material_snapshot": {"material_id": "mat-1", "preview": "material", "original_text": "material"},
            "prompt_snapshot": {"selected_pattern": "bridge_transition"},
            "model_output_snapshot": {
                "parsed_structured_output": {
                    "stem": stem,
                    "options": options,
                    "analysis": analysis,
                }
            },
        },
        "created_at": f"2026-04-21T0{version_no}:00:00+00:00",
    }


class DistillationBehaviorServiceTest(TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        self.repository = QuestionRepository(Path(self.tempdir.name) / "behavior_distillation.db")

        item = _base_item(item_id="item-1", question_card_id="sentence_fill_middle_bridge", revision_count=1)
        self.repository.save_item(item)
        self.repository.save_version(
            _version_payload(
                item_id="item-1",
                version_no=1,
                parent_version_no=None,
                source_action="generate",
                stem="Fill in the blank with the most suitable sentence.",
                options={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                analysis="draft analysis",
            )
        )
        self.repository.save_version(
            _version_payload(
                item_id="item-1",
                version_no=2,
                parent_version_no=1,
                source_action="manual_edit",
                stem="Fill in the blank with the most suitable sentence.",
                options={"A": "Option A revised", "B": "Option B", "C": "Option C", "D": "Option D"},
                analysis="revised analysis",
            )
        )
        self.repository.save_review_action(
            "action-1",
            "item-1",
            "manual_edit",
            {
                "changed_fields": ["options", "analysis"],
                "truth_touched": False,
                "material_boundary_crossed": False,
                "feedback_backtest_unit": {
                    "item_id": "item-1",
                    "question_type": "sentence_fill",
                    "question_card_id": "sentence_fill_middle_bridge",
                    "accepted_as_is": False,
                    "revised_then_kept": True,
                    "discarded": False,
                    "failed_threshold_names": ["distractor_similarity_low"],
                },
            },
            from_version_no=1,
            to_version_no=2,
            result_status="approved",
            operator="tester",
        )
        self.repository.save_usage_event(
            "event-1",
            "item-1",
            "download",
            {"download_variant": "accepted_after_edit"},
            operator="tester",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_build_packet_from_question_card_history(self) -> None:
        service = DistillationBehaviorService(self.repository)

        packet = service.build_packet(
            BehaviorDistillationExtractRequest(
                question_card_id="sentence_fill_middle_bridge",
                limit=10,
            )
        )

        self.assertEqual(packet.aggregate_summary.item_count, 1)
        self.assertEqual(packet.aggregate_summary.total_review_actions, 1)
        self.assertEqual(packet.aggregate_summary.total_downloads, 1)
        self.assertEqual(packet.item_traces[0].final_outcome, "accepted_after_edit")
        self.assertIn("options", packet.item_traces[0].hot_changed_fields)
        self.assertEqual(packet.aggregate_summary.top_failed_thresholds[0].key, "distractor_similarity_low")
        self.assertTrue(packet.candidate_patch_hints)
        self.assertIsNotNone(packet.selected_agent_adjustment)
        self.assertIn("行为蒸馏已覆盖", packet.report.executive_summary)

    def test_build_packet_can_hide_item_traces(self) -> None:
        service = DistillationBehaviorService(self.repository)

        packet = service.build_packet(
            BehaviorDistillationExtractRequest(
                item_id="item-1",
                include_item_traces=False,
            )
        )

        self.assertEqual(packet.aggregate_summary.item_count, 1)
        self.assertEqual(packet.item_traces, [])
        self.assertTrue(packet.candidate_patch_hints)

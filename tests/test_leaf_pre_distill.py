import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools.leaf_pre_distill.axis_confirmation import build_axis_confirmation
from tools.leaf_pre_distill.bootstrap_discovery import build_bootstrap_discovery
from tools.leaf_pre_distill.behavior_marker import build_behavior_trace
from tools.leaf_pre_distill.field_candidate_builder import build_field_candidates, build_slot_projection_draft
from tools.leaf_pre_distill.formal_patch_draft import build_formal_patch_draft
from tools.leaf_pre_distill.formal_writeback_plan import (
    build_formal_writeback_plan,
    render_formal_writeback_diff,
)
from tools.leaf_pre_distill.formal_writeback_executor import (
    FormalWritebackError,
    execute_formal_writeback,
    validate_writeback_approval,
)
from tools.leaf_pre_distill.agent_review_feedback import build_feedback_input, run_agent_review_feedback_normalization
from tools.leaf_pre_distill.formalization_readiness_gate import run_formalization_readiness_gate
from tools.leaf_pre_distill.llm_field_probe import (
    _chat_completions_url,
    _parse_chat_completion_body,
    _parse_sse_chat_content,
    run_llm_field_probe,
)
from tools.leaf_pre_distill.llm_safe_digest import build_llm_safe_digest, digest_json_size
from tools.leaf_pre_distill.material_protocol_draft import (
    build_mock_material_protocol_bundle,
    build_system_alignment_findings,
    run_material_protocol_draft,
    validate_material_protocol_bundle,
)
from tools.leaf_pre_distill.material_evidence_alignment_regression import run_material_evidence_alignment_regression
from tools.leaf_pre_distill.material_protocol_split_pipeline import (
    run_material_protocol_split_pipeline,
    validate_split_stages,
)
from tools.leaf_pre_distill.material_protocol_split_runtime import execute_split_stages
from tools.leaf_pre_distill.material_protocol_split_stage_report import build_pipeline_stage_report
from tools.leaf_pre_distill.report_renderer import render_markdown_report
from tools.leaf_pre_distill.runtime_activation_plan import run_runtime_activation_plan
from tools.leaf_pre_distill.new_leaf_formalization_packet import run_new_leaf_formalization_packet
from tools.leaf_pre_distill.run import run_leaf_pre_distill
from tools.leaf_pre_distill.gold_reconstruction import (
    apply_question_wrapper_leakage_check,
    normalize_gold_reconstruction,
)
from tools.leaf_pre_distill.gold_reconstruction_llm_smoke import run_gold_reconstruction_llm_smoke
from tools.leaf_pre_distill.gold_reconstruction_prompt import build_gold_reconstruction_messages
from tools.leaf_pre_distill.source_candidate_review import run_source_candidate_review
from tools.leaf_pre_distill.source_candidate_search import (
    MockSearchProvider,
    classify_source_risk,
    parse_bing_html_results,
    parse_duckduckgo_html_results,
    run_source_candidate_search_from_queries,
)
from tools.leaf_pre_distill.source_discovery_preparation import run_source_discovery_preparation_from_artifact_dir
from tools.leaf_pre_distill.truth_gold_regression import run_truth_gold_regression_from_artifact_dir


class _FakeClient:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = []

    def complete(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.output


class _FakeSequenceClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls = []

    def complete(self, **kwargs) -> str:
        self.calls.append(kwargs)
        index = min(len(self.calls) - 1, len(self.outputs) - 1)
        return self.outputs[index]


class _FlakyClient:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = []

    def complete(self, **kwargs) -> str:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            raise RuntimeError("temporary empty stream")
        return self.output


def _sample(sample_id: str, analysis: str, exam_points: str = "") -> dict:
    return {
        "sample_id": sample_id,
        "qid": f"#{sample_id}",
        "source_file_name": "sample.docx",
        "mother_family_id": "sentence_order",
        "leaf_label": "日常逻辑-时间脉络",
        "stem": "",
        "analysis": analysis,
        "exam_points": exam_points,
        "raw_text": "",
    }


class LeafPreDistillTest(unittest.TestCase):
    def test_sentence_order_timeline_projects_to_overlay_and_schema_gap(self) -> None:
        samples = [
            _sample(str(index), "按照时间顺序，先后关系不能交换。", "语句排序题-确定顺序-日常逻辑-时间脉络")
            for index in range(40)
        ]
        traces = [build_behavior_trace(sample, mother_family_id="sentence_order") for sample in samples]
        report = build_field_candidates(
            mother_family_id="sentence_order",
            leaf_label="日常逻辑-时间脉络",
            samples=samples,
            traces=traces,
        )
        timeline = next(
            candidate
            for candidate in report["field_candidates"]
            if candidate["field_path"] == "ordering_logic"
        )

        self.assertEqual(timeline["proposed_value"], "timeline_progression")
        self.assertEqual(timeline["target_layer"], "material_card_overlay")
        self.assertEqual(timeline["confidence"], "high")
        self.assertTrue(report["schema_gaps"])

        projection = build_slot_projection_draft(report)
        self.assertEqual(projection["overlay_updates"]["ordering_logic"], "timeline_progression")
        self.assertIn("schema_gap_report", projection["promotion_targets"])

    def test_sentence_order_generic_first_sentence_does_not_create_background_intro(self) -> None:
        samples = [
            _sample(str(index), "观察选项，确定首句。该句适合做首句。")
            for index in range(40)
        ]
        traces = [build_behavior_trace(sample, mother_family_id="sentence_order") for sample in samples]
        report = build_field_candidates(
            mother_family_id="sentence_order",
            leaf_label="普通首句判断",
            samples=samples,
            traces=traces,
        )

        background_candidates = [
            candidate
            for candidate in report["field_candidates"]
            if candidate["field_path"] == "opening_anchor_type"
        ]
        self.assertEqual(background_candidates, [])

    def test_default_run_does_not_generate_llm_probe_artifacts(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_sample("1", "analysis")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="sentence_order",
                    leaf_label="timeline",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                )

            self.assertFalse(summary["llm_probe_enabled"])
            self.assertNotIn("llm_safe_digest", summary["artifacts"])
            self.assertNotIn("llm_field_probe", summary["artifacts"])
            self.assertNotIn("bootstrap_discovery", summary["artifacts"])
            self.assertNotIn("axis_confirmation", summary["artifacts"])
            self.assertNotIn("formal_patch_draft", summary["artifacts"])
            self.assertNotIn("truth_gold_split_manifest", summary["artifacts"])
            self.assertNotIn("truth_gold_regression_results", summary["artifacts"])
            self.assertNotIn("truth_gold_regression_report", summary["artifacts"])
            self.assertNotIn("model_safe_gold_reconstruction_input", summary["artifacts"])
            self.assertNotIn("gold_reconstruction_results", summary["artifacts"])
            self.assertNotIn("gold_reconstruction_report", summary["artifacts"])
            self.assertNotIn("source_discovery_queries", summary["artifacts"])
            self.assertNotIn("material_source_profile", summary["artifacts"])
            self.assertNotIn("initial_material_seed_pack", summary["artifacts"])
            self.assertNotIn("source_discovery_preparation_report", summary["artifacts"])
            self.assertNotIn("system_alignment_findings", summary["artifacts"])
            self.assertNotIn("material_protocol_draft_input_digest", summary["artifacts"])
            self.assertNotIn("material_card_draft", summary["artifacts"])
            self.assertNotIn("material_line_prompt_assets_draft", summary["artifacts"])
            self.assertNotIn("material_quality_regression_draft", summary["artifacts"])
            self.assertNotIn("material_review_prompts", summary["artifacts"])
            self.assertNotIn("material_bridge_mapping_draft", summary["artifacts"])
            self.assertNotIn("material_protocol_assets_draft_report", summary["artifacts"])
            self.assertNotIn("source_text_evidence_manifest", summary["artifacts"])
            self.assertNotIn("source_text_evidence_results", summary["artifacts"])
            self.assertNotIn("source_gold_alignment_results", summary["artifacts"])
            self.assertNotIn("material_quality_regression_results", summary["artifacts"])
            self.assertFalse((output_dir / "llm_safe_digest.json").exists())
            self.assertFalse((output_dir / "llm_field_probe.json").exists())
            self.assertFalse((output_dir / "bootstrap_discovery.json").exists())
            self.assertFalse((output_dir / "axis_confirmation.json").exists())
            self.assertFalse((output_dir / "formal_patch_draft.json").exists())
            self.assertFalse((output_dir / "truth_gold_split_manifest.json").exists())
            self.assertFalse((output_dir / "truth_gold_regression_results.json").exists())
            self.assertFalse((output_dir / "truth_gold_regression_report.md").exists())
            self.assertFalse((output_dir / "model_safe_gold_reconstruction_input.jsonl").exists())
            self.assertFalse((output_dir / "gold_reconstruction_results.jsonl").exists())
            self.assertFalse((output_dir / "gold_reconstruction_report.md").exists())
            self.assertFalse((output_dir / "source_discovery_queries.jsonl").exists())
            self.assertFalse((output_dir / "material_source_profile.json").exists())
            self.assertFalse((output_dir / "initial_material_seed_pack.jsonl").exists())
            self.assertFalse((output_dir / "source_discovery_preparation_report.md").exists())
            self.assertFalse((output_dir / "system_alignment_findings.json").exists())
            self.assertFalse((output_dir / "material_protocol_draft_input_digest.json").exists())
            self.assertFalse((output_dir / "material_card_draft.json").exists())
            self.assertFalse((output_dir / "material_line_prompt_assets_draft.json").exists())
            self.assertFalse((output_dir / "material_quality_regression_draft.json").exists())
            self.assertFalse((output_dir / "material_review_prompts.md").exists())
            self.assertFalse((output_dir / "material_bridge_mapping_draft.json").exists())
            self.assertFalse((output_dir / "material_protocol_assets_draft_report.md").exists())
            self.assertFalse((output_dir / "source_text_evidence_manifest.json").exists())
            self.assertFalse((output_dir / "source_text_evidence_results.jsonl").exists())
            self.assertFalse((output_dir / "source_gold_alignment_results.jsonl").exists())
            self.assertFalse((output_dir / "material_quality_regression_results.json").exists())

    def test_llm_safe_digest_excludes_raw_text_and_truncates_examples(self) -> None:
        samples = [_sample("1", "analysis", "exam")]
        samples[0]["raw_text"] = "SECRET_RAW_TEXT_SHOULD_NOT_APPEAR"
        traces = [
            {
                "sample_id": "1",
                "observed_actions": [
                    {
                        "action": "detect_timeline_progression",
                        "field_path": "ordering_logic",
                        "proposed_value": "timeline_progression",
                    }
                ],
            }
        ]
        candidate_report = {
            "mother_family_id": "sentence_order",
            "leaf_label": "timeline",
            "sample_count": 1,
            "field_candidates": [
                {
                    "field_path": "ordering_logic",
                    "proposed_value": "timeline_progression",
                    "target_layer": "material_card_overlay",
                    "support_rate": 1.0,
                    "support_count": 1,
                    "confidence": "high",
                    "evidence_examples": [f"example-{index}" for index in range(10)],
                    "uniqueness_source": [],
                    "distractor_modes": [],
                }
            ],
            "schema_gaps": [],
            "summary": {},
        }
        slot_projection = build_slot_projection_draft(candidate_report)

        digest = build_llm_safe_digest(
            manifest={"mother_family_id": "sentence_order", "leaf_label": "timeline"},
            samples=samples,
            traces=traces,
            candidate_report=candidate_report,
            slot_projection=slot_projection,
            max_digest_chars=2200,
            max_evidence_examples=5,
        )
        digest_text = str(digest)

        self.assertNotIn("raw_text", digest_text)
        self.assertNotIn("SECRET_RAW_TEXT_SHOULD_NOT_APPEAR", digest_text)
        self.assertLessEqual(len(digest["field_candidates"][0]["evidence_examples"]), 5)
        self.assertLessEqual(digest_json_size(digest), 2200)

    def test_mock_llm_json_generates_field_probe(self) -> None:
        digest = _probe_digest()
        client = _FakeClient(
            """
            {
              "usable": true,
              "leaf_signature": "timeline sequence with local adjacency checks",
              "confirmed_fields": {"ordering_logic": "timeline_progression"},
              "field_risks": [{"field_path": "ordering_logic", "risk": "temporal words may be superficial"}],
              "schema_gap_comments": [{"field": "timeline_progression_as_middle_structure", "comment": "keep as overlay"}],
              "should_promote": true
            }
            """
        )

        probe = run_llm_field_probe(digest=digest, client=client, model="chat")

        self.assertTrue(probe["usable"])
        self.assertEqual(probe["confirmed_fields"], {"ordering_logic": "timeline_progression"})
        self.assertFalse(probe["should_promote"])
        self.assertIn("forced to false", " ".join(probe["warnings"]))
        self.assertEqual(len(client.calls), 1)

    def test_unknown_llm_field_is_rejected_not_confirmed(self) -> None:
        digest = _probe_digest()
        client = _FakeClient(
            """
            {
              "usable": true,
              "leaf_signature": "timeline sequence",
              "confirmed_fields": {
                "ordering_logic": "timeline_progression",
                "invented_formal_field": "new_value"
              },
              "warnings": []
            }
            """
        )

        probe = run_llm_field_probe(digest=digest, client=client, model="chat")

        self.assertEqual(probe["confirmed_fields"], {"ordering_logic": "timeline_progression"})
        self.assertEqual(probe["rejected_suggestions"][0]["field_path"], "invented_formal_field")
        self.assertIn("Rejected unknown", " ".join(probe["warnings"]))

    def test_invalid_llm_json_marks_unusable_without_interrupting(self) -> None:
        digest = _probe_digest()
        probe = run_llm_field_probe(digest=digest, client=_FakeClient("not json"), model="chat")

        self.assertFalse(probe["usable"])
        self.assertFalse(probe["should_promote"])
        self.assertIn("error", probe)

    def test_sse_chat_response_content_can_be_parsed(self) -> None:
        raw = "\n".join(
            [
                'data: {"choices":[{"delta":{"content":"{\\"ok\\":"}}]}',
                'data: {"choices":[{"delta":{"content":" true}"}}]}',
                "data: [DONE]",
            ]
        )

        self.assertEqual(_parse_sse_chat_content(raw), '{"ok": true}')

    def test_chat_completion_body_parser_accepts_json_even_with_sse_header_style_body(self) -> None:
        raw = json.dumps({"choices": [{"message": {"content": "{\"ok\": true}"}}]})

        payload = _parse_chat_completion_body(raw)

        self.assertEqual(payload["choices"][0]["message"]["content"], '{"ok": true}')

    def test_chat_completion_body_parser_tolerates_unescaped_control_chars(self) -> None:
        raw = '{"choices":[{"message":{"content":"line one\nline two"}}]}'

        payload = _parse_chat_completion_body(raw)

        self.assertEqual(payload["choices"][0]["message"]["content"], "line one\nline two")

    def test_chat_completion_url_adds_v1_for_root_compatible_base(self) -> None:
        self.assertEqual(_chat_completions_url("https://new.fastaicode.top"), "https://new.fastaicode.top/v1/chat/completions")
        self.assertEqual(_chat_completions_url("https://new.fastaicode.top/v1"), "https://new.fastaicode.top/v1/chat/completions")

    def test_report_appends_llm_field_probe_section(self) -> None:
        candidate_report = _candidate_report()
        slot_projection = build_slot_projection_draft(candidate_report)
        report = render_markdown_report(
            manifest={"job_id": "job", "mother_family_id": "sentence_order", "leaf_label": "timeline"},
            candidate_report=candidate_report,
            slot_projection=slot_projection,
            llm_probe={
                "enabled": True,
                "usable": True,
                "model": "chat",
                "leaf_signature": "timeline sequence",
                "confirmed_fields": {"ordering_logic": "timeline_progression"},
                "field_risks": [{"field_path": "ordering_logic", "risk": "risk"}],
                "schema_gap_comments": [{"field": "gap", "comment": "comment"}],
                "warnings": ["auxiliary only"],
            },
        )

        self.assertIn("## LLM Field Probe", report)
        self.assertIn("auxiliary evidence only", report)
        self.assertIn("ordering_logic", report)

    def test_llm_dry_run_writes_digest_and_disabled_probe(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_sample("1", "analysis")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="sentence_order",
                    leaf_label="timeline",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    llm_dry_run=True,
                )

            self.assertTrue(summary["llm_probe_dry_run"])
            self.assertTrue((output_dir / "llm_safe_digest.json").exists())
            self.assertTrue((output_dir / "llm_field_probe.json").exists())
            self.assertIn("LLM Field Probe", (output_dir / "report.md").read_text(encoding="utf-8"))

    def test_bootstrap_discovery_generates_hypotheses_for_empty_field_candidates(self) -> None:
        samples = [_word_usage_sample("1"), _word_usage_sample("2")]
        discovery = build_bootstrap_discovery(
            manifest={"mother_family_id": "word_usage", "leaf_label": "实词"},
            samples=samples,
            traces=[{"sample_id": "1", "observed_actions": []}, {"sample_id": "2", "observed_actions": []}],
            candidate_report=_empty_candidate_report(),
            proto_family_label="word_usage",
        )

        self.assertFalse(discovery["known_family_matched"])
        self.assertFalse(discovery["promotion_allowed"])
        self.assertEqual(discovery["proto_mother_family"]["status"], "hypothesis")
        self.assertEqual(discovery["proto_mother_family"]["label"], "word_usage")
        self.assertTrue(discovery["candidate_axes"])
        self.assertTrue(all(axis["status"] == "hypothesis" for axis in discovery["candidate_axes"]))
        axis_names = {axis["axis"] for axis in discovery["candidate_axes"]}
        self.assertTrue(
            axis_names
            & {
                "referent_resolution_mode",
                "contextual_meaning_mode",
                "explanation_target_type",
            }
        )
        taxonomy_modes = {item["mode"] for item in discovery["distractor_taxonomy"]}
        self.assertTrue(taxonomy_modes & {"literal_meaning_trap", "context_detached", "concept_swap"})

        discovery_text = str(discovery)
        self.assertNotIn("confirmed_fields", discovery_text)
        self.assertNotIn("slot_projection_updates", discovery_text)
        self.assertNotIn("validator_contract_candidates", discovery_text)

    def test_bootstrap_discovery_run_writes_artifact_and_report_section(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    leaf_label="实词",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_bootstrap_discovery=True,
                    bootstrap_proto_family_label="word_usage",
                )

            self.assertTrue(summary["bootstrap_discovery_enabled"])
            self.assertIn("bootstrap_discovery", summary["artifacts"])
            discovery_path = output_dir / "bootstrap_discovery.json"
            self.assertTrue(discovery_path.exists())
            discovery = __import__("json").loads(discovery_path.read_text(encoding="utf-8"))
            self.assertFalse(discovery["promotion_allowed"])
            self.assertEqual(discovery["proto_mother_family"]["status"], "hypothesis")
            self.assertIn("Bootstrap Leaf Discovery", (output_dir / "report.md").read_text(encoding="utf-8"))

    def test_bootstrap_discovery_can_coexist_with_llm_probe_as_attachments(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    leaf_label="实词",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    llm_dry_run=True,
                    enable_bootstrap_discovery=True,
                )

            self.assertIn("llm_field_probe", summary["artifacts"])
            self.assertIn("bootstrap_discovery", summary["artifacts"])
            projection = (output_dir / "slot_projection_draft.yaml").read_text(encoding="utf-8")
            self.assertNotIn("bootstrap_discovery", projection)

    def test_axis_confirmation_turns_human_decisions_into_proto_confirmed_only(self) -> None:
        discovery = _word_usage_discovery()
        confirmation = build_axis_confirmation(
            manifest=_word_usage_manifest(),
            bootstrap_discovery=discovery,
            decision_payload={
                "reviewer": "human",
                "proto_family_label": "word_usage",
                "decisions": [
                    {
                        "source_type": "candidate_axis",
                        "source_id": "contextual_meaning_mode",
                        "action": "promote_to_proto_field",
                        "target_name": "contextual_meaning_mode",
                        "target_layer": "business_feature_card",
                        "rationale": "kept for proto drafting",
                    },
                    {
                        "source_type": "candidate_axis",
                        "source_id": "option_elimination_mode",
                        "action": "downgrade_to_note",
                        "rationale": "too generic",
                    },
                    {
                        "source_type": "candidate_axis",
                        "source_id": "invented_axis",
                        "action": "keep",
                    },
                ],
            },
        )

        self.assertEqual(confirmation["status"], "proto_confirmed")
        self.assertFalse(confirmation["formalized"])
        self.assertFalse(confirmation["promotion_allowed"])
        self.assertEqual(confirmation["proto_mother_family"]["status"], "proto_confirmed")
        self.assertEqual(confirmation["axis_decisions"][0]["status"], "proto_confirmed")
        self.assertFalse(confirmation["axis_decisions"][0]["formal"])
        self.assertEqual(confirmation["rejected_or_deferred"][0]["status"], "deferred")
        self.assertIn("Unknown source ignored", " ".join(confirmation["warnings"]))
        self.assertNotIn("confirmed_fields", str(confirmation))

    def test_formal_patch_draft_is_draft_only_and_never_writeback(self) -> None:
        confirmation = build_axis_confirmation(
            manifest=_word_usage_manifest(),
            bootstrap_discovery=_word_usage_discovery(),
            decision_payload={
                "reviewer": "human",
                "decisions": [
                    {
                        "source_type": "candidate_axis",
                        "source_id": "contextual_meaning_mode",
                        "action": "promote_to_proto_field",
                        "target_layer": "business_feature_card",
                    },
                    {
                        "source_type": "candidate_axis",
                        "source_id": "referent_resolution_mode",
                        "action": "map_to_prompt_guard",
                    },
                ],
            },
        )
        draft = build_formal_patch_draft(manifest=_word_usage_manifest(), axis_confirmation=confirmation)

        self.assertEqual(draft["status"], "draft_only")
        self.assertFalse(draft["writeback_allowed"])
        self.assertFalse(draft["formalized"])
        self.assertFalse(draft["promotion_allowed"])
        targets = {patch["target"] for patch in draft["target_patches"]}
        self.assertEqual(targets, {"business_feature_card", "prompt_assets"})
        for patch in draft["target_patches"]:
            self.assertFalse(patch["writeback_allowed"])
            self.assertFalse(patch["formalized"])
            self.assertTrue(patch["patch"]["experimental"])
            self.assertFalse(patch["patch"]["formalized"])
            self.assertEqual(patch["patch"]["proto_confirmed_decisions"][0]["status"], "proto_confirmed")

    def test_axis_confirmation_and_formal_patch_draft_run_write_artifacts_and_report(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            decisions_path = Path(tempdir) / "axis_decisions.json"
            decisions_path.write_text(
                json.dumps(
                    {
                        "reviewer": "human",
                        "proto_family_label": "word_usage",
                        "decisions": [
                            {
                                "source_type": "candidate_axis",
                                "source_id": "contextual_meaning_mode",
                                "action": "promote_to_proto_field",
                                "target_layer": "business_feature_card",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="实词",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_bootstrap_discovery=True,
                    bootstrap_proto_family_label="word_usage",
                    enable_axis_confirmation=True,
                    axis_confirmation_decisions=decisions_path,
                    enable_formal_patch_draft=True,
                )

            self.assertIn("axis_confirmation", summary["artifacts"])
            self.assertIn("formal_patch_draft", summary["artifacts"])
            confirmation = json.loads((output_dir / "axis_confirmation.json").read_text(encoding="utf-8"))
            draft = json.loads((output_dir / "formal_patch_draft.json").read_text(encoding="utf-8"))
            report = (output_dir / "report.md").read_text(encoding="utf-8")

            self.assertEqual(confirmation["axis_decisions"][0]["status"], "proto_confirmed")
            self.assertFalse(confirmation["formalized"])
            self.assertEqual(draft["status"], "draft_only")
            self.assertFalse(draft["writeback_allowed"])
            self.assertIn("Axis Confirmation", report)
            self.assertIn("Formal Patch Draft", report)
            self.assertIn("axis_confirmation", summary["artifacts"]["axis_confirmation"])
            self.assertIn("formal_patch_draft", summary["artifacts"]["formal_patch_draft"])

    def test_formal_writeback_plan_is_preview_only_with_diff(self) -> None:
        confirmation = build_axis_confirmation(
            manifest=_word_usage_manifest(),
            bootstrap_discovery=_word_usage_discovery(),
            decision_payload={
                "reviewer": "human",
                "decisions": [
                    {
                        "source_type": "candidate_axis",
                        "source_id": "contextual_meaning_mode",
                        "action": "promote_to_proto_field",
                        "target_layer": "business_feature_card",
                        "rationale": "keep as proto feature",
                    },
                    {
                        "source_type": "candidate_axis",
                        "source_id": "referent_resolution_mode",
                        "action": "map_to_prompt_guard",
                        "target_layer": "prompt_assets",
                        "rationale": "prompt should preserve contextual meaning",
                    },
                    {
                        "source_type": "distractor_taxonomy",
                        "source_id": "literal_meaning_trap",
                        "action": "map_to_validator_candidate",
                        "target_layer": "validator_contract",
                        "rationale": "candidate validator should flag literal traps",
                    },
                ],
            },
        )
        draft = build_formal_patch_draft(manifest=_word_usage_manifest(), axis_confirmation=confirmation)

        plan = build_formal_writeback_plan(formal_patch_draft=draft, reviewer="human")
        diff = render_formal_writeback_diff(plan)

        self.assertEqual(plan["status"], "preview_only")
        self.assertFalse(plan["writeback_allowed"])
        self.assertTrue(plan["requires_explicit_approval"])
        self.assertEqual(plan["proto_family"], "word_usage")
        self.assertEqual(plan["proto_child_family"], "word_usage_content_word")
        self.assertTrue(plan["writeback_items"])
        files = {item["target_file"] for item in plan["writeback_items"]}
        self.assertIn("card_specs/business_feature_slots/examples/word_usage_word_usage_content_word.proto.yaml", files)
        self.assertIn("prompt_skeleton_service/configs/prompt_templates.yaml", files)
        self.assertIn("card_specs/validator_contracts/proto/word_usage_word_usage_content_word.validator.yaml", files)
        self.assertIn("requires_regression", plan["legacy_family_impact"]["sentence_fill"])
        self.assertIn("Rollback", diff)
        self.assertIn("Prompt guards", diff)
        self.assertIn("Validator candidates", diff)
        self.assertIn("No files have been changed", diff)

    def test_formal_writeback_plan_run_writes_preview_artifacts_and_report(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            decisions_path = Path(tempdir) / "axis_decisions.json"
            decisions_path.write_text(
                json.dumps(
                    {
                        "reviewer": "human",
                        "proto_family_label": "word_usage",
                        "decisions": [
                            {
                                "source_type": "candidate_axis",
                                "source_id": "contextual_meaning_mode",
                                "action": "promote_to_proto_field",
                                "target_layer": "business_feature_card",
                            },
                            {
                                "source_type": "candidate_axis",
                                "source_id": "referent_resolution_mode",
                                "action": "map_to_prompt_guard",
                                "target_layer": "prompt_assets",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_bootstrap_discovery=True,
                    bootstrap_proto_family_label="word_usage",
                    enable_axis_confirmation=True,
                    axis_confirmation_decisions=decisions_path,
                    enable_formal_patch_draft=True,
                    enable_formal_writeback_plan=True,
                    writeback_plan_reviewer="human",
                )

            self.assertTrue(summary["formal_writeback_plan_enabled"])
            self.assertIn("formal_writeback_plan", summary["artifacts"])
            self.assertIn("formal_writeback_diff", summary["artifacts"])
            plan = json.loads((output_dir / "formal_writeback_plan.json").read_text(encoding="utf-8"))
            diff = (output_dir / "formal_writeback_diff.md").read_text(encoding="utf-8")
            report = (output_dir / "report.md").read_text(encoding="utf-8")

            self.assertFalse(plan["writeback_allowed"])
            self.assertTrue(plan["requires_explicit_approval"])
            self.assertIn("Formal Writeback Plan", report)
            self.assertIn("Formal Writeback Diff Preview", diff)
            self.assertIn("No files have been changed", diff)

    def test_formal_writeback_executor_rejects_missing_approval(self) -> None:
        plan = _writeback_plan_without_shared_targets()

        with TemporaryDirectory() as tempdir:
            with self.assertRaisesRegex(FormalWritebackError, "approval is required"):
                execute_formal_writeback(
                    plan=plan,
                    approval=None,
                    repo_root=tempdir,
                    output_dir=Path(tempdir) / "out",
                    regression_commands=[_python_ok_command()],
                )

    def test_formal_writeback_executor_rejects_incomplete_approval(self) -> None:
        plan = _writeback_plan_without_shared_targets()
        approval = {"approval_version": "v1", "approval_type": "formal_writeback", "approved": True}

        with TemporaryDirectory() as tempdir:
            with self.assertRaisesRegex(FormalWritebackError, "approved_at"):
                validate_writeback_approval(plan=plan, approval=approval, repo_root=tempdir)

    def test_formal_writeback_executor_rejects_shared_config_targets(self) -> None:
        plan = _writeback_plan_with_prompt_assets()
        approval = _approval_for_plan(plan)

        with TemporaryDirectory() as tempdir:
            with self.assertRaisesRegex(FormalWritebackError, "shared config target"):
                validate_writeback_approval(plan=plan, approval=approval, repo_root=tempdir)

    def test_formal_writeback_executor_writes_only_allowlist_proto_files_with_patches_manifest_and_regressions(self) -> None:
        plan = _writeback_plan_without_shared_targets()
        approval = _approval_for_plan(plan)

        with TemporaryDirectory() as tempdir:
            repo = Path(tempdir) / "repo"
            repo.mkdir()
            guarded_files = [
                repo / "prompt_skeleton_service" / "configs" / "prompt_templates.yaml",
                repo / "prompt_skeleton_service" / "app" / "services" / "question_generation.py",
                repo / "prompt_skeleton_service" / "app" / "services" / "question_validator.py",
            ]
            for guarded_file in guarded_files:
                guarded_file.parent.mkdir(parents=True, exist_ok=True)
                guarded_file.write_text("UNCHANGED\n", encoding="utf-8")

            out = Path(tempdir) / "out"
            result = execute_formal_writeback(
                plan=plan,
                approval=approval,
                repo_root=repo,
                output_dir=out,
                regression_commands=[_python_ok_command()],
            )

            self.assertEqual(result["status"], "succeeded")
            manifest = json.loads((out / "formal_writeback_manifest.json").read_text(encoding="utf-8"))
            regression_report = json.loads((out / "formal_writeback_regression_report.json").read_text(encoding="utf-8"))
            forward_patch = (out / "formal_writeback_forward.patch").read_text(encoding="utf-8")
            rollback_patch = (out / "formal_writeback_rollback.patch").read_text(encoding="utf-8")

            self.assertTrue(regression_report["passed"])
            self.assertEqual(regression_report["command_count"], 1)
            self.assertIn("new file mode", forward_patch)
            self.assertIn("deleted file mode", rollback_patch)
            self.assertEqual({item["path"] for item in manifest["files"]}, set(approval["approval_scope"]["allowed_files"]))
            for relative_file in approval["approval_scope"]["allowed_files"]:
                written = repo / relative_file
                self.assertTrue(written.exists())
                text = written.read_text(encoding="utf-8")
                self.assertIn("formal_writeback_executor", text)
                self.assertIn("experimental: true", text)
                self.assertIn("formalized: false", text)

            for guarded_file in guarded_files:
                self.assertEqual(guarded_file.read_text(encoding="utf-8"), "UNCHANGED\n")

    def test_formal_writeback_executor_rejects_non_allowlist_path(self) -> None:
        plan = _writeback_plan_without_shared_targets()
        plan["writeback_items"][0]["target_file"] = "prompt_skeleton_service/configs/prompt_templates.yaml"
        approval = _approval_for_plan(plan)

        with TemporaryDirectory() as tempdir:
            with self.assertRaisesRegex(FormalWritebackError, "outside allowlist"):
                validate_writeback_approval(plan=plan, approval=approval, repo_root=tempdir)

    def test_truth_gold_regression_gold_only_writes_split_results_and_report(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            samples = [_word_usage_sample(str(index)) for index in range(10)]
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=samples):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_truth_gold_regression=True,
                    truth_gold_split_seed=7,
                )

            self.assertTrue(summary["truth_gold_regression_enabled"])
            self.assertIn("truth_gold_split_manifest", summary["artifacts"])
            self.assertIn("truth_gold_regression_results", summary["artifacts"])
            self.assertIn("truth_gold_regression_report", summary["artifacts"])
            split_manifest = json.loads((output_dir / "truth_gold_split_manifest.json").read_text(encoding="utf-8"))
            results = json.loads((output_dir / "truth_gold_regression_results.json").read_text(encoding="utf-8"))
            report = (output_dir / "truth_gold_regression_report.md").read_text(encoding="utf-8")
            main_report = (output_dir / "report.md").read_text(encoding="utf-8")

            self.assertEqual(sum(split_manifest["split_counts"].values()), 10)
            self.assertGreater(split_manifest["split_counts"]["insurance_holdout"], 0)
            self.assertEqual(results["mode"], "gold_only_baseline")
            self.assertEqual(results["gold_source"], "raw_samples")
            self.assertEqual(results["sample_results"], [])
            self.assertIn("Truth Gold Regression", report)
            self.assertIn("Truth Gold Regression", main_report)
            self.assertFalse(results["summary"]["ready_for_formalization"])

    def test_truth_gold_regression_generated_comparison_flags_high_overfit(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            samples = [_word_usage_sample(str(index)) for index in range(8)]
            generated_path = Path(tempdir) / "generated_items.jsonl"
            generated_rows = [
                {
                    "sample_id": sample["sample_id"],
                    "generated": {
                        "stem": sample["stem"],
                        "answer": sample["answer"],
                        "analysis": sample["analysis"],
                        "passage": sample.get("raw_text", ""),
                        "metadata": {"difficulty_signal": sample.get("correct_rate")},
                    },
                }
                for sample in samples
            ]
            generated_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in generated_rows), encoding="utf-8")
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=samples):
                run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_truth_gold_regression=True,
                    truth_gold_generated_items=generated_path,
                )

            results = json.loads((output_dir / "truth_gold_regression_results.json").read_text(encoding="utf-8"))

            self.assertEqual(results["mode"], "generated_comparison")
            self.assertEqual(len(results["sample_results"]), 8)
            self.assertEqual(results["dimensions"]["overfit_risk"]["score"], 1.0)
            self.assertEqual(results["summary"]["fit_type"], "surface_fit_high_overfit_risk")
            self.assertTrue(any((item["scores"]["overfit_risk"]["band"] == "high") for item in results["sample_results"]))

    def test_artifact_contract_documents_truth_gold_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")

        self.assertIn("truth_gold_split_manifest.json", contract)
        self.assertIn("truth_gold_regression_results.json", contract)
        self.assertIn("truth_gold_regression_report.md", contract)
        self.assertIn("not formal writeback approval", contract)

    def test_gold_reconstruction_dry_run_writes_model_safe_input_only(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            sample = _word_usage_sample("1")
            sample["raw_text"] = "X" * 80
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[sample]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="dry-run",
                    gold_reconstruction_max_input_chars=30,
                )

            self.assertTrue(summary["gold_reconstruction_enabled"])
            self.assertEqual(summary["gold_reconstruction_mode"], "dry-run")
            self.assertIn("model_safe_gold_reconstruction_input", summary["artifacts"])
            self.assertNotIn("gold_reconstruction_results", summary["artifacts"])
            row = json.loads((output_dir / "model_safe_gold_reconstruction_input.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("input_hash", row)
            self.assertTrue(row["truncation"]["truncated"])
            self.assertLessEqual(len(row["raw_question_block"]), 30)
            self.assertNotIn("OUTPUT_SCHEMA", row["raw_question_block"])

    def test_gold_reconstruction_mock_generates_unified_schema_and_report(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="mock",
                )

            self.assertIn("gold_reconstruction_results", summary["artifacts"])
            self.assertIn("gold_reconstruction_report", summary["artifacts"])
            result = json.loads((output_dir / "gold_reconstruction_results.jsonl").read_text(encoding="utf-8").splitlines()[0])
            for key in (
                "sample_id",
                "reconstruction_summary",
                "gold_material",
                "gold_question",
                "answer_mechanism",
                "distractor_mechanism",
                "gold_quality_flags",
                "mechanical_checks",
                "source",
            ):
                self.assertIn(key, result)
            self.assertIn(result["reconstruction_summary"]["confidence"], {"high", "medium", "low"})
            self.assertIsInstance(result["reconstruction_summary"]["needs_human_review"], bool)
            self.assertIsInstance(result["reconstruction_summary"]["warnings"], list)
            result_text = json.dumps(result, ensure_ascii=False)
            self.assertNotIn("confirmed_fields", result_text)
            self.assertNotIn("validator_rules", result_text)
            self.assertNotIn("prompt_guards", result_text)
            self.assertNotIn("card_specs", result_text)
            report = (output_dir / "gold_reconstruction_report.md").read_text(encoding="utf-8")
            self.assertIn("Confidence Distribution", report)
            self.assertIn("needs_human_review_count", report)

    def test_gold_reconstruction_invalid_model_json_marks_sample_for_human_review(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="llm",
                    gold_reconstruction_client=_FakeClient("not json"),
                )

            result = json.loads((output_dir / "gold_reconstruction_results.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertTrue(result["reconstruction_summary"]["needs_human_review"])
            self.assertFalse(result["mechanical_checks"]["json_parse_ok"])
            self.assertIn("raw_model_error", result["source"])
            self.assertIn("mechanical_checks", result)
            self.assertNotIn("semantic_correct", result["mechanical_checks"])

    def test_gold_reconstruction_retries_one_transient_llm_failure(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            client = _FlakyClient(json.dumps(_natural_gold_reconstruction_payload(), ensure_ascii=False))
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="实词",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="llm",
                    gold_reconstruction_client=client,
                )

            result = json.loads((output_dir / "gold_reconstruction_results.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(len(client.calls), 2)
            self.assertTrue(result["mechanical_checks"]["json_parse_ok"])

    def test_gold_reconstruction_prompt_forbids_question_wrapper_in_restored_text(self) -> None:
        messages = build_gold_reconstruction_messages(
            {
                "sample_id": "sample-1",
                "raw_question_block": "下列对文中加点词理解正确的是",
                "stem": "下列对文中加点词理解正确的是",
                "options": {},
            }
        )
        prompt_text = "\n".join(message["content"] for message in messages)

        self.assertIn("gold_material.restored_text is only for natural source-like material", prompt_text)
        self.assertIn("Forbidden in gold_material.restored_text", prompt_text)
        self.assertIn("下列", prompt_text)
        self.assertIn("答案解析", prompt_text)
        self.assertIn("question_wrapper_leakage_risk", prompt_text)

    def test_gold_reconstruction_marks_question_wrapper_leakage(self) -> None:
        input_row = {
            "sample_id": "sample-1",
            "input_hash": "hash",
            "stem": "下列对文中加点词理解正确的是",
            "options": {"A": "正确解释", "B": "错误解释"},
            "answer": "A",
        }
        payload = _natural_gold_reconstruction_payload()
        payload["gold_material"]["restored_text"] = "下列对文中加点词理解正确的是，这里混入了题干包装。"

        result = normalize_gold_reconstruction(payload, input_row=input_row, model="mock", mode="mock")

        self.assertEqual(result["gold_quality_flags"]["question_wrapper_leakage_risk"], "high")
        self.assertTrue(result["reconstruction_summary"]["needs_human_review"])
        self.assertIn("restored_text_contains_question_wrapper_terms", result["reconstruction_summary"]["warnings"])

    def test_apply_question_wrapper_leakage_check_is_structural_only(self) -> None:
        payload = {
            "reconstruction_summary": {"needs_human_review": False, "warnings": []},
            "gold_material": {"restored_text": "自然材料句子，没有题目包装词。"},
            "gold_quality_flags": {},
        }

        risk = apply_question_wrapper_leakage_check(payload)

        self.assertEqual(risk, "low")
        self.assertEqual(payload["gold_quality_flags"]["question_wrapper_leakage_risk"], "low")
        self.assertNotIn("semantic_correct", payload)

    def test_truth_gold_regression_prefers_reconstructed_gold_when_available(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            samples = [_word_usage_sample(str(index)) for index in range(4)]
            generated_path = Path(tempdir) / "generated_items.jsonl"
            generated_path.write_text(
                "".join(
                    json.dumps(
                        {
                            "sample_id": sample["sample_id"],
                            "generated": {
                                "stem": sample["stem"],
                                "answer": sample["answer"],
                                "analysis": sample["analysis"],
                                "passage": sample.get("raw_text", ""),
                            },
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                    for sample in samples
                ),
                encoding="utf-8",
            )
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=samples):
                run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="mock",
                    enable_truth_gold_regression=True,
                    truth_gold_generated_items=generated_path,
                )

            results = json.loads((output_dir / "truth_gold_regression_results.json").read_text(encoding="utf-8"))
            self.assertEqual(results["gold_source"], "gold_reconstruction_results")
            self.assertTrue(results["sample_results"])
            self.assertTrue(all(item["gold_reconstruction"]["available"] for item in results["sample_results"]))

    def test_artifact_contract_documents_gold_reconstruction_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")

        self.assertIn("model_safe_gold_reconstruction_input.jsonl", contract)
        self.assertIn("gold_reconstruction_results.jsonl", contract)
        self.assertIn("gold_reconstruction_report.md", contract)
        self.assertIn("not formal card", contract)

    def test_truth_gold_regression_can_run_from_existing_artifact_dir(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(json.dumps(_word_usage_manifest(), ensure_ascii=False), encoding="utf-8")
            samples = [_word_usage_sample(str(index)) for index in range(6)]
            (artifact_dir / "samples.jsonl").write_text(
                "".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in samples),
                encoding="utf-8",
            )

            artifacts = run_truth_gold_regression_from_artifact_dir(artifact_dir=artifact_dir)

            self.assertTrue(Path(artifacts["truth_gold_split_manifest"]).exists())
            self.assertTrue(Path(artifacts["truth_gold_regression_results"]).exists())
            self.assertTrue(Path(artifacts["truth_gold_regression_report"]).exists())

    def test_source_discovery_prep_blocked_without_reconstruction_and_no_raw_fallback(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(json.dumps(_word_usage_manifest(), ensure_ascii=False), encoding="utf-8")
            samples = [_word_usage_sample("1")]
            (artifact_dir / "samples.jsonl").write_text(
                "".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in samples),
                encoding="utf-8",
            )

            artifacts = run_source_discovery_preparation_from_artifact_dir(artifact_dir=artifact_dir)

            profile = json.loads(Path(artifacts["material_source_profile"]).read_text(encoding="utf-8"))
            report = Path(artifacts["source_discovery_preparation_report"]).read_text(encoding="utf-8")
            self.assertEqual(profile["status"], "blocked")
            self.assertEqual(profile["gold_source"], "missing")
            self.assertFalse(profile["material_line_conclusion"]["ready_for_source_discovery"])
            self.assertIn("gold_reconstruction_results.jsonl", report)
            self.assertEqual(Path(artifacts["source_discovery_queries"]).read_text(encoding="utf-8"), "")

    def test_source_discovery_prep_uses_reconstructed_gold_and_writes_artifacts(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            sample = _word_usage_sample("1")
            sample["raw_text"] = "城市更新需要保留街区肌理。老厂房改造后，公共空间被重新激活，居民在新的步道上交流。"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[sample]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="实词",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="mock",
                    enable_source_discovery_prep=True,
                )

            self.assertTrue(summary["source_discovery_prep_enabled"])
            self.assertIn("source_discovery_queries", summary["artifacts"])
            self.assertIn("material_source_profile", summary["artifacts"])
            self.assertIn("initial_material_seed_pack", summary["artifacts"])
            self.assertIn("source_discovery_preparation_report", summary["artifacts"])
            query_rows = [
                json.loads(line)
                for line in (output_dir / "source_discovery_queries.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            seed_rows = [
                json.loads(line)
                for line in (output_dir / "initial_material_seed_pack.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            profile = json.loads((output_dir / "material_source_profile.json").read_text(encoding="utf-8"))
            report = (output_dir / "source_discovery_preparation_report.md").read_text(encoding="utf-8")
            main_report = (output_dir / "report.md").read_text(encoding="utf-8")

            self.assertEqual(query_rows[0]["gold_source"], "gold_reconstruction_results")
            self.assertTrue(query_rows[0]["search_queries"])
            for query in query_rows[0]["search_queries"]:
                self.assertNotIn("下列", query["query"])
                self.assertNotIn("答案解析", query["query"])
                self.assertNotIn("本题考查", query["query"])
                self.assertNotIn("正确的是", query["query"])
            self.assertEqual(profile["gold_source"], "gold_reconstruction_results")
            self.assertEqual(seed_rows[0]["status"], "seed_only")
            self.assertFalse(seed_rows[0]["formalized"])
            self.assertIn("Restored Human Material Examples", report)
            self.assertIn("Search Query Examples", report)
            self.assertIn("Source Discovery Preparation", main_report)

    def test_source_discovery_raw_fallback_marks_high_risk(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(json.dumps(_word_usage_manifest(), ensure_ascii=False), encoding="utf-8")
            sample = _word_usage_sample("1")
            sample["stem"] = "下列对加点词理解正确的是哪一项？"
            sample["analysis"] = "答案解析：本题考查词语理解。"
            (artifact_dir / "samples.jsonl").write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")

            artifacts = run_source_discovery_preparation_from_artifact_dir(
                artifact_dir=artifact_dir,
                use_raw_fallback=True,
            )

            query_rows = [
                json.loads(line)
                for line in Path(artifacts["source_discovery_queries"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(query_rows[0]["gold_source"], "raw_samples")
            self.assertTrue(query_rows[0]["using_raw_sample_material"])
            self.assertEqual(query_rows[0]["question_bank_contamination_risk"], "high")
            self.assertTrue(query_rows[0]["needs_human_review"])

    def test_source_discovery_leakage_high_raises_contamination_risk(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(json.dumps(_word_usage_manifest(), ensure_ascii=False), encoding="utf-8")
            sample = _word_usage_sample("1")
            (artifact_dir / "samples.jsonl").write_text(json.dumps(sample, ensure_ascii=False) + "\n", encoding="utf-8")
            reconstruction = _natural_gold_reconstruction_payload()
            reconstruction["sample_id"] = sample["sample_id"]
            reconstruction["gold_material"]["restored_text"] = "下列对文中加点词理解正确的是，这句话不是自然原文。"
            reconstruction = normalize_gold_reconstruction(
                reconstruction,
                input_row={
                    "sample_id": sample["sample_id"],
                    "input_hash": "hash",
                    "stem": sample["stem"],
                    "options": sample["options"],
                    "answer": sample["answer"],
                },
                model="mock",
                mode="mock",
            )
            (artifact_dir / "gold_reconstruction_results.jsonl").write_text(
                json.dumps(reconstruction, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            artifacts = run_source_discovery_preparation_from_artifact_dir(artifact_dir=artifact_dir)

            query_rows = [
                json.loads(line)
                for line in Path(artifacts["source_discovery_queries"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(query_rows[0]["question_bank_contamination_risk"], "high")
            self.assertTrue(query_rows[0]["needs_human_review"])
            self.assertIn("restored_text_contains_question_wrapper_terms", query_rows[0]["warnings"])
            for query in query_rows[0]["search_queries"]:
                self.assertEqual(query["confidence"], "low")

    def test_artifact_contract_documents_source_discovery_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")

        self.assertIn("source_discovery_queries.jsonl", contract)
        self.assertIn("material_source_profile.json", contract)
        self.assertIn("initial_material_seed_pack.jsonl", contract)
        self.assertIn("source_discovery_preparation_report.md", contract)
        self.assertIn("not formal material cards", contract)

    def test_source_candidate_search_disabled_by_default_in_leaf_run(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                )

            self.assertFalse(summary["source_candidate_search_enabled"])
            self.assertNotIn("search_request_manifest", summary["artifacts"])
            self.assertFalse((output_dir / "source_candidate_results.jsonl").exists())

    def test_source_candidate_search_dry_run_writes_manifest_only_candidates_empty(self) -> None:
        with TemporaryDirectory() as tempdir:
            queries_path = _write_source_discovery_queries(Path(tempdir))
            output_dir = Path(tempdir) / "candidate"

            artifacts = run_source_candidate_search_from_queries(
                source_discovery_queries_path=queries_path,
                output_dir=output_dir,
                max_samples=1,
                max_queries_per_sample=2,
                dry_run=True,
                run_search=False,
                search_provider="manual",
            )

            manifest = json.loads(Path(artifacts["search_request_manifest"]).read_text(encoding="utf-8"))
            summary = json.loads(Path(artifacts["source_candidate_summary"]).read_text(encoding="utf-8"))
            self.assertFalse(manifest["run_search"])
            self.assertEqual(manifest["provider"], "manual")
            self.assertEqual(manifest["query_count"], 2)
            self.assertEqual(Path(artifacts["source_candidate_results"]).read_text(encoding="utf-8"), "")
            self.assertFalse(summary["ready_for_material_card_draft"])
            self.assertIn("no source candidates collected", summary["main_blockers"])

    def test_source_candidate_search_mock_provider_writes_unverified_candidates(self) -> None:
        with TemporaryDirectory() as tempdir:
            queries_path = _write_source_discovery_queries(Path(tempdir))
            output_dir = Path(tempdir) / "candidate"

            artifacts = run_source_candidate_search_from_queries(
                source_discovery_queries_path=queries_path,
                output_dir=output_dir,
                max_samples=1,
                max_queries_per_sample=1,
                max_results_per_query=2,
                dry_run=False,
                run_search=True,
                search_provider="mock",
                provider=MockSearchProvider(),
            )

            rows = [
                json.loads(line)
                for line in Path(artifacts["source_candidate_results"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            summary = json.loads(Path(artifacts["source_candidate_summary"]).read_text(encoding="utf-8"))
            report = Path(artifacts["source_candidate_alignment_report"]).read_text(encoding="utf-8")
            self.assertEqual(len(rows), 2)
            self.assertTrue(any(row["source_risk"] in {"question_bank_like", "exam_training_like"} for row in rows))
            for row in rows:
                self.assertFalse(row["verified"])
                self.assertEqual(row["verification_status"], "unverified")
            self.assertTrue(summary["ready_for_human_source_review"])
            self.assertFalse(summary["ready_for_material_card_draft"])
            self.assertIn("Source Candidate Alignment Report", report)
            self.assertIn("Candidates are unverified", report)

    def test_source_candidate_search_marks_exam_training_domain_as_risky(self) -> None:
        risk = classify_source_risk(
            title="言语理解答案解析",
            url="https://www.offcn.com/tiku/example.html",
            domain="www.offcn.com",
            snippet="本题考查行测，正确答案见解析。",
        )

        self.assertIn(risk, {"question_bank_like", "exam_training_like"})

    def test_source_candidate_search_parses_web_provider_html_results(self) -> None:
        html = """
        <div class="result">
          <a class="result__a" href="/l/?uddg=https%3A%2F%2Fwww.xinhuanet.com%2Fpolitics%2Fexample.html">新华网文章标题</a>
          <a class="result__snippet">这里是自然文章摘要，不是题库解析。</a>
        </div>
        """

        results = parse_duckduckgo_html_results(html)

        self.assertEqual(results[0]["title"], "新华网文章标题")
        self.assertEqual(results[0]["url"], "https://www.xinhuanet.com/politics/example.html")
        self.assertIn("自然文章摘要", results[0]["snippet"])

    def test_source_candidate_search_parses_bing_html_results(self) -> None:
        html = """
        <li class="b_algo">
          <h2><a href="https://www.gmw.cn/example.html">光明网评论文章</a></h2>
          <div class="b_caption"><p>这是一段自然文章摘要。</p></div>
        </li>
        """

        results = parse_bing_html_results(html)

        self.assertEqual(results[0]["title"], "光明网评论文章")
        self.assertEqual(results[0]["url"], "https://www.gmw.cn/example.html")
        self.assertIn("自然文章摘要", results[0]["snippet"])

    def test_source_candidate_search_can_attach_to_main_report(self) -> None:
        with TemporaryDirectory() as tempdir:
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            sample = _word_usage_sample("1")
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[sample]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="瀹炶瘝",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_gold_reconstruction=True,
                    gold_reconstruction_mode="mock",
                    enable_source_discovery_prep=True,
                    enable_source_candidate_search=True,
                    source_candidate_provider="mock",
                    source_candidate_dry_run=False,
                    source_candidate_run_search=True,
                    source_candidate_max_samples=1,
                    source_candidate_max_queries_per_sample=1,
                    source_candidate_max_results_per_query=2,
                )

            report = (output_dir / "report.md").read_text(encoding="utf-8")
            self.assertTrue(summary["source_candidate_search_enabled"])
            self.assertIn("search_request_manifest", summary["artifacts"])
            self.assertIn("source_candidate_results", summary["artifacts"])
            self.assertIn("source_candidate_summary", summary["artifacts"])
            self.assertIn("source_candidate_alignment_report", summary["artifacts"])
            self.assertIn("Source Candidate Search", report)
            self.assertIn("ready_for_material_card_draft: `False`", report)
            self.assertFalse((Path(tempdir) / "card_specs").exists())

    def test_artifact_contract_documents_source_candidate_search_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")

        self.assertIn("search_request_manifest.json", contract)
        self.assertIn("source_candidate_results.jsonl", contract)
        self.assertIn("source_candidate_summary.json", contract)
        self.assertIn("source_candidate_alignment_report.md", contract)
        self.assertIn("Candidate sources are not verified original sources", contract)

    def test_source_candidate_review_generates_review_seed_registry_and_manifest(self) -> None:
        with TemporaryDirectory() as tempdir:
            candidate_path = _write_source_candidate_results(Path(tempdir))
            decision_path = _write_source_candidate_review_decisions(Path(tempdir))
            output_dir = Path(tempdir) / "review"

            artifacts = run_source_candidate_review(
                source_candidate_results_path=candidate_path,
                review_decisions_path=decision_path,
                output_dir=output_dir,
            )

            review = json.loads(Path(artifacts["source_candidate_review"]).read_text(encoding="utf-8"))
            seeds = [
                json.loads(line)
                for line in Path(artifacts["source_seed_registry"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            crawl = json.loads(Path(artifacts["crawl_seed_manifest"]).read_text(encoding="utf-8"))
            report = Path(artifacts["source_candidate_human_review_report"]).read_text(encoding="utf-8")

            self.assertEqual(review["accepted_count"], 2)
            self.assertEqual(review["rejected_count"], 2)
            self.assertEqual(review["deferred_count"], 1)
            self.assertEqual(review["verified_original_source_count"], 0)
            self.assertEqual(len(seeds), 2)
            self.assertFalse(crawl["crawl_allowed"])
            self.assertFalse(crawl["recommended_limits"]["fetch_body"])
            self.assertFalse(crawl["ready_for_material_card_draft"])
            self.assertIn("Accepted Similar Material Seeds", report)
            self.assertIn("Rejected Question-Bank", report)
            self.assertFalse((Path(tempdir) / "card_specs").exists())

    def test_source_candidate_review_preserves_unverified_boundaries_for_accepted_seeds(self) -> None:
        with TemporaryDirectory() as tempdir:
            candidate_path = _write_source_candidate_results(Path(tempdir))
            decision_path = _write_source_candidate_review_decisions(Path(tempdir))
            output_dir = Path(tempdir) / "review"

            artifacts = run_source_candidate_review(
                source_candidate_results_path=candidate_path,
                review_decisions_path=decision_path,
                output_dir=output_dir,
            )

            review = json.loads(Path(artifacts["source_candidate_review"]).read_text(encoding="utf-8"))
            seeds = [
                json.loads(line)
                for line in Path(artifacts["source_seed_registry"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            for item in review["reviewed_candidates"]:
                self.assertFalse(item["verified"])
                self.assertFalse(item["verified_original_source"])
            for seed in seeds:
                self.assertEqual(seed["status"], "seed_only")
                self.assertFalse(seed["formalized"])
                self.assertFalse(seed["verified"])
                self.assertFalse(seed["verified_original_source"])
                self.assertEqual(seed["verification_status"], "human_reviewed_unverified")

    def test_source_candidate_review_rejects_risky_seed_without_explicit_allowance(self) -> None:
        with TemporaryDirectory() as tempdir:
            candidate_path = _write_source_candidate_results(Path(tempdir))
            decisions = {
                "review_version": "v1",
                "reviewer": "human",
                "decisions": [
                    {
                        "sample_id": "sample-1",
                        "url": "https://www.offcn.com/tiku/a.html",
                        "decision": "keep_as_similar_material_seed",
                        "source_use": "similar_material",
                        "rationale": "risky fixture",
                    }
                ],
            }
            decision_path = Path(tempdir) / "decisions.json"
            decision_path.write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")

            artifacts = run_source_candidate_review(
                source_candidate_results_path=candidate_path,
                review_decisions_path=decision_path,
                output_dir=Path(tempdir) / "review",
            )

            review = json.loads(Path(artifacts["source_candidate_review"]).read_text(encoding="utf-8"))
            seeds_text = Path(artifacts["source_seed_registry"]).read_text(encoding="utf-8")
            self.assertEqual(seeds_text, "")
            self.assertIn("risky_candidate_seed_rejected_without_explicit_allowance", review["warnings"])

    def test_source_candidate_review_can_accept_risky_seed_only_with_explicit_allowance(self) -> None:
        with TemporaryDirectory() as tempdir:
            candidate_path = _write_source_candidate_results(Path(tempdir))
            decisions = {
                "review_version": "v1",
                "reviewer": "human",
                "decisions": [
                    {
                        "sample_id": "sample-1",
                        "url": "https://www.offcn.com/tiku/a.html",
                        "decision": "keep_as_similar_material_seed",
                        "source_use": "similar_material",
                        "crawl_priority": "high",
                        "allow_risky_seed": True,
                        "rationale": "retain only for audit fixture",
                    }
                ],
            }
            decision_path = Path(tempdir) / "decisions.json"
            decision_path.write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")

            artifacts = run_source_candidate_review(
                source_candidate_results_path=candidate_path,
                review_decisions_path=decision_path,
                output_dir=Path(tempdir) / "review",
                allow_risky_seeds=True,
            )

            seeds = [
                json.loads(line)
                for line in Path(artifacts["source_seed_registry"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            review = json.loads(Path(artifacts["source_candidate_review"]).read_text(encoding="utf-8"))
            self.assertEqual(len(seeds), 1)
            self.assertIn("risky_seed_accepted_by_human", seeds[0]["warnings"])
            self.assertEqual(review["risky_accepted_seed_count"], 1)

    def test_source_candidate_review_unknown_candidate_does_not_generate_seed(self) -> None:
        with TemporaryDirectory() as tempdir:
            candidate_path = _write_source_candidate_results(Path(tempdir))
            decisions = {
                "review_version": "v1",
                "reviewer": "human",
                "decisions": [
                    {
                        "sample_id": "missing",
                        "url": "https://example.com/missing.html",
                        "decision": "keep_as_similar_material_seed",
                        "source_use": "similar_material",
                        "rationale": "unknown should not be accepted",
                    }
                ],
            }
            decision_path = Path(tempdir) / "decisions.json"
            decision_path.write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")

            artifacts = run_source_candidate_review(
                source_candidate_results_path=candidate_path,
                review_decisions_path=decision_path,
                output_dir=Path(tempdir) / "review",
            )

            review = json.loads(Path(artifacts["source_candidate_review"]).read_text(encoding="utf-8"))
            self.assertEqual(Path(artifacts["source_seed_registry"]).read_text(encoding="utf-8"), "")
            self.assertIn("unknown_candidate_rejected", review["warnings"])

    def test_source_candidate_review_can_attach_to_main_report(self) -> None:
        with TemporaryDirectory() as tempdir:
            candidate_path = _write_source_candidate_results(Path(tempdir))
            decision_path = _write_source_candidate_review_decisions(Path(tempdir))
            source_file = Path(tempdir) / "sample.docx"
            source_file.write_text("placeholder", encoding="utf-8")
            output_dir = Path(tempdir) / "out"
            with patch("tools.leaf_pre_distill.run.parse_docx_pack", return_value=[_word_usage_sample("1")]):
                summary = run_leaf_pre_distill(
                    mother_family_id="word_usage",
                    child_family_id="word_usage_content_word",
                    leaf_label="实词",
                    source_files=[str(source_file)],
                    output_dir=output_dir,
                    enable_source_candidate_review=True,
                    source_candidate_results_path=candidate_path,
                    source_candidate_review_decisions=decision_path,
                )

            report = (output_dir / "report.md").read_text(encoding="utf-8")
            self.assertTrue(summary["source_candidate_review_enabled"])
            self.assertIn("source_candidate_review", summary["artifacts"])
            self.assertIn("source_seed_registry", summary["artifacts"])
            self.assertIn("crawl_seed_manifest", summary["artifacts"])
            self.assertIn("source_candidate_human_review_report", summary["artifacts"])
            self.assertIn("Source Candidate Human Review", report)
            self.assertIn("ready_for_material_card_draft: `False`", report)

    def test_artifact_contract_documents_source_candidate_review_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")

        self.assertIn("source_candidate_review_decisions.json", contract)
        self.assertIn("source_candidate_review.json", contract)
        self.assertIn("source_seed_registry.jsonl", contract)
        self.assertIn("crawl_seed_manifest.json", contract)
        self.assertIn("source_candidate_human_review_report.md", contract)
        self.assertIn("Source seed is not material library", contract)

    def test_material_evidence_alignment_regression_generates_three_gates(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            seed_path = _write_source_seed_registry(root)
            approval_path = _write_source_text_evidence_approval(root)
            gold_path = _write_gold_reconstruction_results_for_material_evidence(root)
            output_dir = root / "material_evidence"

            artifacts = run_material_evidence_alignment_regression(
                output_dir=output_dir,
                source_seed_registry_path=seed_path,
                source_text_evidence_approval_path=approval_path,
                gold_reconstruction_results_path=gold_path,
                source_text_mode="mock",
                alignment_mode="mock",
            )

            self.assertIn("source_text_evidence_results", artifacts)
            self.assertIn("source_gold_alignment_results", artifacts)
            self.assertIn("material_quality_regression_results", artifacts)
            source_rows = [json.loads(line) for line in Path(artifacts["source_text_evidence_results"]).read_text(encoding="utf-8").splitlines()]
            alignment_rows = [json.loads(line) for line in Path(artifacts["source_gold_alignment_results"]).read_text(encoding="utf-8").splitlines()]
            quality = json.loads(Path(artifacts["material_quality_regression_results"]).read_text(encoding="utf-8"))
            self.assertTrue(source_rows)
            self.assertTrue(alignment_rows)
            self.assertFalse(any(row.get("verified") for row in source_rows))
            self.assertFalse(any(row.get("verified_original_source") for row in source_rows))
            self.assertFalse(any(row.get("verified_original_source") for row in alignment_rows))
            self.assertEqual(quality["ready_for_material_card_formalization"], False)
            self.assertIn("source_gold_alignment", " ".join(item["dimension"] for item in quality["dimensions"]))

    def test_material_evidence_regression_blocked_when_text_unavailable(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            seed_path = _write_source_seed_registry(root)
            approval_path = _write_source_text_evidence_approval(root)
            gold_path = _write_gold_reconstruction_results_for_material_evidence(root)
            output_dir = root / "material_evidence"

            artifacts = run_material_evidence_alignment_regression(
                output_dir=output_dir,
                source_seed_registry_path=seed_path,
                source_text_evidence_approval_path=approval_path,
                gold_reconstruction_results_path=gold_path,
                source_text_mode="manual",
                alignment_mode="mock",
            )

            source_manifest = json.loads(Path(artifacts["source_text_evidence_manifest"]).read_text(encoding="utf-8"))
            quality = json.loads(Path(artifacts["material_quality_regression_results"]).read_text(encoding="utf-8"))
            self.assertGreater(source_manifest["manual_required_count"], 0)
            self.assertEqual(quality["status"], "blocked")

    def test_material_alignment_llm_cannot_verify_source(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            seed_path = _write_source_seed_registry(root)
            approval_path = _write_source_text_evidence_approval(root)
            gold_path = _write_gold_reconstruction_results_for_material_evidence(root)
            manual_path = root / "manual_source_texts.jsonl"
            manual_path.write_text(
                json.dumps(
                    {
                        "seed_id": "source_seed_city",
                        "text": "城市更新需要保留街区肌理，修复公共空间，让居民重新建立联系。",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            fake = _FakeClient(
                json.dumps(
                    {
                        "alignment_status": "aligned",
                        "relationship": "original_source_candidate",
                        "confidence": "high",
                        "verified": True,
                        "verified_original_source": True,
                        "matched_spans": [{"source_excerpt": "城市更新", "gold_excerpt": "城市更新", "note": "same topic"}],
                        "transformation_hypothesis": {"possible_extraction": True, "notes": "model overclaim"},
                        "warnings": [],
                    },
                    ensure_ascii=False,
                )
            )

            artifacts = run_material_evidence_alignment_regression(
                output_dir=root / "material_evidence",
                source_seed_registry_path=seed_path,
                source_text_evidence_approval_path=approval_path,
                source_text_manual_results_path=manual_path,
                gold_reconstruction_results_path=gold_path,
                source_text_mode="manual",
                alignment_mode="llm",
                alignment_client=fake,
            )

            rows = [json.loads(line) for line in Path(artifacts["source_gold_alignment_results"]).read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["relationship"], "original_source_candidate")
            self.assertFalse(rows[0]["verified"])
            self.assertFalse(rows[0]["verified_original_source"])
            self.assertFalse(rows[0]["formalized"])
            self.assertTrue(rows[0]["requires_human_review"])
            self.assertIn("model_verification_claim_ignored", rows[0]["warnings"])

    def test_material_evidence_report_renderer_sections(self) -> None:
        report = render_markdown_report(
            manifest={"leaf_label": "demo", "job_id": "job", "mother_family_id": "demo_family", "clean_leaf_boundary": True},
            candidate_report={"sample_count": 1, "field_candidates": [], "summary": {}},
            slot_projection={},
            source_text_evidence={"status": "completed", "result_count": 1, "blocked_count": 0, "requires_human_review": True, "verified_original_source_count": 0, "ready_for_source_gold_alignment": True},
            source_gold_alignment={"status": "completed", "alignment_count": 1, "blocked_count": 0, "needs_human_review_count": 1, "verified_original_source_count": 0, "ready_for_material_quality_regression": True},
            material_quality_regression={"status": "blocked", "dimensions": [{"dimension": "source_provenance_status"}], "blocking_issues": ["source_provenance_status"], "requires_human_review": True, "verified_original_source_count": 0, "ready_for_material_card_formalization": False, "recommended_next_action": "human_material_review"},
        )
        self.assertIn("Source Text Evidence", report)
        self.assertIn("Source/Gold Alignment", report)
        self.assertIn("Material Quality Regression", report)

    def test_artifact_contract_documents_material_evidence_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")
        for name in (
            "source_text_evidence_approval.json",
            "source_text_evidence_manifest.json",
            "source_text_evidence_results.jsonl",
            "source_gold_alignment_results.jsonl",
            "source_gold_alignment_summary.json",
            "material_quality_regression_results.json",
            "source_gold_alignment_review.json",
            "material_quality_review.json",
        ):
            self.assertIn(name, contract)
        self.assertIn("not source verification", contract)
        self.assertIn("not direct formal config", contract)

    def test_gold_reconstruction_llm_smoke_dry_run_writes_sample_manifest_only(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = _write_word_usage_artifact_dir(Path(tempdir), sample_count=5)
            output_dir = Path(tempdir) / "smoke"

            artifacts = run_gold_reconstruction_llm_smoke(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                sample_size=3,
                seed=11,
                run_llm=False,
            )

            manifest = json.loads((output_dir / "llm_smoke_sample_manifest.json").read_text(encoding="utf-8"))
            self.assertIn("llm_smoke_sample_manifest", artifacts)
            self.assertEqual(manifest["sample_size"], 3)
            self.assertEqual(manifest["actual_sample_count"], 3)
            self.assertEqual(manifest["seed"], 11)
            self.assertEqual(len(manifest["sample_ids"]), 3)
            self.assertFalse(manifest["run_llm"])
            self.assertTrue((output_dir / "model_safe_gold_reconstruction_input.jsonl").exists())
            self.assertFalse((output_dir / "gold_reconstruction_results.jsonl").exists())
            self.assertFalse((output_dir / "source_discovery_queries.jsonl").exists())

    def test_gold_reconstruction_llm_smoke_fake_client_runs_source_discovery(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = _write_word_usage_artifact_dir(Path(tempdir), sample_count=4)
            output_dir = Path(tempdir) / "smoke"
            fake_output = json.dumps(_natural_gold_reconstruction_payload(), ensure_ascii=False)
            client = _FakeClient(fake_output)

            artifacts = run_gold_reconstruction_llm_smoke(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                sample_size=2,
                seed=7,
                run_llm=True,
                client=client,
            )

            self.assertEqual(len(client.calls), 2)
            self.assertIn("gold_reconstruction_results", artifacts)
            self.assertIn("source_discovery_queries", artifacts)
            self.assertIn("initial_material_seed_pack", artifacts)
            query_rows = [
                json.loads(line)
                for line in (output_dir / "source_discovery_queries.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            seed_rows = [
                json.loads(line)
                for line in (output_dir / "initial_material_seed_pack.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            report = (output_dir / "gold_reconstruction_llm_smoke_report.md").read_text(encoding="utf-8")
            self.assertEqual(len(query_rows), 2)
            self.assertEqual(len(seed_rows), 2)
            self.assertIn("Restored Human Material Examples", report)
            self.assertIn("Search Query Examples", report)
            self.assertIn("source_discovery_readiness", report)
            self.assertIn("Question Wrapper Leakage Risk Distribution", report)
            self.assertIn("Query Quality Distribution", report)
            self.assertIn("parse_success_count", report)
            self.assertIn("request_count", report)
            for row in query_rows:
                self.assertNotEqual(row["gold_source"], "raw_samples")
            self.assertFalse((Path(tempdir) / "card_specs").exists())

    def test_gold_reconstruction_llm_smoke_single_failure_does_not_abort(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = _write_word_usage_artifact_dir(Path(tempdir), sample_count=3)
            output_dir = Path(tempdir) / "smoke"
            client = _FakeSequenceClient(
                [
                    "not json",
                    "not json",
                    json.dumps(_natural_gold_reconstruction_payload(), ensure_ascii=False),
                ]
            )

            run_gold_reconstruction_llm_smoke(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                sample_size=2,
                seed=7,
                run_llm=True,
                client=client,
            )

            results = [
                json.loads(line)
                for line in (output_dir / "gold_reconstruction_results.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(results), 2)
            self.assertTrue(results[0]["reconstruction_summary"]["needs_human_review"])
            self.assertFalse(results[0]["mechanical_checks"]["json_parse_ok"])
            self.assertTrue((output_dir / "source_discovery_queries.jsonl").exists())


    def test_material_protocol_draft_dry_run_generates_alignment_and_digest(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "mother_family_id": "custom_family",
                        "child_family_id": "custom_leaf",
                        "leaf_label": "Custom Leaf",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"

            artifacts = run_material_protocol_draft(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                mode="dry-run",
            )

            self.assertIn("system_alignment_findings", artifacts)
            self.assertIn("material_protocol_draft_input_digest", artifacts)
            self.assertNotIn("material_card_draft", artifacts)
            digest = json.loads((output_dir / "material_protocol_draft_input_digest.json").read_text(encoding="utf-8"))
            self.assertEqual(digest["family_context"]["mother_family_id"], "custom_family")
            self.assertEqual(digest["family_context"]["child_family_id"], "custom_leaf")
            self.assertEqual(digest["family_context"]["material_card_id_draft"], "proto.custom_family.custom_leaf.material.v0")

    def test_material_protocol_draft_accepts_truth_gold_split_manifest_path(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(
                json.dumps({"mother_family_id": "family_split", "child_family_id": "leaf_split", "leaf_label": "Leaf Split"}),
                encoding="utf-8",
            )
            split_path = Path(tempdir) / "truth_gold_split_manifest.json"
            split_path.write_text(
                json.dumps({"split_version": "v1", "split_counts": {"insurance_holdout": 2}}, ensure_ascii=False),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"

            run_material_protocol_draft(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                mode="dry-run",
                truth_gold_split_manifest=split_path,
            )

            digest = json.loads((output_dir / "material_protocol_draft_input_digest.json").read_text(encoding="utf-8"))
            self.assertEqual(digest["evidence_paths"]["truth_gold_split_manifest"], str(split_path))
            self.assertNotIn("truth_gold_split_manifest", digest["missing_evidence"])
            self.assertTrue(digest["truth_gold_split_summary"]["available"])

    def test_material_protocol_draft_mock_generates_generic_draft_assets(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "mother_family_id": "arbitrary_family",
                        "child_family_id": "arbitrary_leaf",
                        "leaf_label": "Arbitrary Leaf",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"

            artifacts = run_material_protocol_draft(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                mode="mock",
            )

            for key in (
                "material_card_draft",
                "material_line_prompt_assets_draft",
                "material_quality_regression_draft",
                "material_review_prompts",
                "material_bridge_mapping_draft",
                "material_protocol_assets_draft_report",
            ):
                self.assertIn(key, artifacts)
            card = json.loads((output_dir / "material_card_draft.json").read_text(encoding="utf-8"))
            self.assertEqual(card["status"], "draft_only")
            self.assertFalse(card["formalized"])
            self.assertFalse(card["writeback_allowed"])
            self.assertTrue(card["requires_human_review"])
            self.assertTrue(card["requires_regression"])
            self.assertEqual(card["family_binding"]["mother_family_id"], "arbitrary_family")
            self.assertEqual(card["family_binding"]["child_family_id"], "arbitrary_leaf")
            self.assertNotIn("word_usage_content_word", json.dumps(card, ensure_ascii=False))

    def test_material_protocol_checker_rejects_forbidden_flags(self) -> None:
        digest = {
            "family_context": {
                "mother_family_id": "family_a",
                "child_family_id": "leaf_a",
                "leaf_label": "Leaf A",
            }
        }
        alignment = build_system_alignment_findings(Path.cwd())
        bundle = build_mock_material_protocol_bundle(digest=digest, alignment=alignment)
        bundle["material_card_draft"]["verified"] = True

        errors = validate_material_protocol_bundle(bundle=bundle, digest=digest, alignment=alignment)

        self.assertTrue(any("verified" in error for error in errors))

    def test_material_protocol_checker_rejects_writeback_and_family_mismatch(self) -> None:
        digest = {
            "family_context": {
                "mother_family_id": "family_a",
                "child_family_id": "leaf_a",
                "leaf_label": "Leaf A",
            }
        }
        alignment = build_system_alignment_findings(Path.cwd())
        bundle = build_mock_material_protocol_bundle(digest=digest, alignment=alignment)
        bundle["material_bridge_mapping_draft"]["writeback_allowed"] = True
        bundle["material_card_draft"]["family_binding"]["child_family_id"] = "other_leaf"

        errors = validate_material_protocol_bundle(bundle=bundle, digest=digest, alignment=alignment)

        self.assertTrue(any("writeback_allowed" in error for error in errors))
        self.assertTrue(any("family_binding.child_family_id" in error for error in errors))

    def test_material_protocol_quality_dimensions_and_review_prompts(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(
                json.dumps({"mother_family_id": "family_b", "child_family_id": "leaf_b", "leaf_label": "Leaf B"}),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"
            run_material_protocol_draft(artifact_dir=artifact_dir, output_dir=output_dir, mode="mock")

            quality = json.loads((output_dir / "material_quality_regression_draft.json").read_text(encoding="utf-8"))
            self.assertTrue(quality["dimensions"])
            for dimension in quality["dimensions"]:
                self.assertIn("method", dimension)
                self.assertIn("confidence", dimension)
                self.assertIn("limitation", dimension)
            prompts = (output_dir / "material_review_prompts.md").read_text(encoding="utf-8")
            self.assertIn("Source Review", prompts)
            self.assertIn("Material Quality Review", prompts)
            report = (output_dir / "material_protocol_assets_draft_report.md").read_text(encoding="utf-8")
            self.assertIn("材料线协议资产草案报告", report)

    def test_report_renderer_includes_material_protocol_draft_section(self) -> None:
        report = render_markdown_report(
            manifest={"job_id": "job", "mother_family_id": "family_c", "leaf_label": "Leaf C"},
            candidate_report={"sample_count": 0, "field_candidates": [], "summary": {}},
            slot_projection={},
            material_protocol_draft={
                "family_context": {"mother_family_id": "family_c", "child_family_id": "leaf_c"},
                "missing_evidence": ["source_seed_registry"],
                "system_alignment_findings_summary": {"checked_file_count": 1},
            },
        )

        self.assertIn("Material Protocol Draft", report)
        self.assertIn("evidence_gaps_count", report)

    def test_artifact_contract_mentions_material_protocol_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")
        self.assertIn("system_alignment_findings.json", contract)
        self.assertIn("material_protocol_draft_input_digest.json", contract)
        self.assertIn("material_card_draft.json", contract)
        self.assertIn("material_bridge_mapping_draft.json", contract)

    def test_material_protocol_split_pipeline_mock_generates_stage_artifacts(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(
                json.dumps({"mother_family_id": "split_family", "child_family_id": "split_leaf", "leaf_label": "Split Leaf"}),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"

            artifacts = run_material_protocol_split_pipeline(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                mode="mock",
            )

            for key in (
                "material_evidence_map",
                "material_semantic_requirements_draft",
                "material_card_draft",
                "material_line_prompt_assets_draft",
                "material_quality_regression_draft",
                "material_bridge_mapping_draft",
                "material_protocol_split_pipeline_report",
            ):
                self.assertIn(key, artifacts)
            card = json.loads((output_dir / "material_card_draft.json").read_text(encoding="utf-8"))
            self.assertEqual(card["family_binding"]["mother_family_id"], "split_family")
            self.assertTrue(card["cleaning_and_slicing_hypothesis"]["source_body_required"])
            self.assertTrue(card["cleaning_and_slicing_hypothesis"]["source_gold_alignment_required"])
            prompts = json.loads((output_dir / "material_line_prompt_assets_draft.json").read_text(encoding="utf-8"))
            self.assertIn("source_evidence_review", prompts["prompts"])
            quality = json.loads((output_dir / "material_quality_regression_draft.json").read_text(encoding="utf-8"))
            self.assertTrue(quality["dimensions"])
            bridge = json.loads((output_dir / "material_bridge_mapping_draft.json").read_text(encoding="utf-8"))
            self.assertEqual(bridge["system_alignment_findings_ref"], "system_alignment_findings.json")

    def test_material_protocol_split_pipeline_dry_run_only_writes_evidence_map(self) -> None:
        with TemporaryDirectory() as tempdir:
            artifact_dir = Path(tempdir) / "artifact"
            artifact_dir.mkdir()
            (artifact_dir / "manifest.json").write_text(
                json.dumps({"mother_family_id": "dry_family", "child_family_id": "dry_leaf", "leaf_label": "Dry Leaf"}),
                encoding="utf-8",
            )
            output_dir = Path(tempdir) / "out"

            artifacts = run_material_protocol_split_pipeline(
                artifact_dir=artifact_dir,
                output_dir=output_dir,
                mode="dry-run",
            )

            self.assertIn("material_evidence_map", artifacts)
            self.assertNotIn("material_card_draft", artifacts)
            self.assertFalse((output_dir / "material_card_draft.json").exists())

    def test_material_protocol_split_checker_rejects_empty_stage_contracts(self) -> None:
        digest = {
            "family_context": {
                "mother_family_id": "family_x",
                "child_family_id": "leaf_x",
                "leaf_label": "Leaf X",
            }
        }
        stages = {
            "material_semantic_requirements_draft": {"status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True},
            "material_card_draft": {"status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True, "family_binding": digest["family_context"], "evidence_refs": {}, "cleaning_and_slicing_hypothesis": {}},
            "material_line_prompt_assets_draft": {"status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True, "prompts": {}},
            "material_quality_regression_draft": {"status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True, "dimensions": []},
            "material_bridge_mapping_draft": {"status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True},
        }

        errors = validate_split_stages(stages=stages, digest=digest)

        self.assertTrue(any("evidence_refs" in error for error in errors))
        self.assertTrue(any("source_body_required" in error for error in errors))
        self.assertTrue(any("prompts.source_evidence_review" in error for error in errors))
        self.assertTrue(any("dimensions" in error for error in errors))
        self.assertTrue(any("system_alignment_findings_ref" in error for error in errors))

    def test_split_runtime_keeps_completed_stages_when_provider_fails(self) -> None:
        with TemporaryDirectory() as tempdir:
            calls = []

            def builder(stage_key: str, completed: dict) -> dict:
                calls.append(stage_key)
                if stage_key == "material_card_draft":
                    raise RuntimeError("provider 502")
                return {"stage": stage_key, "status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True}

            def validator(candidate: dict) -> list[str]:
                return []

            completed, state, artifacts = execute_split_stages(
                output_dir=Path(tempdir),
                mode="llm",
                stage_builder=builder,
                stage_validator=validator,
                max_retries=1,
            )

            self.assertIn("material_evidence_map", completed)
            self.assertIn("material_semantic_requirements_draft", completed)
            self.assertNotIn("material_card_draft", completed)
            self.assertTrue((Path(tempdir) / "stages" / "01_material_evidence_map.json").exists())
            self.assertTrue((Path(tempdir) / "stages" / "02_material_semantic_requirements_draft.json").exists())
            self.assertEqual(state["stages"]["material_card_draft"]["status"], "provider_error")
            self.assertEqual(state["stages"]["material_card_draft"]["retry_count"], 1)
            self.assertTrue((Path(tempdir) / "pipeline_state.json").exists())
            self.assertIn("pipeline_stage_report", artifacts)

    def test_split_runtime_resume_skips_successful_stages(self) -> None:
        with TemporaryDirectory() as tempdir:
            call_count = {"count": 0}
            fail_once = {"done": False}

            def builder(stage_key: str, completed: dict) -> dict:
                call_count["count"] += 1
                if stage_key == "material_card_draft" and not fail_once["done"]:
                    fail_once["done"] = True
                    raise RuntimeError("temporary provider failure")
                return {"stage": stage_key, "status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True}

            def validator(candidate: dict) -> list[str]:
                return []

            execute_split_stages(
                output_dir=Path(tempdir),
                mode="llm",
                stage_builder=builder,
                stage_validator=validator,
                max_retries=0,
            )
            first_count = call_count["count"]
            completed, state, _ = execute_split_stages(
                output_dir=Path(tempdir),
                mode="llm",
                stage_builder=builder,
                stage_validator=validator,
                resume=True,
                max_retries=0,
            )

            self.assertLess(call_count["count"] - first_count, 6)
            self.assertIn("material_bridge_mapping_draft", completed)
            self.assertEqual(state["stages"]["material_evidence_map"]["status"], "skipped")
            self.assertEqual(state["stages"]["material_semantic_requirements_draft"]["status"], "skipped")

    def test_split_runtime_validation_error_and_report_statuses(self) -> None:
        with TemporaryDirectory() as tempdir:
            def builder(stage_key: str, completed: dict) -> dict:
                return {"stage": stage_key, "status": "draft_only", "formalized": False, "writeback_allowed": False, "requires_human_review": True, "requires_regression": True}

            def validator(candidate: dict) -> list[str]:
                if "material_semantic_requirements_draft" in candidate:
                    return ["material_semantic_requirements_draft.invalid shape"]
                return []

            _, state, _ = execute_split_stages(
                output_dir=Path(tempdir),
                mode="llm",
                stage_builder=builder,
                stage_validator=validator,
                max_retries=1,
            )
            report = build_pipeline_stage_report(state=state)
            statuses = {stage["stage"]: stage["status"] for stage in report["stages"]}

            self.assertEqual(statuses["material_evidence_map"], "success")
            self.assertEqual(statuses["material_semantic_requirements_draft"], "validation_error")
            self.assertTrue(report["blocked"])


def _candidate_report() -> dict:
    return {
        "mother_family_id": "sentence_order",
        "leaf_label": "timeline",
        "sample_count": 40,
        "field_candidates": [
            {
                "field_path": "ordering_logic",
                "proposed_value": "timeline_progression",
                "target_layer": "material_card_overlay",
                "support_rate": 1.0,
                "support_count": 40,
                "confidence": "high",
                "evidence_examples": ["timeline", "before-after"],
                "uniqueness_source": [],
                "distractor_modes": [],
                "ablation_question": "remove ordering_logic?",
            }
        ],
        "schema_gaps": [
            {
                "field": "timeline_progression_as_middle_structure",
                "reason": "better represented as ordering_logic",
                "suggested_resolution": "keep as overlay",
            }
        ],
        "summary": {"high_confidence_count": 1, "medium_confidence_count": 0, "low_confidence_count": 0},
    }


def _probe_digest() -> dict:
    candidate_report = _candidate_report()
    slot_projection = build_slot_projection_draft(candidate_report)
    return build_llm_safe_digest(
        manifest={"mother_family_id": "sentence_order", "leaf_label": "timeline"},
        samples=[],
        traces=[],
        candidate_report=candidate_report,
        slot_projection=slot_projection,
    )


def _empty_candidate_report() -> dict:
    return {
        "mother_family_id": "word_usage",
        "leaf_label": "实词",
        "sample_count": 2,
        "field_candidates": [],
        "schema_gaps": [],
        "summary": {"high_confidence_count": 0, "medium_confidence_count": 0, "low_confidence_count": 0},
    }


def _word_usage_sample(sample_id: str) -> dict:
    return {
        "sample_id": sample_id,
        "qid": f"#{sample_id}",
        "source_file_name": "word_usage.docx",
        "mother_family_id": "word_usage",
        "leaf_label": "实词",
        "stem": "加点词在文中的意思是？下列对这个词语理解正确的是哪一项？",
        "options": {"A": "结合语境的正确解释", "B": "脱离语境的字面解释", "C": "偷换概念", "D": "范围扩大"},
        "answer": "A",
        "analysis": (
            "本题为词语理解题，应结合上下文和具体语境理解，不是字面意思。"
            "该词指代前文内容，错误选项存在偷换概念、范围扩大和无中生有。"
        ),
        "exam_points": "言语理解与表达-词句理解题-实词;",
        "correct_rate": "45%",
        "wrong_option": "B",
        "raw_text": "",
    }


def _word_usage_manifest() -> dict:
    return {
        "job_id": "job_word_usage",
        "mother_family_id": "word_usage",
        "child_family_id": "word_usage_content_word",
        "leaf_label": "实词",
        "clean_leaf_boundary": True,
    }


def _word_usage_discovery() -> dict:
    return build_bootstrap_discovery(
        manifest=_word_usage_manifest(),
        samples=[_word_usage_sample("1"), _word_usage_sample("2")],
        traces=[{"sample_id": "1", "observed_actions": []}, {"sample_id": "2", "observed_actions": []}],
        candidate_report=_empty_candidate_report(),
        proto_family_label="word_usage",
    )


def _writeback_plan_without_shared_targets() -> dict:
    confirmation = build_axis_confirmation(
        manifest=_word_usage_manifest(),
        bootstrap_discovery=_word_usage_discovery(),
        decision_payload={
            "reviewer": "human",
            "decisions": [
                {
                    "source_type": "candidate_axis",
                    "source_id": "contextual_meaning_mode",
                    "action": "promote_to_proto_field",
                    "target_layer": "business_feature_card",
                    "rationale": "business feature proto axis",
                },
                {
                    "source_type": "distractor_taxonomy",
                    "source_id": "context_detached",
                    "action": "map_to_distractor_taxonomy",
                    "target_layer": "signal_layer",
                    "rationale": "signal layer proto taxonomy",
                },
                {
                    "source_type": "candidate_axis",
                    "source_id": "concept_boundary_mode",
                    "action": "map_to_validator_candidate",
                    "target_layer": "validator_contract",
                    "rationale": "validator candidate only",
                },
            ],
        },
    )
    draft = build_formal_patch_draft(manifest=_word_usage_manifest(), axis_confirmation=confirmation)
    return build_formal_writeback_plan(formal_patch_draft=draft, reviewer="human")


def _writeback_plan_with_prompt_assets() -> dict:
    confirmation = build_axis_confirmation(
        manifest=_word_usage_manifest(),
        bootstrap_discovery=_word_usage_discovery(),
        decision_payload={
            "reviewer": "human",
            "decisions": [
                {
                    "source_type": "candidate_axis",
                    "source_id": "referent_resolution_mode",
                    "action": "map_to_prompt_guard",
                    "target_layer": "prompt_assets",
                    "rationale": "shared prompt guard should remain draft",
                }
            ],
        },
    )
    draft = build_formal_patch_draft(manifest=_word_usage_manifest(), axis_confirmation=confirmation)
    return build_formal_writeback_plan(formal_patch_draft=draft, reviewer="human")


def _approval_for_plan(plan: dict) -> dict:
    allowed_targets = [item["target"] for item in plan["writeback_items"]]
    allowed_files = [item["target_file"] for item in plan["writeback_items"]]
    return {
        "approval_version": "v1",
        "approval_type": "formal_writeback",
        "approved": True,
        "approved_at": "2026-04-26T00:00:00+08:00",
        "approved_by": "human_reviewer",
        "approval_scope": {
            "proto_family": plan["proto_family"],
            "proto_child_family": plan["proto_child_family"],
            "allowed_targets": allowed_targets,
            "allowed_files": allowed_files,
        },
        "source_artifacts": {
            "axis_confirmation_path": "axis_confirmation.json",
            "formal_patch_draft_path": "formal_patch_draft.json",
            "formal_writeback_plan_path": "formal_writeback_plan.json",
            "formal_writeback_diff_path": "formal_writeback_diff.md",
        },
        "human_review_assertions": {
            "candidate_axes_are_proto_confirmed": True,
            "draft_reviewed": True,
            "diff_reviewed": True,
            "rollback_reviewed": True,
            "no_shared_config_write_in_v1": True,
        },
    }


def _python_ok_command() -> str:
    return f'"{sys.executable}" -c "print(\'regression ok\')"'


def _write_word_usage_artifact_dir(root: Path, *, sample_count: int) -> Path:
    artifact_dir = root / "artifact"
    artifact_dir.mkdir()
    (artifact_dir / "manifest.json").write_text(json.dumps(_word_usage_manifest(), ensure_ascii=False), encoding="utf-8")
    samples = [_word_usage_sample(str(index)) for index in range(sample_count)]
    (artifact_dir / "samples.jsonl").write_text(
        "".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in samples),
        encoding="utf-8",
    )
    return artifact_dir


def _write_source_discovery_queries(root: Path) -> Path:
    path = root / "source_discovery_queries.jsonl"
    rows = [
        {
            "sample_id": "sample-1",
            "query_version": "v1",
            "gold_source": "gold_reconstruction_results",
            "restored_human_material": "城市更新并不是简单拆旧建新。保留街区肌理能让居民重新建立联系。",
            "search_queries": [
                {
                    "query": "城市更新并不是简单拆旧建新 保留街区肌理",
                    "query_type": "exact_sentence",
                    "purpose": "find_original_source",
                    "confidence": "high",
                },
                {
                    "query": "保留街区肌理 居民 重新建立联系",
                    "query_type": "keyword_combo",
                    "purpose": "find_similar_material",
                    "confidence": "medium",
                },
            ],
            "question_bank_contamination_risk": "low",
            "needs_human_review": False,
            "warnings": [],
        },
        {
            "sample_id": "sample-2",
            "query_version": "v1",
            "gold_source": "gold_reconstruction_results",
            "restored_human_material": "下列对文中词语理解正确的是。",
            "search_queries": [
                {
                    "query": "下列对文中词语理解正确的是",
                    "query_type": "exact_sentence",
                    "purpose": "find_original_source",
                    "confidence": "high",
                }
            ],
            "question_bank_contamination_risk": "high",
            "needs_human_review": True,
            "warnings": ["high question-bank contamination risk"],
        },
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def _write_source_candidate_results(root: Path) -> Path:
    path = root / "source_candidate_results.jsonl"
    rows = [
        {
            "sample_id": "sample-1",
            "query": "城市更新 保留街区肌理",
            "query_type": "exact_sentence",
            "candidate_rank": 1,
            "title": "城市更新评论文章",
            "url": "https://www.gmw.cn/example/city.html",
            "domain": "www.gmw.cn",
            "snippet": "城市更新需要保留街区肌理。",
            "source_risk": "low",
            "candidate_score": 0.42,
            "candidate_status": "weak_candidate",
            "verification_status": "unverified",
            "verified": False,
            "alignment_signals": {},
            "warnings": [],
        },
        {
            "sample_id": "sample-1",
            "query": "城市更新 保留街区肌理",
            "query_type": "exact_sentence",
            "candidate_rank": 2,
            "title": "城市更新答案解析",
            "url": "https://www.offcn.com/tiku/a.html",
            "domain": "www.offcn.com",
            "snippet": "本题考查言语理解。",
            "source_risk": "exam_training_like",
            "candidate_score": 0.0,
            "candidate_status": "question_bank_like",
            "verification_status": "unverified",
            "verified": False,
            "alignment_signals": {},
            "warnings": ["candidate looks like question bank or exam training source"],
        },
        {
            "sample_id": "sample-2",
            "query": "二氧化碳 植物生长",
            "query_type": "exact_sentence",
            "candidate_rank": 1,
            "title": "二氧化碳浓度越高，植物生长越快？",
            "url": "https://www.nju.edu.cn/info/3191/215671.htm",
            "domain": "www.nju.edu.cn",
            "snippet": "二氧化碳是植物光合作用的重要原料。",
            "source_risk": "low",
            "candidate_score": 0.3,
            "candidate_status": "weak_candidate",
            "verification_status": "unverified",
            "verified": False,
            "alignment_signals": {},
            "warnings": [],
        },
        {
            "sample_id": "sample-3",
            "query": "无关",
            "query_type": "keyword_combo",
            "candidate_rank": 1,
            "title": "无关百科",
            "url": "https://baike.baidu.com/item/unrelated",
            "domain": "baike.baidu.com",
            "snippet": "无关内容。",
            "source_risk": "unknown",
            "candidate_score": 0.1,
            "candidate_status": "blocked",
            "verification_status": "unverified",
            "verified": False,
            "alignment_signals": {},
            "warnings": [],
        },
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def _write_source_candidate_review_decisions(root: Path) -> Path:
    path = root / "source_candidate_review_decisions.json"
    payload = {
        "review_version": "v1",
        "reviewer": "human",
        "reviewed_at": "2026-04-26T00:00:00+08:00",
        "decisions": [
            {
                "sample_id": "sample-2",
                "url": "https://www.nju.edu.cn/info/3191/215671.htm",
                "decision": "keep_as_similar_material_seed",
                "source_use": "similar_material",
                "crawl_priority": "high",
                "rationale": "主题与二氧化碳浓度和植物生长相关，可作为同机制材料。",
                "human_opened_url": False,
            },
            {
                "sample_id": "sample-1",
                "url": "https://www.gmw.cn/example/city.html",
                "decision": "keep_as_original_source_candidate",
                "source_use": "original_source_candidate",
                "crawl_priority": "medium",
                "rationale": "可能接近原文，但尚未验证。",
                "human_opened_url": False,
            },
            {
                "sample_id": "sample-1",
                "url": "https://www.offcn.com/tiku/a.html",
                "decision": "reject_question_bank",
                "source_use": "reject",
                "rationale": "公考培训题库页。",
                "human_opened_url": False,
            },
            {
                "sample_id": "sample-3",
                "url": "https://baike.baidu.com/item/unrelated",
                "decision": "reject_irrelevant",
                "source_use": "reject",
                "rationale": "无关。",
                "human_opened_url": False,
            },
            {
                "sample_id": "sample-3",
                "url": "https://baike.baidu.com/item/unrelated",
                "decision": "defer",
                "source_use": "defer",
                "rationale": "以后再看。",
                "human_opened_url": False,
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_source_seed_registry(root: Path) -> Path:
    path = root / "source_seed_registry.jsonl"
    rows = [
        {
            "seed_id": "source_seed_city",
            "seed_version": "v1",
            "sample_id": "sample-1",
            "source_use": "original_source_candidate",
            "seed_type": "url_seed",
            "url": "https://www.gmw.cn/example/city.html",
            "domain": "www.gmw.cn",
            "title": "城市更新评论文章",
            "snippet": "城市更新需要保留街区肌理，修复公共空间，让居民在熟悉的生活场景中重新建立联系。",
            "source_risk": "low",
            "candidate_status": "weak_candidate",
            "crawl_priority": "medium",
            "usable_for_family": "demo_family",
            "usable_for_leaf": "demo_leaf",
            "linked_query": "城市更新 街区肌理 公共空间",
            "linked_candidate_score": 0.42,
            "verification_status": "human_reviewed_unverified",
            "verified_original_source": False,
            "verified": False,
            "formalized": False,
            "status": "seed_only",
            "negative_patterns": ["question_bank_page"],
            "review_rationale": "可能接近原文，但未验证。",
            "warnings": [],
        }
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def _write_source_text_evidence_approval(root: Path) -> Path:
    path = root / "source_text_evidence_approval.json"
    payload = {
        "approval_version": "v1",
        "reviewer": "human",
        "approved_at": "2026-04-27T00:00:00+08:00",
        "source_seed_registry_path": str(root / "source_seed_registry.jsonl"),
        "approved_seed_ids": ["source_seed_city"],
        "limits": {
            "max_urls": 1,
            "allowed_domains": [],
            "blocked_domains": [],
            "allow_risky_seed": False,
        },
        "approval_scope": "prepare_source_text_evidence_only",
        "does_not_confirm_original_source": True,
        "does_not_allow_material_library_write": True,
        "does_not_allow_material_card_write": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_gold_reconstruction_results_for_material_evidence(root: Path) -> Path:
    path = root / "gold_reconstruction_results.jsonl"
    payload = _natural_gold_reconstruction_payload()
    payload["sample_id"] = "sample-1"
    payload["gold_material"]["restored_text"] = "城市更新并不是简单拆旧建新。保留街区肌理、修复公共空间，能让居民在熟悉的生活场景中重新建立联系。"
    payload["gold_material"]["context_window"] = "保留街区肌理、修复公共空间，让居民重新建立联系。"
    payload["gold_material"]["evidence_units"] = ["街区肌理", "公共空间", "重新建立联系"]
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _natural_gold_reconstruction_payload() -> dict:
    return {
        "sample_id": "placeholder",
        "reconstruction_version": "v1",
        "question_family_guess": "word_usage",
        "leaf_label_guess": "content_word",
        "reconstruction_summary": {
            "what_was_reconstructed": "A natural context window and the original answer mechanism.",
            "why_this_reconstruction_is_needed": "Source discovery needs article-like material rather than question wording.",
            "confidence": "medium",
            "needs_human_review": False,
            "warnings": [],
        },
        "gold_material": {
            "restored_text": "城市更新并不是简单拆旧建新。保留街区肌理、修复公共空间，能让居民在熟悉的生活场景中重新建立联系。",
            "context_window": "保留街区肌理、修复公共空间，能让居民在熟悉的生活场景中重新建立联系。",
            "material_units": ["城市更新", "街区肌理", "公共空间"],
            "evidence_units": ["保留街区肌理", "重新建立联系"],
            "material_boundary_note": "This is a reconstructed context window for source discovery smoke.",
        },
        "gold_question": {
            "stem": "文中词语的含义理解。",
            "options": {"A": "结合语境的解释", "B": "脱离语境的解释", "C": "范围扩大", "D": "偷换概念"},
            "answer": "A",
            "correct_option_text": "结合语境的解释",
        },
        "answer_mechanism": {
            "core_reasoning": "The target term must be interpreted by the surrounding context.",
            "uniqueness_source": "context window",
            "evidence_mapping": [],
        },
        "distractor_mechanism": {
            "distractor_modes": ["context_detached", "scope_shift"],
            "easy_wrong_reason": "",
            "option_diagnostics": {},
        },
        "gold_quality_flags": {
            "is_reconstructable": True,
            "missing_information": [],
            "ambiguous_points": [],
            "requires_source_article": True,
            "overfit_risk_note": "",
        },
    }


class NewLeafFormalizationFactoryTest(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

    def _seed_artifacts(self, root: Path) -> dict[str, Path]:
        paths = {
            "manifest": root / "manifest.json",
            "axis_confirmation": root / "axis_confirmation.json",
            "formal_patch_draft": root / "formal_patch_draft.json",
            "material_card_draft": root / "material_card_draft.json",
            "material_bridge_mapping_draft": root / "material_bridge_mapping_draft.json",
            "material_quality_regression_draft": root / "material_quality_regression_draft.json",
            "source_candidate_review": root / "source_candidate_review.json",
            "source_seed_registry": root / "source_seed_registry.jsonl",
            "crawl_seed_manifest": root / "crawl_seed_manifest.json",
            "truth_gold_regression_results": root / "truth_gold_regression_results.json",
            "truth_gold_split_manifest": root / "truth_gold_split_manifest.json",
            "system_alignment_findings": root / "system_alignment_findings.json",
        }
        self._write_json(paths["manifest"], {"job_id": "job-1", "mother_family_id": "demo_family", "child_family_id": "demo_leaf", "leaf_label": "demo leaf", "clean_leaf_boundary": True})
        self._write_json(paths["axis_confirmation"], {"confirmation_version": "v1", "axis_decisions": [{"axis": "reasoning_mode", "status": "proto_confirmed"}]})
        self._write_json(
            paths["formal_patch_draft"],
            {
                "draft_version": "v1",
                "status": "draft_only",
                "formalized": False,
                "writeback_allowed": False,
                "target_patches": [
                    {"target": "business_feature_card", "payload": {"status": "draft_only"}},
                    {"target": "prompt_assets", "payload": {"status": "draft_only"}},
                    {"target": "validator_contract", "payload": {"status": "draft_only"}},
                ],
            },
        )
        self._write_json(
            paths["material_card_draft"],
            {
                "status": "draft_only",
                "formalized": False,
                "writeback_allowed": False,
                "family_binding": {
                    "mother_family_id": "demo_family",
                    "child_family_id": "demo_leaf",
                    "leaf_label": "demo leaf",
                    "business_subtype": "demo_leaf",
                    "question_focus": "demo_family",
                },
            },
        )
        self._write_json(paths["material_bridge_mapping_draft"], {"status": "draft_only", "formalized": False, "writeback_allowed": False, "confirmed_repository_fields_used": ["query", "filters"]})
        self._write_json(paths["material_quality_regression_draft"], {"status": "draft_only", "formalized": False, "writeback_allowed": False})
        self._write_json(paths["source_candidate_review"], {"review_version": "v1", "accepted_count": 1, "rejected_count": 0, "deferred_count": 0, "verified_original_source_count": 0})
        self._write_jsonl(paths["source_seed_registry"], [{"seed_id": "seed-1", "status": "seed_only", "formalized": False, "verified": False, "verified_original_source": False}])
        self._write_json(paths["crawl_seed_manifest"], {"crawl_allowed": False, "ready_for_material_card_draft": False})
        self._write_json(paths["truth_gold_regression_results"], {"summary": {"fit_type": "route_available_not_quality_proven", "ready_for_formalization": False}, "gold_source": "gold_reconstruction_results"})
        self._write_json(paths["truth_gold_split_manifest"], {"splits": {"train_observation": ["s1"], "dev_tuning": ["s2"], "eval": ["s3"], "insurance_holdout": ["s4"]}})
        self._write_json(paths["system_alignment_findings"], {"confirmed_bridge_request_fields": ["query", "filters"], "confirmed_existing_entrypoints": {"MaterialBridgeV2": True}})
        return paths

    def test_agent_review_feedback_mock_normalizes_and_stays_evidence_only(self) -> None:
        with TemporaryDirectory() as temp:
            artifacts = run_agent_review_feedback_normalization(
                output_dir=temp,
                feedback_input=build_feedback_input(raw_feedback="太简单了，材料太短，干扰项不够迷惑。", reviewer="human", target_scope="batch"),
                mode="mock",
            )
            normalized = json.loads(Path(artifacts["agent_review_feedback_normalized"]).read_text(encoding="utf-8"))
            dimensions = {item["dimension"] for item in normalized["normalized_feedback"]}
            self.assertIn("difficulty_too_low", dimensions)
            self.assertIn("material_too_short", dimensions)
            self.assertIn("distractor_weakness", dimensions)
            self.assertFalse(normalized["writeback_allowed"])
            self.assertFalse(normalized["formalized"])
            report = Path(artifacts["agent_review_feedback_report"]).read_text(encoding="utf-8")
            self.assertIn("Agent Review Feedback", report)

    def test_new_leaf_packet_collects_feedback_and_keeps_source_seed_unverified(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self._seed_artifacts(root)
            self._write_json(root / "source_text_evidence_manifest.json", {"status": "completed", "result_count": 1, "available_count": 1, "manual_required_count": 0})
            self._write_json(root / "source_gold_alignment_summary.json", {"status": "completed", "alignment_count": 1, "needs_human_review_count": 1, "verified_original_source_count": 0})
            self._write_json(root / "material_quality_regression_results.json", {"status": "blocked", "requires_human_review": True, "ready_for_material_card_formalization": False, "verified_original_source_count": 0})
            feedback_artifacts = run_agent_review_feedback_normalization(output_dir=root, feedback_input=build_feedback_input(raw_feedback="材料太短"), mode="mock")
            packet_artifacts = run_new_leaf_formalization_packet(artifact_dir=root, agent_review_feedback_path=feedback_artifacts["agent_review_feedback_normalized"])
            packet = json.loads(Path(packet_artifacts["new_leaf_formalization_packet"]).read_text(encoding="utf-8"))
            self.assertEqual(packet["status"], "draft_review_packet")
            self.assertFalse(packet["writeback_allowed"])
            self.assertFalse(packet["formalized"])
            self.assertTrue(packet["confirmed_user_decisions"]["agent_review_feedback"]["available"])
            self.assertIn("material_evidence_summary", packet)
            self.assertEqual(packet["material_evidence_summary"]["material_quality_regression_status"], "blocked")
            self.assertFalse(packet["material_evidence_summary"]["ready_for_material_card_review"])
            self.assertFalse(packet["material_evidence_summary"]["ready_for_material_card_formalization"])
            self.assertIn("source_seed_is_not_verified_source", packet["blocking_issues"])
            self.assertTrue(any(item["target"] == "business_feature_card" for item in packet["formal_target_candidates"]))

    def test_runtime_activation_plan_is_read_only_and_reports_missing_mapping(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self._seed_artifacts(root)
            feedback_artifacts = run_agent_review_feedback_normalization(output_dir=root, feedback_input=build_feedback_input(raw_feedback="材料太短"), mode="mock")
            packet_artifacts = run_new_leaf_formalization_packet(artifact_dir=root, agent_review_feedback_path=feedback_artifacts["agent_review_feedback_normalized"])
            activation_artifacts = run_runtime_activation_plan(artifact_dir=root, formalization_packet_path=packet_artifacts["new_leaf_formalization_packet"])
            plan = json.loads(Path(activation_artifacts["runtime_activation_plan"]).read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "draft_only")
            self.assertFalse(plan["writeback_allowed"])
            self.assertFalse(plan["formalized"])
            self.assertFalse(plan["proto_vs_formal"]["can_run_formal_generation"])
            self.assertIn("runtime_mapping_missing", plan["activation_blockers"])

    def test_readiness_gate_blocks_without_activation_plan_and_high_feedback(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self._seed_artifacts(root)
            feedback = {
                "feedback_version": "v1",
                "status": "normalized",
                "writeback_allowed": False,
                "formalized": False,
                "normalized_feedback": [{"dimension": "distractor_weakness", "severity": "high"}],
            }
            feedback_path = root / "agent_review_feedback_normalized.json"
            self._write_json(feedback_path, feedback)
            packet_artifacts = run_new_leaf_formalization_packet(artifact_dir=root, agent_review_feedback_path=feedback_path)
            gate_artifacts = run_formalization_readiness_gate(artifact_dir=root, formalization_packet_path=packet_artifacts["new_leaf_formalization_packet"], agent_review_feedback_path=feedback_path)
            gate = json.loads(Path(gate_artifacts["formalization_readiness_checklist"]).read_text(encoding="utf-8"))
            self.assertEqual(gate["status"], "blocked")
            self.assertFalse(gate["writeback_allowed"])
            self.assertIn("runtime_activation_plan_available", gate["blocking_issues"])
            self.assertIn("high_severity_feedback_resolved", gate["blocking_issues"])

    def test_readiness_gate_reports_material_card_review_ready_status(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self._seed_artifacts(root)
            packet_path = root / "new_leaf_formalization_packet.json"
            runtime_path = root / "runtime_activation_plan.json"
            feedback_path = root / "agent_review_feedback_normalized.json"
            source_manifest_path = root / "source_text_evidence_manifest.json"
            alignment_path = root / "source_gold_alignment_summary.json"
            quality_path = root / "material_quality_regression_results.json"
            self._write_json(packet_path, {"family_context": {"mother_family_id": "demo_family"}, "formalized": False, "writeback_allowed": False})
            self._write_json(runtime_path, {"family_context": {"mother_family_id": "demo_family"}, "activation_blockers": [], "proto_vs_formal": {"can_run_proto_trial": True, "can_run_formal_generation": False}})
            self._write_json(feedback_path, {"status": "normalized", "formalized": False, "writeback_allowed": False, "normalized_feedback": []})
            self._write_json(source_manifest_path, {"status": "completed", "available_count": 1, "result_count": 1, "verified_original_source_count": 0})
            self._write_json(alignment_path, {"status": "completed", "alignment_count": 1, "needs_human_review_count": 0, "verified_original_source_count": 0})
            self._write_json(quality_path, {"status": "warning", "requires_human_review": False, "ready_for_material_card_formalization": False, "verified_original_source_count": 0})

            artifacts = run_formalization_readiness_gate(
                artifact_dir=root,
                formalization_packet_path=packet_path,
                runtime_activation_plan_path=runtime_path,
                agent_review_feedback_path=feedback_path,
                source_text_evidence_manifest_path=source_manifest_path,
                source_gold_alignment_summary_path=alignment_path,
                material_quality_regression_results_path=quality_path,
            )

            gate = json.loads(Path(artifacts["formalization_readiness_checklist"]).read_text(encoding="utf-8"))
            self.assertEqual(gate["categories"]["material_line_readiness"]["status"], "material_card_review_ready")
            self.assertFalse(gate["categories"]["material_line_readiness"]["material_card_formalization_allowed"])

    def test_report_renderer_shows_new_formalization_sections(self) -> None:
        report = render_markdown_report(
            manifest={"leaf_label": "demo", "job_id": "job", "mother_family_id": "demo_family", "clean_leaf_boundary": True},
            candidate_report={"sample_count": 1, "field_candidates": [], "summary": {}},
            slot_projection={},
            agent_review_feedback={"status": "normalized", "writeback_allowed": False, "formalized": False, "normalized_feedback": []},
            new_leaf_formalization_packet={"status": "draft_review_packet", "writeback_allowed": False, "formal_target_candidates": [], "blocking_issues": [], "recommended_next_action": "runtime_activation_plan"},
            runtime_activation_plan={"status": "draft_only", "writeback_allowed": False, "proto_vs_formal": {}, "activation_blockers": []},
            formalization_readiness_gate={"status": "blocked", "writeback_allowed": False, "blocking_issues": ["runtime_activation_plan_available"], "recommended_next_action": "fix_evidence"},
        )
        self.assertIn("Agent Review Feedback", report)
        self.assertIn("New Leaf Formalization Packet", report)
        self.assertIn("Runtime Activation Plan", report)
        self.assertIn("Formalization Readiness Gate", report)

    def test_artifact_contract_contains_formalization_factory_artifacts(self) -> None:
        contract = Path("docs/leaf_pre_distill_artifact_contract.md").read_text(encoding="utf-8")
        for name in (
            "agent_review_feedback_input.json",
            "agent_review_feedback_normalized.json",
            "new_leaf_formalization_packet.json",
            "runtime_activation_plan.json",
            "formalization_readiness_checklist.json",
        ):
            self.assertIn(name, contract)


if __name__ == "__main__":
    unittest.main()

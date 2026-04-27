from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import yaml
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.core.dependencies import get_runtime_registry
from app.main import app


class DemoShellSmokeTest(TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        runtime_source = Path(__file__).resolve().parents[1] / "configs" / "question_runtime.yaml"
        runtime_payload = yaml.safe_load(runtime_source.read_text(encoding="utf-8")) or {}
        runtime_payload.setdefault("ui", {})
        runtime_payload["ui"]["distill_access"] = {
            "enabled": True,
            "key": "unit-test-distill-key",
            "cookie_name": "distill_demo_access",
        }
        self.runtime_path = Path(self.tempdir.name) / "question_runtime.yaml"
        self.runtime_path.write_text(yaml.safe_dump(runtime_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

        os.environ["PROMPT_SERVICE_SECURITY_ENABLED"] = "true"
        os.environ["PROMPT_SERVICE_API_TOKEN"] = "demo-token"
        os.environ["PROMPT_RUNTIME_CONFIG_PATH"] = str(self.runtime_path)
        get_settings.cache_clear()
        get_runtime_registry.cache_clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()
        os.environ.pop("PROMPT_SERVICE_SECURITY_ENABLED", None)
        os.environ.pop("PROMPT_SERVICE_API_TOKEN", None)
        os.environ.pop("PROMPT_RUNTIME_CONFIG_PATH", None)
        get_settings.cache_clear()
        get_runtime_registry.cache_clear()

    def test_demo_index_is_public_even_when_security_enabled(self) -> None:
        response = self.client.get("/demo")

        self.assertEqual(response.status_code, 200)
        self.assertIn("言语理解v0.6", response.text)
        self.assertIn('id="builderScreen"', response.text)
        self.assertIn('id="loadingScreen"', response.text)
        self.assertIn('id="resultScreen"', response.text)
        self.assertIn('id="businessSubtype"', response.text)
        self.assertIn('id="specialType"', response.text)
        self.assertIn("/demo-static/app_v2.js", response.text)
        self.assertIn("/demo-static/app_v2_zh_patch.js", response.text)

    def test_demo_static_asset_is_public_even_when_security_enabled(self) -> None:
        response = self.client.get("/demo-static/app_v2.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("QUESTION_FOCUS_OPTIONS", response.text)
        self.assertIn("SPECIAL_TYPE_TREE", response.text)
        self.assertIn("renderSubtypeOptions", response.text)
        self.assertIn("buildGeneratePayload", response.text)
        self.assertIn("renderDistractorPatchPanel", response.text)
        self.assertIn("apply-distractor-patch", response.text)

    def test_demo_page_loads_distill_entry_patch_script(self) -> None:
        response = self.client.get("/demo")

        self.assertEqual(response.status_code, 200)
        self.assertIn("/demo-static/app_v2_zh_patch.js", response.text)

        patch_asset = self.client.get("/demo-static/app_v2_zh_patch.js")
        self.assertEqual(patch_asset.status_code, 200)
        self.assertIn("研发蒸馏台", patch_asset.text)
        self.assertIn("请输入训练入口密钥", patch_asset.text)
        self.assertIn("确认进入", patch_asset.text)
        self.assertIn("/api/v1/distill/access/verify", patch_asset.text)

    def test_distill_demo_redirects_to_main_demo_without_cookie(self) -> None:
        response = self.client.get("/demo/distill", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/demo")

    def test_verify_distill_access_sets_cookie_and_allows_demo(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})

        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["next"], "/demo/distill")
        self.assertIn("distill_demo_access", verify.headers.get("set-cookie", ""))

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn("蒸馏训练工作台", page.text)
        self.assertIn("1. 建样本集", page.text)
        self.assertIn('id="behaviorForm"', page.text)
        self.assertIn('id="behaviorPacketDetail"', page.text)

    def test_distill_demo_exposes_experimental_proto_route_switch(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="datasetExperimentalProtoRoute"', page.text)
        self.assertIn('id="trialExperimentalProtoRoute"', page.text)
        self.assertIn("实验性原型路由", page.text)
        self.assertIn("不会把题型升格为正式题型", page.text)
        self.assertIn("未知子类仍会失败", page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function withExperimentalProtoRoute", script.text)
        self.assertIn("function withExperimentalProtoRouteSamples", script.text)
        self.assertIn("experimental_proto_route: true", script.text)
        self.assertIn("request.extra_constraints", script.text)
        self.assertIn('$("datasetExperimentalProtoRoute").checked', script.text)
        self.assertIn('$("trialExperimentalProtoRoute").checked', script.text)

    def test_distill_demo_exposes_axis_confirmation_stage_one(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="axisConfirmForm"', page.text)
        self.assertIn('id="bootstrapDiscoveryJson"', page.text)
        self.assertIn('id="axisConfirmationJson"', page.text)
        self.assertIn('id="formalPatchDraftJson"', page.text)
        self.assertIn('id="createCanonicalPatchesBtn"', page.text)
        self.assertIn("创建规范目标补丁", page.text)
        self.assertIn("不会写入正式题卡", page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function buildAxisConfirmationArtifact", script.text)
        self.assertIn("function buildFormalPatchDraftArtifact", script.text)
        self.assertIn("function handleCreateCanonicalPatches", script.text)
        self.assertIn("writeback_allowed: false", script.text)
        self.assertIn("formalized: false", script.text)
        self.assertIn("business_feature_card", script.text)
        self.assertIn("validator_contract", script.text)
        self.assertIn("/patches", script.text)

    def test_distill_demo_exposes_formal_writeback_preview_stage_two(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="writebackPreviewForm"', page.text)
        self.assertIn('id="formalWritebackPlanJson"', page.text)
        self.assertIn('id="formalWritebackDiffMd"', page.text)
        self.assertIn('id="generateWritebackPreviewBtn"', page.text)
        self.assertIn('id="copyWritebackPlanToLeafPatchBtn"', page.text)
        self.assertIn("写回计划预览", page.text)
        self.assertIn("不会写入任何文件", page.text)
        self.assertIn("真正写回前仍然必须显式批准", page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function buildFormalWritebackPlanArtifact", script.text)
        self.assertIn("function renderFormalWritebackDiff", script.text)
        self.assertIn("function handleGenerateWritebackPreview", script.text)
        self.assertIn("function handleCopyWritebackPlanToLeafPatch", script.text)
        self.assertIn("writeback_allowed: false", script.text)
        self.assertIn("requires_explicit_approval: true", script.text)
        self.assertIn("formal_writeback_plan_path", script.text)
        self.assertIn("formal_writeback_diff_path", script.text)

    def test_distill_demo_exposes_source_candidate_review_ui(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn("5C. 来源候选人工审查", page.text)
        self.assertIn('id="sourceCandidateReviewForm"', page.text)
        self.assertIn('id="sourceCandidateResultsJsonl"', page.text)
        self.assertIn('id="sourceCandidateReviewList"', page.text)
        self.assertIn('id="generateSourceReviewDecisionsBtn"', page.text)
        self.assertIn('id="fillMockSourceCandidatesBtn"', page.text)
        self.assertIn('id="copySourceReviewDecisionsBtn"', page.text)
        self.assertIn('id="downloadSourceReviewDecisionsBtn"', page.text)
        self.assertIn("不确认原文", page.text)
        self.assertIn("不抓正文", page.text)
        self.assertIn("不会生成材料卡", page.text)
        self.assertIn("种子资产", page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        for decision in (
            "keep_as_original_source_candidate",
            "keep_as_similar_material_seed",
            "keep_as_domain_seed",
            "reject_question_bank",
            "reject_irrelevant",
            "defer",
        ):
            self.assertIn(decision, script.text)
        self.assertIn("function parseSourceCandidateJsonl", script.text)
        self.assertIn("function buildSourceReviewDecisionPayload", script.text)
        self.assertIn("MOCK_SOURCE_CANDIDATE_ROWS", script.text)
        self.assertIn("function handleFillMockSourceCandidates", script.text)
        self.assertIn("allow_risky_seed", script.text)
        self.assertIn("source_candidate_review_decisions.json", script.text)
        self.assertNotIn("verified_original_source: true", script.text)
        self.assertNotIn("verified: true", script.text)
        self.assertNotIn("crawl_allowed: true", script.text)

    def test_distill_demo_exposes_agent_review_feedback_entry(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="agentReviewFeedbackForm"', page.text)
        self.assertIn('id="agentFeedbackRaw"', page.text)
        self.assertIn('id="agentReviewFeedbackInputJson"', page.text)
        self.assertIn('id="generateAgentFeedbackInputBtn"', page.text)
        self.assertIn('id="copyAgentFeedbackInputBtn"', page.text)
        self.assertIn('id="downloadAgentFeedbackInputBtn"', page.text)

        static_root = Path(__file__).resolve().parents[1] / "app" / "demo_static"
        html_text = (static_root / "distill_demo.html").read_text(encoding="utf-8")
        self.assertIn("用户反馈是 evidence", html_text)
        self.assertIn("不直接写回", html_text)
        self.assertIn("不会直接改题卡、材料卡、prompt、validator 或 runtime", html_text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function buildAgentReviewFeedbackInputPayload", script.text)
        self.assertIn("function handleGenerateAgentReviewFeedbackInput", script.text)
        self.assertIn("agent_review_feedback_input.json", script.text)
        self.assertIn("feedback_version: \"v1\"", script.text)
        self.assertNotIn("writeback_allowed: true", script.text)
        self.assertNotIn("formalized: true", script.text)
        self.assertNotIn("verified_original_source: true", script.text)

    def test_verify_distill_access_rejects_wrong_key(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "wrong-key"})

        self.assertEqual(verify.status_code, 401)
        self.assertIn("密钥不正确", verify.text)

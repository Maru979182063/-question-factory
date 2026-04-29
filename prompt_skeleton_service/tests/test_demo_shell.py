from __future__ import annotations

import os
import io
import zipfile
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
        self.assertIn("使用用户材料生成", response.text)
        self.assertIn("进入蒸馏工作台", response.text)
        self.assertNotIn("不是一次性 Prompt 出题", response.text)
        self.assertNotIn("打开试验入口", response.text)
        self.assertNotIn("能力验证入口", response.text)

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
        self.assertIn("蒸馏工作台", patch_asset.text)
        self.assertIn("请输入访问密钥", patch_asset.text)
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
        self.assertIn("蒸馏工作台", page.text)
        self.assertIn("新题卡蒸馏", page.text)
        self.assertIn("历史记录调整蒸馏", page.text)
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

    def test_distill_demo_exposes_formalization_gate_preview_entry(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Formalization Gate Preview", page.text)
        self.assertIn('id="formalizationGatePreviewForm"', page.text)
        self.assertIn('id="formalGateFormalPatchDraftJson"', page.text)
        self.assertIn('id="formalGateMaterialEvidenceSummaryJson"', page.text)
        self.assertIn('id="formalGateAgentFeedbackJson"', page.text)
        self.assertIn('id="formalGateRuntimeActivationPlanJson"', page.text)
        self.assertIn('id="generateFormalGatePreviewBtn"', page.text)
        self.assertIn('id="formalGatePacketPreviewJson"', page.text)
        self.assertIn('id="formalGateReadinessPreviewJson"', page.text)
        self.assertIn('id="workbenchControlPlane"', page.text)
        self.assertIn('data-workbench-layer-target="business_mode"', page.text)
        self.assertIn('data-workbench-layer-target="status_history"', page.text)
        self.assertNotIn('data-workbench-layer-target="data_trial"', page.text)
        self.assertIn('id="saveWorkbenchDraftBtn"', page.text)
        self.assertIn('id="restoreWorkbenchDraftBtn"', page.text)
        self.assertIn('id="exitWorkbenchBtn"', page.text)
        self.assertIn("blocked", page.text)
        self.assertIn("material_card_review_ready", page.text)
        self.assertIn("source seed / similar material", page.text)
        self.assertIn("writeback approval", page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function buildFormalizationGatePreview", script.text)
        self.assertIn("function handleGenerateFormalizationGatePreview", script.text)
        self.assertIn("function setWorkbenchLayer", script.text)
        self.assertIn("function saveWorkbenchDraft", script.text)
        self.assertIn("function restoreWorkbenchDraft", script.text)
        self.assertIn("function exitWorkbench", script.text)
        self.assertIn("WORKBENCH_DRAFT_STORAGE_KEY", script.text)
        self.assertIn("FORMALIZATION_GATE_UNSAFE_FIELDS", script.text)
        self.assertIn("executor_allowed: false", script.text)
        self.assertIn("writeback_allowed: false", script.text)
        self.assertIn("formalized: false", script.text)
        self.assertIn("verified_original_source", script.text)
        self.assertNotIn("executor_allowed: true", script.text)
        self.assertNotIn("writeback_allowed: true", script.text)
        self.assertNotIn("formalized: true", script.text)
        self.assertIn('id="sourceCandidateReviewForm"', page.text)
        self.assertIn('id="agentReviewFeedbackForm"', page.text)

    def test_distill_demo_exposes_behavior_business_summary_entry(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn("历史记录调整蒸馏", page.text)
        self.assertIn("业务视图", page.text)
        self.assertIn("多叶族蒸馏任务工作台", page.text)
        self.assertIn("叶族问题列表", page.text)
        self.assertIn("多任务队列", page.text)
        self.assertIn("一个叶族一个任务", page.text)
        self.assertIn("前后对比", page.text)
        self.assertIn("技术详情", page.text)
        self.assertIn("生成业务视图", page.text)
        self.assertIn("启动任务", page.text)
        self.assertIn('id="businessViewAsyncState"', page.text)
        self.assertIn('id="businessViewStage"', page.text)
        self.assertIn('id="businessViewScopeMode"', page.text)
        self.assertIn('id="businessViewLeafId"', page.text)
        self.assertIn("多叶族", page.text)
        self.assertIn("全部叶族", page.text)
        self.assertIn("生成业务视图", page.text)
        self.assertIn("一个叶族一个任务", page.text)
        self.assertIn("独立验收、暂存、返工、发布和回退", page.text)
        self.assertIn('id="generateBusinessSummaryBtn"', page.text)
        self.assertIn('id="behaviorPacketDetail"', page.text)
        self.assertIn('id="formalizationGatePreviewForm"', page.text)
        self.assertIn('id="businessSummaryBehaviorPacketJson"', page.text)
        self.assertIn('id="businessSummaryBeforeAfterJson"', page.text)
        self.assertIn('id="businessReadableView"', page.text)
        self.assertIn('id="businessViewJson"', page.text)
        self.assertIn('id="businessSummaryJson"', page.text)
        self.assertIn('id="businessSummaryMarkdown"', page.text)
        self.assertIn('id="buildLeafIssueSelectionBtn"', page.text)
        self.assertIn('id="submitLeafIssueTasksBtn"', page.text)
        self.assertIn('id="leafIssueSelectionTable"', page.text)
        self.assertIn('id="leafDistillTaskQueue"', page.text)
        self.assertIn('id="leafDistillAcceptancePanel"', page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function buildBehaviorBusinessSummary", script.text)
        self.assertIn("function buildBehaviorBusinessView", script.text)
        self.assertIn("function renderBusinessReadableView", script.text)
        self.assertIn("function handleLoadBusinessViewExisting", script.text)
        self.assertIn("function handleStartBusinessViewLongTask", script.text)
        self.assertIn("function setBusinessViewAsyncState", script.text)
        self.assertIn("function parseBusinessViewLeafSelection", script.text)
        self.assertIn("function applyBusinessViewLeafScope", script.text)
        self.assertIn("function collectBehaviorActionClusters", script.text)
        self.assertIn("function renderBusinessViewComparePage", script.text)
        self.assertIn("renderBeforeAfterDiff", script.text)
        self.assertIn("function buildLeafIssueRowsFromBusinessView", script.text)
        self.assertIn("function submitLeafIssueTasks", script.text)
        self.assertIn("function confirmLeafTaskPublish", script.text)
        self.assertIn("1 叶族问题选择", script.text)
        self.assertIn("2 多任务队列", script.text)
        self.assertIn("3 多任务验收发布", script.text)
        self.assertIn("提交意见继续蒸馏", script.text)
        self.assertIn("暂存下次继续", script.text)
        self.assertIn("确认发布", script.text)
        self.assertIn("function handleGenerateBusinessSummary", script.text)
        self.assertIn("behavior_distillation_business_summary.json", script.text)
        self.assertIn("behavior_distillation_business_view.json", script.text)
        self.assertIn("behavior_distillation_business_report.md", script.text)
        self.assertNotIn("writeback_allowed: true", script.text)
        self.assertNotIn("formalized: true", script.text)
        self.assertNotIn("executor_allowed: true", script.text)

    def test_distill_demo_exposes_business_mode_entry(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})
        self.assertEqual(verify.status_code, 200)

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn('data-workbench-layer-target="business_mode"', page.text)
        self.assertIn('data-workbench-layer-target="status_history"', page.text)
        self.assertNotIn('data-workbench-layer-target="data_trial"', page.text)
        self.assertNotIn('data-workbench-layer-target="protocol_patch"', page.text)
        self.assertNotIn('data-workbench-layer-target="material_feedback"', page.text)
        self.assertNotIn('data-workbench-layer-target="formalization_gate"', page.text)
        self.assertIn('id="businessModeForm"', page.text)
        self.assertIn('id="businessQuestionPackFile"', page.text)
        self.assertIn('accept=".pdf,.csv,.doc,.docx,.json,.jsonl,.md,.markdown,.txt,.xlsx"', page.text)
        self.assertIn("PDF", page.text)
        self.assertIn("Markdown", page.text)
        self.assertIn('id="businessQuestionPackText"', page.text)
        self.assertIn('id="businessStagePrep"', page.text)
        self.assertIn('id="businessStageSource"', page.text)
        self.assertIn('id="businessStageDraft"', page.text)
        self.assertIn('id="businessStageAcceptance"', page.text)
        self.assertIn('id="businessAsyncLoading"', page.text)
        self.assertIn("材料准备报告", page.text)
        self.assertIn("来源网站确认", page.text)
        self.assertIn("字段草案确认", page.text)
        self.assertIn("蒸馏结果验收", page.text)
        self.assertIn("采用 / 不采用 / 待定", page.text)
        self.assertIn("材料片段", page.text)
        self.assertIn('id="businessSourceUsefulness"', page.text)
        self.assertIn('id="businessManualSourceUrl"', page.text)
        self.assertIn('id="businessManualSourceText"', page.text)
        self.assertIn('id="businessDraftReadiness"', page.text)
        self.assertIn('id="businessGeneratedQuestionJudgment"', page.text)
        self.assertIn('id="businessLandingDecision"', page.text)
        self.assertIn('id="businessRerunSuggestionText"', page.text)
        self.assertIn('id="businessApproveBtn"', page.text)
        self.assertIn('id="businessDeferBtn"', page.text)
        self.assertIn('id="businessRerunBtn"', page.text)
        self.assertIn("业务只需要判断三件事", page.text)
        self.assertIn("这些网址有用，可以继续看", page.text)
        self.assertIn("能用，接近真题", page.text)
        self.assertIn('id="businessProtocolEvidenceJson"', page.text)
        self.assertIn('id="businessGateEvidenceJson"', page.text)
        self.assertIn('id="businessUserFeedbackText"', page.text)
        self.assertIn('id="businessHumanSummary"', page.text)
        self.assertIn('id="businessCardFamilyReportText"', page.text)
        self.assertIn('id="businessModePreviewJson"', page.text)

        script = self.client.get("/demo-static/distill_demo.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn("function buildBusinessModePreview", script.text)
        self.assertIn("function businessHumanGateTranslation", script.text)
        self.assertIn("function businessUserJudgments", script.text)
        self.assertIn("function businessSourceDecisions", script.text)
        self.assertIn("function setBusinessStage", script.text)
        self.assertIn("function setBusinessLoading", script.text)
        self.assertIn("function handleBusinessFinalDecision", script.text)
        self.assertIn("business-linked-question", script.text)
        self.assertIn("business-source-decision", script.text)
        self.assertIn("business-material-excerpt", script.text)
        self.assertIn("manual_source_url", script.text)
        self.assertIn("manual_source_text_excerpt", script.text)
        self.assertIn("source_text_evidence", script.text)
        self.assertIn("function buildBusinessCardFamilyMarkdown", script.text)
        self.assertIn("function handleBusinessQuestionPackFile", script.text)
        self.assertIn("upload_preview_formats", script.text)
        self.assertIn("best_effort_formats", script.text)
        self.assertIn("/api/v1/distill/question-pack/preview", script.text)
        self.assertNotIn("executor_allowed: true", script.text)
        self.assertNotIn("writeback_allowed: true", script.text)
        self.assertNotIn("formalized: true", script.text)

    def test_distill_question_pack_preview_accepts_common_formats(self) -> None:
        response = self.client.post(
            "/api/v1/distill/question-pack/preview",
            headers={"Authorization": "Bearer demo-token"},
            files=[
                ("files", ("sample.json", b'{"samples":[{"sample_id":"s1"}]}', "application/json")),
                ("files", ("sample.csv", "sample_id,stem\ns1,题干".encode("utf-8"), "text/csv")),
                ("files", ("sample.md", "# 题包\n\n- 题目".encode("utf-8"), "text/markdown")),
            ],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["file_count"], 3)
        self.assertEqual(payload["parsed_file_count"], 3)
        self.assertIn(".pdf", payload["supported_formats"])
        self.assertIn(".doc", payload["supported_formats"])
        self.assertIn(".docx", payload["supported_formats"])
        self.assertIn(".xlsx", payload["supported_formats"])
        self.assertIn(".md", payload["supported_formats"])
        self.assertIn("题干", payload["combined_text_excerpt"])

    def test_distill_question_pack_preview_accepts_office_pdf_and_doc(self) -> None:
        response = self.client.post(
            "/api/v1/distill/question-pack/preview",
            headers={"Authorization": "Bearer demo-token"},
            files=[
                ("files", ("sample.docx", _minimal_docx("DOCX question text"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ("files", ("sample.xlsx", _minimal_xlsx("XLSX question text"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                ("files", ("sample.pdf", b"%PDF-1.4\nstream\n(PDF question text) Tj\nendstream\n%%EOF", "application/pdf")),
                ("files", ("sample.doc", b"\xd0\xcf\x11\xe0 legacy DOC question text", "application/msword")),
            ],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["file_count"], 4)
        self.assertGreaterEqual(payload["parsed_file_count"], 3)
        statuses = {item["extension"]: item["status"] for item in payload["files"]}
        self.assertEqual(statuses[".docx"], "parsed")
        self.assertEqual(statuses[".xlsx"], "parsed")
        self.assertIn(statuses[".pdf"], {"degraded", "manual_required"})
        self.assertIn(statuses[".doc"], {"degraded", "manual_required"})
        self.assertIn("DOCX question text", payload["combined_text_excerpt"])
        self.assertIn("XLSX question text", payload["combined_text_excerpt"])

def _minimal_docx(text: str) -> bytes:
    buffer = io.BytesIO()
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _minimal_xlsx(text: str) -> bytes:
    buffer = io.BytesIO()
    shared_strings = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="1" uniqueCount="1">'
        f"<si><t>{text}</t></si></sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>'
    )
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", shared_strings)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


    def test_verify_distill_access_rejects_wrong_key(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "wrong-key"})

        self.assertEqual(verify.status_code, 401)
        self.assertIn("密钥不正确", verify.text)

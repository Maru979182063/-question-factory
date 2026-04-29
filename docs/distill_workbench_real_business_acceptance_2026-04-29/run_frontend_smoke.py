# -*- coding: utf-8 -*-
"""Local browser smoke for the distill workbench business flow."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(r"E:\agent_repo_src")
OUT = ROOT / "docs" / "distill_workbench_real_business_acceptance_2026-04-29"
DOCX = ROOT / "data" / "manual_test_packs" / "relative_absolute_business_acceptance.docx"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def write_value(page, selector, value):
    if page.locator(selector).count() == 0:
        return
    page.eval_on_selector(
        selector,
        """(el, value) => {
          el.value = value;
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        value,
    )


protocol_payload = {
    "family_context": {
        "mother_family_id": "detail_understanding",
        "child_family_id": "fast_location_method",
        "leaf_label": "相对绝对项",
        "business_subtype": "relative_absolute_item",
        "question_focus": "细节理解题 / 快速定位法 / 相对绝对项",
    },
    "sample_count": 3,
    "source_files": [str(DOCX)],
    "leaf_detection": {
        "known_mother_family": False,
        "known_child_family": False,
        "requires_manual_naming": True,
        "suggested_name": "细节理解题 / 快速定位法 / 相对绝对项",
    },
    "candidate_axes": [
        {"name": "相对绝对词识别"},
        {"name": "原文范围定位"},
        {"name": "绝对化错项"},
    ],
    "core_features": [
        "正确答案必须能在材料中定位依据。",
        "错项常出现绝对化、范围扩大、条件遗漏。",
        "材料需要保留完整上下文和限定词。",
        "业务命名需要人工确认母族、子族、叶族。",
    ],
    "formal_patch_draft": {
        "status": "draft_only",
        "formalized": False,
        "writeback_allowed": False,
        "targets": ["business_feature_card", "signal_layer", "prompt_assets", "validator_contract"],
    },
}

gate_payload = {
    "status": "blocked",
    "source_candidates": [
        {
            "domain": "local.demo",
            "url": "local://demo/relative-absolute/001",
            "source_risk": "low",
            "material_excerpt": "近年来，部分城市在推进公共服务数字化时，并非所有事项都适合完全线上办理。对于老年人、残障人士以及需要现场核验身份的事项，线下窗口仍然具有不可替代作用。",
            "linked_questions": [
                {"sample_id": "relative_absolute_001", "stem": "下列说法与材料相符的是？"},
                {"sample_id": "relative_absolute_002", "stem": "以下哪项没有扩大原文范围？"},
            ],
        },
        {
            "domain": "gov.example",
            "url": "local://demo/relative-absolute/002",
            "source_risk": "low",
            "material_excerpt": "改革方案提出，应优先压缩重复证明材料；对确需现场办理的事项，保留必要窗口并提供预约服务。",
            "linked_questions": [{"sample_id": "relative_absolute_003", "stem": "根据材料，改革方案强调的是哪一项？"}],
        },
        {
            "domain": "某公考题库站",
            "url": "https://example.invalid/question-bank",
            "source_risk": "question_bank_like",
            "material_excerpt": "页面主要展示题干、选项、正确答案和答案解析，缺少可作为自然原文的连续材料。",
            "linked_questions": [{"sample_id": "relative_absolute_004", "stem": "疑似答案解析页转载，不作为材料来源。"}],
        },
    ],
    "material_evidence_summary": {
        "source_text_evidence_status": "available",
        "source_text_evidence_count": 3,
        "source_text_available_count": 2,
        "source_text_manual_required_count": 1,
        "source_gold_alignment_status": "needs_human_review",
        "source_gold_alignment_count": 2,
        "source_gold_alignment_needs_human_review_count": 2,
        "material_quality_regression_status": "blocked",
        "verified_original_source_count": 0,
        "requires_source_review": True,
        "requires_alignment_review": True,
        "requires_material_quality_review": True,
        "ready_for_material_card_review": False,
        "ready_for_material_card_formalization": False,
        "blocking_issues": [
            "当前来源主要是本地/manual 正文证据，尚未完成 source/gold 人审。",
            "材料质量回归仍为 blocked。",
        ],
    },
    "material_card_draft": {
        "status": "draft_only",
        "formalized": False,
        "writeback_allowed": False,
        "material_requirements": {
            "must_contain": ["限定词", "范围条件", "可定位原文句"],
            "document_genre_candidates": ["政务服务说明", "评论", "新闻报道"],
            "material_structure_label_candidates": ["现象-限定-措施", "背景-条件-结论"],
        },
    },
    "readiness_gate": {
        "status": "blocked",
        "recommended_next_action": "人工确认来源正文和对齐关系；补充真实来源或更完整正文。",
    },
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sample_text = (
        "母族：细节理解题\n"
        "子族：快速定位法\n"
        "叶族：相对绝对项\n\n"
        "题包包含 3 道题。系统应先识别是否需要新叶族命名，再让业务确认候选来源、初始字段和试生成结果。"
    )
    formal_patch = {
        "status": "draft_only",
        "formalized": False,
        "writeback_allowed": False,
        "family_context": protocol_payload["family_context"],
        "targets": ["business_feature_card", "signal_layer", "prompt_assets", "validator_contract"],
    }
    feedback = {
        "status": "normalized",
        "writeback_allowed": False,
        "formalized": False,
        "normalized_feedback": [
            {
                "dimension": "material_too_short",
                "severity": "high",
                "target_line": "material_line",
                "requires_regression": True,
                "requires_human_review": True,
            },
            {
                "dimension": "distractor_weakness",
                "severity": "medium",
                "target_line": "question_card",
                "requires_regression": True,
                "requires_human_review": True,
            },
        ],
    }
    truth_gold = {"summary": {"ready_for_formalization": False}, "gold_source": "gold_reconstruction_results"}
    runtime_plan = {
        "status": "draft_only",
        "formalized": False,
        "writeback_allowed": False,
        "proto_vs_formal": {
            "can_run_proto_trial": True,
            "can_run_formal_generation": False,
            "blocked_reasons": ["material evidence review missing"],
        },
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=str(CHROME),
            args=["--disable-gpu", "--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.goto("http://127.0.0.1:8011/demo-static/distill_demo.html", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "01_business_entry.png"), full_page=True)

        page.click('[data-workbench-layer-target="business_mode"]')
        if DOCX.exists():
            page.set_input_files("#businessQuestionPackFile", str(DOCX))
        write_value(page, "#businessQuestionPackText", sample_text)
        write_value(page, "#businessProtocolEvidenceJson", json.dumps(protocol_payload, ensure_ascii=False, indent=2))
        write_value(page, "#businessGateEvidenceJson", json.dumps(gate_payload, ensure_ascii=False, indent=2))
        page.click("#businessRunParseBtn")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "02_material_prep_report.png"), full_page=True)

        page.click('[data-business-stage-target="source"]')
        page.wait_for_timeout(400)
        selects = page.locator(".business-source-decision")
        if selects.count() >= 3:
            selects.nth(0).select_option("adopt")
            selects.nth(1).select_option("defer")
            selects.nth(2).select_option("reject")
        page.select_option("#businessSourceUsefulness", "similar_only")
        write_value(page, "#businessSourceReviewText", "local.demo 可继续审查；gov.example 先待定；题库站不采用。当前仍不确认原文。")
        write_value(page, "#businessManualSourceUrl", "local://demo/relative-absolute/manual-source")
        write_value(page, "#businessManualSourceText", "人工补充材料片段：公共服务数字化不能简单等同于完全线上办理，仍需保留线下兜底。")
        page.screenshot(path=str(OUT / "03_source_review_stage.png"), full_page=True)

        page.click('[data-business-stage-target="draft"]')
        page.wait_for_timeout(400)
        page.select_option("#businessDraftReadiness", "needs_more_material")
        write_value(page, "#businessDraftReviewText", "相对绝对项字段方向成立，但材料来源和对齐关系还需要人工确认。")
        page.screenshot(path=str(OUT / "04_initial_field_draft_stage.png"), full_page=True)

        page.click('[data-business-stage-target="acceptance"]')
        page.wait_for_timeout(400)
        page.select_option("#businessGeneratedQuestionJudgment", "not_usable")
        write_value(page, "#businessGeneratedQuestionText", "样题方向接近，但干扰项还不够迷惑，材料依据偏短。")
        write_value(page, "#businessRerunSuggestionText", "重跑时增加限定词错项、范围扩大错项，并补充更完整材料。")
        page.select_option("#businessLandingDecision", "hold_material")
        write_value(page, "#businessUserFeedbackText", "材料还偏短，干扰项不够迷惑；当前不要正式落位，先补来源正文和材料对齐。")
        page.click("#businessRerunBtn")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "05_acceptance_rerun_button.png"), full_page=True)
        page.click("#businessDeferBtn")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "06_acceptance_defer_button.png"), full_page=True)
        page.click("#businessApproveBtn")
        page.wait_for_timeout(300)
        page.click("#generateBusinessModeReportBtn")
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "07_acceptance_report_after_confirm_attempt.png"), full_page=True)

        page.click("#saveWorkbenchDraftBtn")
        page.wait_for_timeout(300)
        page.click("#restoreWorkbenchDraftBtn")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "08_save_restore_state.png"), full_page=True)

        page.click('[data-workbench-layer-target="material_feedback"]')
        page.wait_for_timeout(500)
        candidate = {
            "sample_id": "relative_absolute_001",
            "query": "公共服务 数字化 线下窗口 老年人",
            "title": "公共服务数字化与线下服务保留",
            "url": "local://demo/relative-absolute/001",
            "domain": "local.demo",
            "snippet": "部分城市推进公共服务数字化，但并非所有事项都适合完全线上办理。",
            "source_risk": "low",
            "candidate_status": "weak_candidate",
            "candidate_score": 0.42,
            "verification_status": "unverified",
            "verified": False,
        }
        write_value(page, "#sourceCandidateResultsJsonl", json.dumps(candidate, ensure_ascii=False))
        page.click("#loadSourceCandidatesBtn")
        page.wait_for_timeout(500)
        page.click("#generateSourceReviewDecisionsBtn")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "09_source_candidate_review_decisions.png"), full_page=True)

        write_value(page, "#agentFeedbackRaw", "太简单了，材料也太短，干扰项不够迷惑，不像真题。")
        page.click("#generateAgentFeedbackInputBtn")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "10_agent_feedback_input.png"), full_page=True)

        page.click('[data-workbench-layer-target="formalization_gate"]')
        page.wait_for_timeout(500)
        write_value(page, "#formalGateFormalPatchDraftJson", json.dumps(formal_patch, ensure_ascii=False, indent=2))
        write_value(page, "#formalGateMaterialCardDraftJson", json.dumps(gate_payload["material_card_draft"], ensure_ascii=False, indent=2))
        write_value(page, "#formalGateMaterialEvidenceSummaryJson", json.dumps(gate_payload["material_evidence_summary"], ensure_ascii=False, indent=2))
        write_value(page, "#formalGateAgentFeedbackJson", json.dumps(feedback, ensure_ascii=False, indent=2))
        write_value(page, "#formalGateSourceReviewJson", json.dumps({"accepted_count": 2, "verified_original_source_count": 0}, ensure_ascii=False, indent=2))
        write_value(page, "#formalGateTruthGoldRegressionJson", json.dumps(truth_gold, ensure_ascii=False, indent=2))
        write_value(page, "#formalGateRuntimeActivationPlanJson", json.dumps(runtime_plan, ensure_ascii=False, indent=2))
        page.click("#generateFormalGatePreviewBtn")
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "11_formalization_gate_blocked_preview.png"), full_page=True)

        result = {}
        for key, selector in {
            "business_mode_preview_json": "#businessModePreviewJson",
            "source_review_decisions_json": "#sourceReviewDecisionsJson",
            "agent_feedback_input_json": "#agentReviewFeedbackInputJson",
            "formal_gate_readiness_preview_json": "#formalGateReadinessPreviewJson",
        }.items():
            loc = page.locator(selector)
            result[key] = loc.input_value() if loc.count() else ""
        (OUT / "frontend_smoke_outputs.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()

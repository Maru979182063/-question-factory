# material_protocol_draft full evidence smoke 报告

日期：2026-04-26

## 1. 本轮目标

本轮目标是用已有完整材料线 evidence 重新跑 `material_protocol_draft` 工作台，验证草案是否真正引用了已有 evidence，而不是生成空草案。

本轮不是功能扩展，也不是正式落位。本轮没有网络访问、没有正文抓取、没有 source verification、没有 passage_service ingest、没有 material promotion、没有 material_card 写回、没有 card_specs 写回、没有 runtime / prompt / validator / generation 主链修改。

## 2. resolved_evidence_paths

根目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425`

本轮实际使用的 evidence：

| evidence | resolved path | status |
| --- | --- | --- |
| manifest | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/manifest.json` | found |
| gold_reconstruction_results | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl` | found |
| source_discovery_queries | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/source_discovery_queries.jsonl` | found |
| material_source_profile | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/material_source_profile.json` | found |
| source_candidate_summary | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_web_smoke/source_candidate_summary.json` | found |
| source_candidate_review | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_candidate_review.json` | found |
| source_seed_registry | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_seed_registry.jsonl` | found |
| crawl_seed_manifest | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/crawl_seed_manifest.json` | found |
| truth_gold_regression_results | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_regression_results.json` | found |
| truth_gold_split_manifest | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_split_manifest.json` | found on disk, but current material_protocol_draft CLI has no explicit split-manifest argument |

备注：本轮不改功能，所以没有为 `truth_gold_split_manifest` 临时新增参数。该项保留为工具侧 evidence gap。

## 3. dry-run 结果

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_dry_run`

生成 artifacts：

- `system_alignment_findings.json`
- `material_protocol_draft_input_digest.json`
- `material_protocol_assets_draft_report.md`

dry-run 结果正常：

- 系统对齐完成；
- evidence 路径解析完成；
- 未生成最终 draft；
- 未调用模型；
- 未访问网络；
- 未写任何正式配置。

## 4. mock 结果

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_mock_smoke`

生成 artifacts：

- `system_alignment_findings.json`
- `material_protocol_draft_input_digest.json`
- `material_card_draft.json`
- `material_line_prompt_assets_draft.json`
- `material_quality_regression_draft.json`
- `material_review_prompts.md`
- `material_bridge_mapping_draft.json`
- `material_protocol_assets_draft_report.md`

mock 结果正常。核心检查结果：

- family_context 正确解析为当前 artifact 的题包上下文；
- evidence_refs 已引用 gold reconstruction、source discovery、source review、seed registry、crawl manifest；
- 所有 draft 均保持 `status=draft_only`；
- 所有 draft 均保持 `formalized=false`；
- 所有 draft 均保持 `writeback_allowed=false`；
- 所有 draft 均保持 `requires_human_review=true`；
- 所有 draft 均保持 `requires_regression=true`；
- 未发现 `verified=true`；
- 未发现 `verified_original_source=true`；
- 未发现 `crawl_allowed=true`；
- 未发现 `material_library_write=true`；
- 未发现 `card_specs_write=true`；
- 未发现 `promotion_allowed=true`。

## 5. LLM smoke 是否执行

本轮没有执行真实 LLM smoke。

原因：

- 当前环境没有设置 `LEAF_PRE_DISTILL_LLM_API_KEY`；
- 当前环境没有设置 `LEAF_PRE_DISTILL_LLM_BASE_URL`；
- 虽然环境中存在 `OPENAI_API_KEY`，但本轮要求使用低成本 chat endpoint，且不能把历史 key 或 base URL 写入命令、日志或文档；
- 本轮禁止网络访问和外部 source 操作，mock 已足够验证完整 evidence 接入。

结论：

- 工具链与 evidence 接入通过；
- LLM 语义草案尚未验证；
- 不进入 material_card review；
- 若下一步要跑 LLM，应先在环境变量中配置 `LEAF_PRE_DISTILL_LLM_API_KEY` 和 `LEAF_PRE_DISTILL_LLM_BASE_URL`，再单独执行一次受控 LLM smoke。

## 6. evidence gaps 前后对比

上一轮 mock smoke 使用根 artifact 目录，未显式传入材料线证据，出现 9 个 gaps：

- `gold_reconstruction_results`
- `truth_gold_regression_results`
- `truth_gold_split_manifest`
- `source_discovery_queries`
- `material_source_profile`
- `source_candidate_summary`
- `source_candidate_review`
- `source_seed_registry`
- `crawl_seed_manifest`

本轮显式传入完整 evidence 后，gaps 降为 1 个：

- `truth_gold_split_manifest`

该 gap 的原因不是文件不存在，而是当前 `material_protocol_draft` CLI 尚无显式 `--truth-gold-split-manifest` 参数。本轮是 smoke，不扩功能，所以保留为后续小修项。

## 7. material_card_draft 摘要

`material_card_draft.evidence_refs` 已引用：

- `manifest`
- `gold_reconstruction_results`
- `truth_gold_regression_results`
- `source_discovery_queries`
- `material_source_profile`
- `source_candidate_summary`
- `source_candidate_review`
- `source_seed_registry`
- `crawl_seed_manifest`
- `initial_plan_doc`

关键边界仍然存在：

- `cleaning_and_slicing_hypothesis.source_body_required=true`
- `cleaning_and_slicing_hypothesis.source_gold_alignment_required=true`
- `quality_gate_draft.requires_material_quality_regression=true`
- `source_policy.requires_source_verification_before_formalization=true`
- `source_policy.verified_original_source_required_for_original_source_claim=true`

判断：

- 草案已经能吃到已有 evidence；
- 没有把 source seed 当 verified source；
- 没有声称已经有 source body；
- 没有声称已经完成 source/gold alignment；
- 仍不能 formalize。

## 8. material_line_prompt_assets_draft 摘要

prompt assets draft 包含：

- `source_evidence_review`
- `source_gold_alignment`
- `material_transformation_hypothesis`
- `material_quality_review`
- `material_card_draft`

每个 prompt 都保留：

- `status=draft_only`
- `formalized=false`
- `writeback_allowed=false`
- `requires_human_review=true`
- `requires_regression=true`

全局 forbidden actions 包含：

- `confirm_original_source`
- `set_verified_true`
- `write_material_card`
- `write_card_specs`
- `modify_question_card`
- `modify_prompt_assets`
- `modify_validator_contract`
- `modify_runtime_mapping`
- `promote_material`
- `call_material_ingest`

判断：

- prompt assets 仍是通用草案；
- 没有正式写入 prompt assets；
- 没有要求模型替代 source verification 或 material approval。

## 9. material_quality_regression_draft 摘要

维度包含：

- `source_provenance_status`
- `question_bank_contamination`
- `source_gold_alignment`
- `material_independence`
- `material_sufficiency`
- `slicing_quality`
- `family_fit`
- `distractor_support`
- `overfit_or_copy_risk`
- `bridge_compatibility`
- `insurance_holdout_performance`

每个 dimension 均包含：

- `method`
- `confidence`
- `limitation`
- `requires_human_review`
- `requires_future_evidence`

判断：

- 覆盖了来源、污染、对齐、独立性、充分性、切片、题型适配、干扰项支持、过拟合风险、桥接兼容和 holdout；
- 没有宣称评分可替代人审；
- 没有宣称 low contamination 等于原文确认。

## 10. material_bridge_mapping_draft 摘要

target runtime：

`MaterialV2SearchRequest`

使用的仓库确认字段：

- `business_family_id`
- `question_card_id`
- `business_card_ids`
- `preferred_business_card_ids`
- `query_terms`
- `topic`
- `text_direction`
- `document_genre`
- `material_structure_label`
- `target_length`
- `length_tolerance`
- `structure_constraints`
- `status`
- `release_channel`
- `review_gate_mode`

默认值来自 `question_runtime.yaml` 的真实材料配置：

- `status=promoted`
- `release_channel=stable`
- `review_gate_mode=stable_relaxed`

判断：

- bridge mapping draft 基于 `system_alignment_findings`；
- 没有调用 `/materials/v2/search`；
- 没有修改 `question_runtime.yaml`；
- 没有写 runtime mapping。

## 11. system_alignment_findings 摘要

系统对齐检查了 13 个文件。

确认到的关键系统落点：

- `passage_service` 的 articles / materials / materials_v2 / crawl routes；
- `MaterialV2SearchRequest`；
- `MaterialBridgeV2Service.select_materials`；
- `prompt_skeleton_service/configs/question_runtime.yaml` 的 materials 配置；
- `card_specs/normalized/material_cards` 的现有材料卡 shape；
- `card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml`；
- `passage_service/app/config/material_governance.yaml`。

现有 material card shape 关键字段包括：

- `card_id`
- `display_name`
- `selection_core`
- `structures`
- `required_signals`
- `preferred_signals`
- `avoid_signals`
- `candidate_contract`
- `card_bias`
- `default_generation_archetype`
- `distractor_bias`

判断：

- 草案以仓库真实字段为准；
- 没有把设计文档里的 proposed 字段冒充 existing 字段；
- `material_card_draft` 中新增的 evidence/source/quality 字段仍是 draft/proposed。

## 12. hardcoded family 风险

本轮 family_context 来自当前 artifact：

```json
{
  "mother_family_id": "word_usage",
  "child_family_id": "word_usage_content_word",
  "leaf_label": "实词",
  "business_subtype": "word_usage_content_word",
  "question_focus": "word_usage",
  "question_card_reference": null,
  "material_card_id_draft": "proto.word_usage.word_usage_content_word.material.v0"
}
```

这是当前 smoke 的样例上下文，不是工具写死的全局规则。

判断：

- 未发现 `hardcoded_only_word_usage` 或等价越权信号；
- mock draft 的通用 prompt 类别未把 word_usage 当成唯一题型；
- 后续仍建议用非 word_usage artifact 再做一次 cross-family smoke。

## 13. source seed 被误当 verified source 的风险

检查结果：

- 未发现 `verified=true`；
- 未发现 `verified_original_source=true`；
- 未发现 `crawl_allowed=true`；
- `crawl_seed_manifest` 仍是 seed/crawl review 入口，不是 crawl approval；
- `material_card_draft` 仍要求 source verification 才能 formalize。

判断：本轮没有把 source seed 误当 verified source。

## 14. formalization 越权风险

检查结果：

- 未发现 `formalized=true`；
- 未发现 `writeback_allowed=true`；
- 未发现 `card_specs_write=true`；
- 未发现 `promotion_allowed=true`；
- 未改 `card_specs`；
- 未改 runtime mapping；
- 未改 prompt assets；
- 未改 validator；
- 未改 question_card。

判断：本轮没有 formalization 越权。

## 15. 下一步建议

建议分两步：

1. 小修 `material_protocol_draft` 输入能力：增加可选 `--truth-gold-split-manifest`，让 split manifest 也能显式进入 digest，消除当前唯一 gap。
2. 在环境变量安全配置完成后，单独跑一次 LLM smoke：
   - `LEAF_PRE_DISTILL_LLM_API_KEY`
   - `LEAF_PRE_DISTILL_LLM_BASE_URL`
   - `--mode llm`
   - `--max-input-chars 12000`
   - `--max-output-tokens 3500`

如果 LLM smoke 通过，可以进入 `material_protocol_draft human review`。

即使 LLM 通过，也仍然不能写回。后续合理方向仍是：

```text
人工审查 material_protocol_draft
-> crawl_approval + source_body_fetch 审计/计划
-> 小样本正文抓取 approval
-> source/gold alignment
-> material_quality_regression
-> material_card_draft review
```

## 16. 本轮明确未做事项

本轮没有：

- 网络访问；
- 正文抓取；
- source verification；
- source/gold alignment；
- passage_service ingest；
- material promotion；
- material_card 写回；
- card_specs 写回；
- runtime mapping 写回；
- prompt_assets 正式写回；
- validator 写回；
- question_card 修改；
- generation / validator / prompt / runtime 主链修改；
- API / UI 修改；
- 新增 promotion target。


# material_protocol_draft full evidence LLM smoke 执行报告

日期：2026-04-26

## 1. 修改文件

本轮只补了一个 evidence 输入能力，并运行 smoke。

修改文件：

- `tools/leaf_pre_distill/material_protocol_draft.py`
- `tools/leaf_pre_distill/run.py`
- `tests/test_leaf_pre_distill.py`

新增报告：

- `docs/material_protocol_draft_full_evidence_llm_execution_report_2026-04-26.md`

## 2. `--truth-gold-split-manifest` 接入情况

已接入。

新增能力：

- `tools.leaf_pre_distill.material_protocol_draft` 支持 `--truth-gold-split-manifest`。
- `run_material_protocol_draft(...)` 支持 `truth_gold_split_manifest` 参数。
- digest 中新增 `truth_gold_split_summary`。
- `truth_gold_split_manifest.json` 会进入：
  - `material_protocol_draft_input_digest.json.evidence_paths`
  - `material_protocol_draft_input_digest.json.truth_gold_split_summary`
  - mock 产物的 `material_card_draft.evidence_refs`
  - `material_protocol_assets_draft_report.md` 的 evidence gap 统计

新增测试覆盖：

- `test_material_protocol_draft_accepts_truth_gold_split_manifest_path`

## 3. resolved evidence paths

根目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425`

本轮使用：

| evidence | resolved path |
| --- | --- |
| manifest | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/manifest.json` |
| gold_reconstruction_results | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl` |
| truth_gold_regression_results | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_regression_results.json` |
| truth_gold_split_manifest | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_split_manifest.json` |
| source_discovery_queries | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/source_discovery_queries.jsonl` |
| material_source_profile | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/material_source_profile.json` |
| source_candidate_summary | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_web_smoke/source_candidate_summary.json` |
| source_candidate_review | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_candidate_review.json` |
| source_seed_registry | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_seed_registry.jsonl` |
| crawl_seed_manifest | `E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/crawl_seed_manifest.json` |

## 4. dry-run 结果

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_split_dry_run`

结果：

- 生成 `system_alignment_findings.json`
- 生成 `material_protocol_draft_input_digest.json`
- 生成 `material_protocol_assets_draft_report.md`
- evidence gaps = 0
- `truth_gold_split_manifest` 已进入 digest
- 未调用 LLM
- 未生成最终 draft
- 未写正式配置

## 5. mock 结果

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_split_mock_smoke`

结果：

- evidence gaps = 0
- `material_card_draft.evidence_refs` 已包含 `truth_gold_split_manifest`
- `material_card_draft` / `material_line_prompt_assets_draft` / `material_quality_regression_draft` / `material_bridge_mapping_draft` 均生成
- 所有 draft 保持：
  - `status=draft_only`
  - `formalized=false`
  - `writeback_allowed=false`
  - `requires_human_review=true`
  - `requires_regression=true`

## 6. LLM smoke 是否执行

已执行。

执行方式：

- `mode=llm`
- `model=chat`
- `max_input_chars=12000`
- `max_output_tokens=3500`
- key 通过环境变量读取
- base_url 通过环境变量读取
- 未在报告中记录 key

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke`

## 7. LLM 成功/失败

LLM smoke 失败，状态为 blocked。

结果：

- `system_alignment_findings.json` 已生成
- `material_protocol_draft_input_digest.json` 已生成
- `material_protocol_assets_draft_report.md` 已生成
- `material_card_draft.json` 未生成
- `material_line_prompt_assets_draft.json` 未生成
- `material_quality_regression_draft.json` 未生成
- `material_bridge_mapping_draft.json` 未生成

blocked 原因：

- LLM 单次请求进入后发生 read timeout。

说明：

- 工具没有写假草案；
- 没有把失败输出当成功；
- 没有循环扩大；
- 没有批量重试；
- 这符合本轮“JSON 失败或请求失败则 blocked，不写假草案”的验收边界。

## 8. evidence gaps

dry-run：

- evidence gaps = 0

mock：

- evidence gaps = 0

LLM：

- evidence gaps = 0
- LLM blocked 与 evidence 无关，是单次请求 timeout。

## 9. material_card_draft 摘要

mock 产物中：

- `material_card_id_draft=proto.word_usage.word_usage_content_word.material.v0`
- `family_binding` 来自 artifact 的 family context；
- `evidence_refs` 已引用完整 evidence；
- `source_body_required=true`
- `source_gold_alignment_required=true`
- `requires_material_quality_regression=true`
- `requires_source_verification_before_formalization=true`
- 未出现 `verified=true`
- 未出现 `verified_original_source=true`
- 未出现 `crawl_allowed=true`
- 未出现 `writeback_allowed=true`

LLM 产物中：

- 未生成 `material_card_draft.json`；
- 原因是 LLM blocked；
- 没有写假草案。

## 10. prompt_assets_draft 摘要

mock 产物中包含：

- `source_evidence_review`
- `source_gold_alignment`
- `material_transformation_hypothesis`
- `material_quality_review`
- `material_card_draft`

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

LLM 产物中：

- 未生成 prompt assets draft；
- 原因是 LLM blocked。

## 11. quality_regression_draft 摘要

mock 产物中包含维度：

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

每个维度包含：

- `method`
- `confidence`
- `limitation`
- `requires_human_review`
- `requires_future_evidence`

LLM 产物中：

- 未生成 quality regression draft；
- 原因是 LLM blocked。

## 12. bridge_mapping_draft 摘要

mock 产物中：

- `target_runtime=MaterialV2SearchRequest`
- `system_alignment_findings_ref=system_alignment_findings.json`
- 使用仓库确认字段：
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

未调用 `/materials/v2/search`，未修改 `question_runtime.yaml`。

LLM 产物中：

- 未生成 bridge mapping draft；
- 原因是 LLM blocked。

## 13. hardcoded family 风险

本轮工具仍从 artifact 解析 family context。

当前 family context 是本次 smoke 样例值：

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

判断：

- mock 产物未把 word_usage 写成通用规则；
- LLM 未生成草案，因此不存在 LLM 写死 family 的产物风险；
- 后续仍建议用非 word_usage artifact 做一次 cross-family smoke。

## 14. source seed 被误当 verified source 风险

检查结果：

- 未出现 `verified=true`
- 未出现 `verified_original_source=true`
- 未出现 `crawl_allowed=true`
- `crawl_seed_manifest` 仍只是 evidence/ref，不是 crawl approval
- `material_card_draft` 仍要求 source verification

判断：

- 没有把 source seed 误当 verified source。

## 15. formalization 越权风险

检查结果：

- 未出现 `formalized=true`
- 未出现 `writeback_allowed=true`
- 未出现 `card_specs_write=true`
- 未出现 `promotion_allowed=true`
- 未写 material_card
- 未写 card_specs
- 未写 runtime mapping
- 未写 prompt_assets
- 未写 validator
- 未改 question_card

判断：

- 没有 formalization 越权。

## 16. 测试命令和结果

已运行：

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：

- 70 tests passed

已运行：

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

结果：

- 10 tests passed

已运行：

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

结果：

- 4 tests passed

已运行：

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

结果：

- 10 tests passed

## 17. 本轮明确未做事项

本轮没有：

- 网页搜索；
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

说明：本轮按要求调用了一次 LLM endpoint 做 smoke；除此之外没有进行网页、爬虫、材料来源访问。

## 18. 下一步建议

当前结论：

- evidence 输入链路已补齐；
- dry-run/mock 均通过；
- LLM smoke 已执行但被 timeout blocked；
- 工具行为正确：没有写假草案。

下一步建议：

1. 不进入 material_card review，因为 LLM 语义草案没有生成。
2. 做一刀很小的 LLM prompt / client hardening：
   - 增加可选 `--timeout-seconds` 参数；
   - 在 report 中记录 timeout 配置；
   - 可考虑把 digest 再压短到 8000 chars；
   - 仍然只允许单次 smoke，不做批量。
3. hardening 后再跑一次 LLM smoke。


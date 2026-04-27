# material_protocol_split_pipeline 分工位执行韧性执行报告

日期：2026-04-27

## 1. 本轮目标

本轮只给 `material_protocol_split_pipeline` 补执行韧性：

- stage checkpoint；
- stage-level retry；
- stage report；
- resume from checkpoint。

本轮没有改 6 个工位定义，没有新增正式写回，没有改主链业务边界。

## 2. 修改文件清单

新增：

- `tools/leaf_pre_distill/material_protocol_split_state.py`
- `tools/leaf_pre_distill/material_protocol_split_runtime.py`
- `tools/leaf_pre_distill/material_protocol_split_stage_report.py`
- `docs/material_protocol_split_pipeline_resilience_execution_report_2026-04-27.md`

修改：

- `tools/leaf_pre_distill/material_protocol_split_pipeline.py`
- `tests/test_leaf_pre_distill.py`

## 3. checkpoint 实现

新增 `stages/` 目录，按固定顺序落盘：

- `stages/01_material_evidence_map.json`
- `stages/02_material_semantic_requirements_draft.json`
- `stages/03_material_card_draft.json`
- `stages/04_material_line_prompt_assets_draft.json`
- `stages/05_material_quality_regression_draft.json`
- `stages/06_material_bridge_mapping_draft.json`

每个 stage 只要成功，就立即写入对应文件，并更新 `pipeline_state.json`。

效果：

- 后续 stage 失败不会丢掉前面成功 stage；
- provider 502 时可以保留已完成产物；
- mock / llm / dry-run 都有状态文件和 stage report。

## 4. retry 实现

新增 stage-level retry：

- 默认每个 stage 最多 retry 1 次；
- retry 只作用于当前 stage；
- 前面已成功 stage 不会重新执行；
- retry 记录在 `pipeline_state.json.stages[stage].retry_count` 和 `attempts` 中。

CLI 参数：

```powershell
--max-stage-retries 1
```

默认值为 1。

## 5. report 实现

新增：

- `pipeline_stage_report.json`
- `pipeline_stage_report.md`

报告字段包括：

- 每个 stage 的 status；
- output_path；
- error_summary；
- retry_count；
- duration_seconds；
- pipeline_complete；
- blocked；
- status_counts。

支持状态：

- `success`
- `skipped`
- `pending`
- `retrying`
- `provider_error`
- `validation_error`
- `blocked`

## 6. resume 实现

新增 resume 能力：

```powershell
--resume
```

行为：

- 如果 `pipeline_state.json` 中某 stage 是 `success`，且 output_path 存在，则跳过该 stage；
- 被跳过 stage 状态记录为 `skipped`；
- 继续执行后续未完成 stage；
- resume 不会绕过 checker。

## 7. 如何运行

mock 样本：

```powershell
python -m tools.leaf_pre_distill.material_protocol_split_pipeline `
  --artifact-dir E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425 `
  --gold-reconstruction-results E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl `
  --truth-gold-regression-results E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_regression_results.json `
  --truth-gold-split-manifest E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_split_manifest.json `
  --source-discovery-queries E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/source_discovery_queries.jsonl `
  --material-source-profile E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/material_source_profile.json `
  --source-candidate-summary E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_web_smoke/source_candidate_summary.json `
  --source-candidate-review E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_candidate_review.json `
  --source-seed-registry E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_seed_registry.jsonl `
  --crawl-seed-manifest E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/crawl_seed_manifest.json `
  --output-dir E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_split_pipeline_resilient_mock_sample `
  --mode mock
```

resume 示例：

```powershell
python -m tools.leaf_pre_distill.material_protocol_split_pipeline ...同上参数... --mode llm --resume
```

## 8. 样本输出

本轮生成 mock 样本：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_split_pipeline_resilient_mock_sample`

包含：

- `pipeline_state.json`
- `pipeline_stage_report.json`
- `pipeline_stage_report.md`
- `stages/01_material_evidence_map.json`
- `stages/02_material_semantic_requirements_draft.json`
- `stages/03_material_card_draft.json`
- `stages/04_material_line_prompt_assets_draft.json`
- `stages/05_material_quality_regression_draft.json`
- `stages/06_material_bridge_mapping_draft.json`

stage report 显示：

- `pipeline_complete=true`
- `blocked=false`
- `status_counts={'success': 6}`

## 9. 新增测试

新增或扩展测试覆盖：

1. `test_material_protocol_split_pipeline_mock_generates_stage_artifacts`
   - 验证 mock 生成所有 stage artifacts。
2. `test_material_protocol_split_pipeline_dry_run_only_writes_evidence_map`
   - 验证 dry-run 只写 evidence map，不生成后续 draft。
3. `test_material_protocol_split_checker_rejects_empty_stage_contracts`
   - 验证 checker 拒绝空 stage contract。
4. `test_split_runtime_keeps_completed_stages_when_provider_fails`
   - 验证第 N 个 stage provider error 时，前 N-1 个 stage 仍保留。
5. `test_split_runtime_resume_skips_successful_stages`
   - 验证 resume 会跳过已成功 stage。
6. `test_split_runtime_validation_error_and_report_statuses`
   - 验证 validation_error 和 stage report 状态。

## 10. 测试结果

已运行：

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：

- 76 tests passed

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

## 11. 后续调试最推荐先看哪个 stage

后续蒸馏调试最推荐先看：

```text
02_material_semantic_requirements_draft.json
```

原因：

- 它是从 evidence map 到 material_card_draft 的语义中间层；
- 如果这个 stage 偏了，后面的 material_card、prompt assets、quality regression 都会跟着偏；
- 它最能暴露“材料需求理解”是否成立；
- 它还没有进入正式 material_card 字段，因此修正成本最低。

其次看：

```text
03_material_card_draft.json
```

因为它检验语义需求是否被正确落成材料卡草案。

## 12. 本轮明确未做事项

本轮没有：

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


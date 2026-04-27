# material_protocol_split_pipeline v1 执行报告

日期：2026-04-27

## 1. 本轮目标

本轮把上一版“一口气生成完整材料协议 bundle”的方式拆成分工位材料协议草案流水线。

目标不是写正式材料卡，也不是入库，而是让不同环节按自己的输入、schema、checker 生成初版草案：

```text
material_evidence_map
-> material_semantic_requirements_draft
-> material_card_draft
-> material_line_prompt_assets_draft
-> material_quality_regression_draft
-> material_bridge_mapping_draft
-> material_protocol_split_pipeline_report
```

## 2. 修改文件

新增：

- `tools/leaf_pre_distill/material_protocol_split_pipeline.py`

修改：

- `tests/test_leaf_pre_distill.py`

新增报告：

- `docs/material_protocol_split_pipeline_execution_report_2026-04-27.md`

## 3. 新增 CLI

新增命令：

```powershell
python -m tools.leaf_pre_distill.material_protocol_split_pipeline
```

支持参数：

- `--artifact-dir`
- `--output-dir`
- `--mode dry-run|mock|llm`
- `--model`
- `--base-url`
- `--api-key-env`
- `--max-input-chars`
- `--max-output-tokens`
- `--timeout-seconds`
- `--gold-reconstruction-results`
- `--truth-gold-regression-results`
- `--truth-gold-split-manifest`
- `--source-discovery-queries`
- `--material-source-profile`
- `--source-candidate-summary`
- `--source-candidate-review`
- `--source-seed-registry`
- `--crawl-seed-manifest`
- `--initial-plan-doc`

默认模式为 `dry-run`。

## 4. 分工位设计

### 4.1 material_evidence_map

机械生成。

用途：

- 汇总 family context；
- 汇总 evidence paths；
- 汇总 evidence gaps；
- 汇总 gold/source/review/seed/system alignment claims；
- 明确 blocked claims：
  - 未验证原文；
  - 未抓正文；
  - 未完成 source/gold alignment；
  - 未允许 material_card formalization。

### 4.2 material_semantic_requirements_draft

材料语义需求工位。

用途：

- 基于 evidence map 总结当前题包的材料需求假设；
- 标记 source_body_required；
- 标记 source_gold_alignment_required；
- 保持 hypothesis_only。

### 4.3 material_card_draft

材料卡草案工位。

用途：

- 只把已整理的 evidence 和 semantic requirements 落入 material_card 草案；
- 不负责发明原文处理规则；
- 不写正式 material card。

关键要求：

- `evidence_refs` 必须非空；
- `family_binding` 必须和 digest 中 family_context 完全一致；
- `source_body_required=true`；
- `source_gold_alignment_required=true`。

### 4.4 material_line_prompt_assets_draft

提示词资产草案工位。

必须包含五类 prompt：

- `source_evidence_review`
- `source_gold_alignment`
- `material_transformation_hypothesis`
- `material_quality_review`
- `material_card_draft`

### 4.5 material_quality_regression_draft

质量回归草案工位。

必须包含 `dimensions` 数组，每个 dimension 至少包含：

- `dimension`
- `method`
- `confidence`
- `limitation`

### 4.6 material_bridge_mapping_draft

系统桥接映射草案工位。

必须：

- 引用 `system_alignment_findings.json`；
- 使用仓库确认的 `MaterialV2SearchRequest` 字段；
- 不调用 `/materials/v2/search`；
- 不修改 `question_runtime.yaml`。

## 5. 样本输出

使用完整 evidence 路径跑了 mock 样本。

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_split_pipeline_mock_sample`

样本文件：

- `material_evidence_map.json`
- `material_semantic_requirements_draft.json`
- `material_card_draft.json`
- `material_line_prompt_assets_draft.json`
- `material_quality_regression_draft.json`
- `material_bridge_mapping_draft.json`
- `material_protocol_split_pipeline_report.md`

样本摘要：

- evidence gaps = 0；
- `material_card_draft.evidence_refs` 已包含：
  - `manifest`
  - `gold_reconstruction_results`
  - `truth_gold_regression_results`
  - `truth_gold_split_manifest`
  - `source_discovery_queries`
  - `material_source_profile`
  - `source_candidate_summary`
  - `source_candidate_review`
  - `source_seed_registry`
  - `crawl_seed_manifest`
  - `initial_plan_doc`
- prompt assets 包含五类 prompt；
- quality regression 包含 11 个维度；
- bridge mapping 使用 `MaterialV2SearchRequest` 确认字段。

## 6. LLM 样本尝试

尝试用完整 evidence 跑 LLM 分工位样本。

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_split_pipeline_llm_sample`

结果：

- 生成 `material_evidence_map.json`；
- 后续工位未生成；
- 原因：兼容端在 `material_line_prompt_assets_draft` 工位返回 HTTP 502。

等待后重试一次。

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_split_pipeline_llm_sample_retry`

结果：

- 生成 `material_evidence_map.json`；
- 后续工位未生成；
- 原因：兼容端在 `material_quality_regression_draft` 工位返回 HTTP 502。

判断：

- 分工位 prompt/schema 不再是一口气大 bundle；
- 这次失败主要是兼容端 origin 502，不是 checker 结构拒绝；
- 本轮没有继续循环重试，避免把 smoke 变成批量压测。

## 7. 新增 checker

新增 `validate_split_stages`。

会拒绝：

- 缺少任一工位；
- 任一产物不是 `draft_only`；
- 任一产物 `formalized=true`；
- 任一产物 `writeback_allowed=true`；
- 出现 `verified=true`；
- 出现 `verified_original_source=true`；
- 出现 `crawl_allowed=true`；
- 出现 `material_library_write=true`；
- 出现 `card_specs_write=true`；
- `material_card_draft.evidence_refs` 为空；
- `material_card_draft.family_binding` 与 digest family_context 不一致；
- prompt assets 缺少五类 prompt；
- quality regression 缺少 dimensions；
- bridge mapping 缺少 `system_alignment_findings_ref`；
- bridge mapping 缺少 confirmed repository fields。

## 8. 测试结果

已运行：

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：

- 73 tests passed

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

## 9. 当前判断

这刀已经把材料协议草案从“一口气 bundle”拆成了可控分工位。

mock 样本完整可用，可作为前端/人审/后续 prompt hardening 的结构样本。

LLM 样本当前被兼容端 502 阻断，未产生完整 LLM stage artifacts。由于失败来自 provider origin，本轮没有继续扩大调用。

## 10. 下一步建议

下一刀建议不是改主链，而是做 LLM 分工位执行的韧性增强：

1. stage checkpoint：每个成功工位先落盘，不因后续工位 502 丢失前面结果；
2. stage-level retry：只允许单工位最多 1 次 retry，并记录 retry_after；
3. stage report：每个工位单独记录 success / blocked / validation_errors；
4. 继续禁止写正式 material_card / card_specs / runtime / prompt / validator。

这样即使 provider 中途抖动，也能保留已经合格的工位样本。

## 11. 本轮明确未做事项

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


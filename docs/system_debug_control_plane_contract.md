# System Debug Control Plane Contract

日期：2026-04-27

## 1. 目标

`system_debug_control_plane` 是当前仓库的最小系统级调试总控台。

它的职责是：

- 登记已有调试子链；
- 只读扫描已有 artifact；
- 汇总每条链的状态、成熟度和能力特征；
- 记录跨链依赖关系；
- 生成系统级总调试报告。

它不是：

- 自动主执行器；
- multi-agent 平台；
- LLM 调度器；
- 生题执行器；
- 蒸馏执行器；
- crawler；
- material/card/prompt/validator 写回器。

## 2. 强边界

本控制层必须保持只读优先：

- 不自动调用 LLM；
- 不自动执行生题；
- 不自动执行 distill run；
- 不自动执行 source search / crawl / body fetch；
- 不确认原文；
- 不写 material_card；
- 不写 card_specs；
- 不写 runtime mapping；
- 不写 prompt assets；
- 不写 validator；
- 不新增 promotion target；
- 不把人工串联夸大成自动 orchestration。

## 3. 四层概念

### 3.1 Registry

文件：`tools/system_debug_registry.py`

职责：

- 定义系统已知的调试子链；
- 记录每条链的 category、maturity_level、能力特征、输入输出 artifact、依赖关系和阻断点；
- 提供自动发现 artifact 的文件名模式。

每条链必须包含：

- `chain_name`
- `category`
- `maturity_level`
- `has_contract`
- `has_checkpoint`
- `has_retry`
- `has_resume`
- `has_state_file`
- `has_stage_report`
- `has_diff_or_backtest`
- `has_patch_or_bundle`
- `has_human_review_gate`
- `input_artifacts`
- `output_artifacts`
- `dependency_on`
- `blocked_by`
- `notes`

### 3.2 Manifest

文件：`tools/system_debug_manifest.py`

输出：

- `system_debug_run_manifest.json`

职责：

- 创建一次系统级 debug run 的登记；
- 记录 run id、artifact root、纳入的 chains、依赖边；
- 明确 `read_only=true`、`auto_execute=false`、`llm_calls_allowed=false`、`writeback_allowed=false`。

### 3.3 Artifact Index

文件：`tools/system_debug_artifact_index.py`

输出：

- `system_debug_artifact_index.json`

职责：

- 只读扫描 artifact root；
- 根据 registry artifact patterns 归属 artifact；
- 记录 path、relative_path、filename、size、modified_at、matched_chains、artifact_role、status_hint；
- 不解析大正文，不执行业务逻辑。

### 3.4 Report

文件：`tools/system_debug_report.py`

输出：

- `system_debug_report.json`
- `system_debug_report.md`

职责：

- 汇总每条链的当前状态；
- 展示 checkpoint/retry/resume/diff/human gate 等能力矩阵；
- 展示跨链依赖；
- 标记 blocked points；
- 标记 missing adapter / contract；
- 给出最多 3 条下一步最小补刀建议。

## 4. 当前纳入的链

最小版本纳入以下链：

| chain_name | category | 说明 |
|---|---|---|
| `source_discovery_review` | `material_line` | source discovery、candidate search、human review、seed registry |
| `material_protocol_split_pipeline` | `material_line` | 6 工位材料协议草案流水线 |
| `material_cleaning_slicing_chain` | `material_line` | 清洗、切片、选段链；当前登记为 Level 0 缺口，不表示已实现 |
| `question_protocol_patch_chain` | `question_protocol_line` | axis confirmation、formal patch draft、writeback plan/executor |
| `question_generation_runtime` | `generation_line` | 生题主链、validator、review/action、runtime observer |
| `difficulty_control_chain` | `difficulty_line` | projection、assessment、diff、calibration、backtest artifact |
| `distillation_runtime_workbench` | `distillation_line` | distillation runtime、workbench、diff、promotion bundle |
| `truth_gold_regression` | `distillation_line` | gold split、regression、generated comparison |

## 5. 链状态判断

最小版状态判断只基于已发现 artifact：

- `registered_only`：registry 中存在，但 artifact root 下没有发现匹配 artifact；
- `available`：发现一个或多个 artifact；
- `complete`：发现明确 `pipeline_complete=true` 的 artifact；
- `blocked`：发现 artifact 中存在 `blocked=true`、`status=failed/blocked/provider_error/validation_error`，或 stage status 里存在错误。

该状态只是总控台观察结果，不代表业务语义通过或失败。

## 6. 独立链与依赖链

控制台必须允许：

- 独立链；
- 半独立链；
- 可选依赖链；
- 强依赖链。

当前最小版只登记依赖图，不自动根据依赖执行或阻断任何链。

## 7. CLI

示例：

```powershell
python -m tools.system_debug_control_plane `
  --artifact-root E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425 `
  --output-dir E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/system_debug_control_plane
```

可选参数：

- `--system-debug-run-id`
- `--chains`
- `--artifact`
- `--max-files`

## 8. 输出

必须输出：

- `system_debug_run_manifest.json`
- `system_debug_artifact_index.json`
- `system_debug_report.json`
- `system_debug_report.md`

## 9. 后续扩展边界

后续可以继续做：

- 更细的 artifact adapter registry；
- 统一 correlation id；
- blocked chain drilldown；
- 只读 report UI。

后续仍不得直接做：

- 自动写回正式配置；
- 自动执行跨链主流程；
- 自动把 draft/promoted/evidence 混为正式状态。

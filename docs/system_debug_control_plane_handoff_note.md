# System Debug Control Plane Handoff Note

日期：2026-04-27

## 1. 本轮交付

本轮新增最小版系统级调试总控台。

它只做：

- chain registry；
- system debug run manifest；
- read-only artifact index；
- system debug report；
- dependency edge 登记；
- blocked / registered-only / available / complete 状态汇总。

它不做：

- LLM 调用；
- 生题；
- distill run；
- source search；
- crawler；
- source verification；
- material_card 写回；
- card_specs 写回；
- runtime / prompt / validator / generation 主链修改。

## 2. 新增文件

代码：

- `tools/system_debug_registry.py`
- `tools/system_debug_manifest.py`
- `tools/system_debug_artifact_index.py`
- `tools/system_debug_report.py`
- `tools/system_debug_control_plane.py`

文档：

- `docs/system_debug_control_plane_contract.md`
- `docs/system_debug_control_plane_handoff_note.md`

## 3. 推荐运行方式

```powershell
python -m tools.system_debug_control_plane `
  --artifact-root E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425 `
  --output-dir E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/system_debug_control_plane
```

输出：

- `system_debug_run_manifest.json`
- `system_debug_artifact_index.json`
- `system_debug_report.json`
- `system_debug_report.md`

## 4. 当前接入深度

### 深接入

`material_protocol_split_pipeline`

- 有 stage sequence；
- 有 checkpoint；
- 有 retry；
- 有 resume；
- 有 `pipeline_state.json`；
- 有 stage report。

### 中等接入

`distillation_runtime_workbench`

- 有 dataset/session/run/review/patch/promote；
- 有 promotion bundle；
- 有 human review gate；
- 但没有通用 checkpoint/retry/resume。

`question_protocol_patch_chain`

- 有 draft/plan/diff/executor artifact；
- 有 approval 和 regression 边界；
- 但各环节仍主要通过离线 artifact 人工串联。

`source_discovery_review`

- 有 source candidate、human review、seed registry；
- seed 仍是 seed_only；
- 不确认原文，不抓正文。

### 仅登记缺口

`material_cleaning_slicing_chain`

- 用来覆盖材料线中的清洗、切片、选段位置；
- 当前没有正式 runtime、contract、state 或 report；
- 登记为 `Level 0`，用于总控台暴露“正文抓取/对齐之前不能进入清洗选段”的缺口。

### 登记为主

`question_generation_runtime`

- 仓库中有强业务 orchestrator；
- 但当前总控台只通过 artifact pattern 观察，不直接接入 repository/runtime event DB。

`difficulty_control_chain`

- 有 projection/assessment/diff/calibration 服务；
- 但缺统一 durable backtest artifact runner。

## 5. 当前限制

1. artifact 发现基于文件名 pattern，尚未有中心化 artifact registry。
2. DB 中的 distill run/runtime event 没有直接读取。
3. 不会自动判断跨链依赖是否满足，只登记依赖边。
4. 不会读取业务配置来确认某个 draft 是否已经正式写回。
5. 不会把人工路径传递变成自动 orchestration。

## 6. 下一刀建议

最建议补：

`artifact adapter registry`

目的：

- 明确每个 output artifact 能作为哪些链的 input；
- 记录必需字段；
- 记录缺失字段时的降级策略；
- 让总控台从“发现文件”升级到“知道文件能接到哪里”。

仍然建议保持只读，不要直接执行跨链调度。

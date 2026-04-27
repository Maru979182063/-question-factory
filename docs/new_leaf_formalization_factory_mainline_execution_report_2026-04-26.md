# 新题包正式化工厂 4+1 刀主线执行报告

执行日期：2026-04-27

## 结论

本轮 5 刀均已完成，系统从“蒸馏实验台”推进到“新题包正式化送审工厂”的最小闭环：

题包证据、人工反馈、题卡草案、材料草案、runtime 接入计划、回归要求，可以被合成正式化送审包，并由 readiness gate 判断下一步是否可进入写回计划。

当前结果不是自动正式写回。readiness gate 在 mock 小闭环中返回 `blocked`，原因是 runtime mapping、question_card binding、显式 approval、writeback plan 等正式落位条件仍未满足。这是预期行为。

## 修改文件

- `tools/leaf_pre_distill/agent_review_feedback.py`
- `tools/leaf_pre_distill/agent_review_feedback_prompt.py`
- `tools/leaf_pre_distill/new_leaf_formalization_packet.py`
- `tools/leaf_pre_distill/runtime_activation_plan.py`
- `tools/leaf_pre_distill/formalization_readiness_gate.py`
- `tools/leaf_pre_distill/report_renderer.py`
- `docs/leaf_pre_distill_artifact_contract.md`
- `prompt_skeleton_service/app/demo_static/distill_demo.html`
- `prompt_skeleton_service/app/demo_static/distill_demo.js`
- `tests/test_leaf_pre_distill.py`
- `prompt_skeleton_service/tests/test_demo_shell.py`
- `docs/new_leaf_formalization_factory_mainline_execution_report_2026-04-26.md`

## 新增 Artifacts

第 1 刀：

- `agent_review_feedback_input.json`
- `agent_review_feedback_normalized.json`
- `agent_review_feedback_report.md`

第 2 刀：

- `new_leaf_formalization_packet.json`
- `new_leaf_formalization_packet_report.md`

第 3 刀：

- `runtime_activation_plan.json`
- `runtime_activation_plan_report.md`

第 4 刀：

- `formalization_readiness_checklist.json`
- `formalization_readiness_report.md`

第 5 刀：

- 前端生成 `agent_review_feedback_input.json`，不新增后端 artifact 类型。

## 输出目录

本轮生成 mock 小闭环输出：

`data/leaf_pre_distill/new_leaf_formalization_factory_mock_20260427`

包含：

- `agent_review_feedback_input.json`
- `agent_review_feedback_normalized.json`
- `agent_review_feedback_report.md`
- `new_leaf_formalization_packet.json`
- `new_leaf_formalization_packet_report.md`
- `runtime_activation_plan.json`
- `runtime_activation_plan_report.md`
- `formalization_readiness_checklist.json`
- `formalization_readiness_report.md`

## 五刀状态

| 刀 | 状态 | 说明 |
|---|---|---|
| agent_review_feedback_normalization v1 | pass | mock 模式可把“太简单了，材料太短，干扰项不够迷惑”归一化为 `difficulty_too_low`、`material_too_short`、`distractor_weakness`。 |
| new_leaf_formalization_packet v1 | pass | 可合并 axis、patch draft、material draft、source seed、truth gold、agent feedback 等证据。 |
| runtime_activation_plan v1 | pass | 可只读生成 runtime 接入计划，并明确缺失 binding / mapping。 |
| formalization_readiness_gate v1 | pass | 可统一判断 blocked / review_needed / proto_ready 等状态；mock 小闭环为 `blocked`。 |
| agent_feedback_ui v1 | pass | distill demo 新增用户反馈输入区，只生成 JSON，不调用 LLM，不写回。 |

## 核心结果

### Agent Feedback

- 支持 `dry-run`、`mock`、`llm` 三种模式。
- 机械层只做 schema、边界、字段校验。
- 输出始终保持 `writeback_allowed=false`、`formalized=false`。
- 用户自然语言反馈不会直接改题卡、材料卡、prompt、validator 或 runtime。

### Formalization Packet

- 当前 packet 类型：`new_leaf_formalization_packet`
- 状态：`draft_review_packet`
- 可收集：
  - axis confirmation
  - formal patch draft
  - material protocol draft
  - source review / seed registry
  - truth-gold regression
  - agent review feedback
- 不会把 `source_seed_registry` 当作 verified source。
- 不会把 `material_card_draft` 当正式 material_card。

### Runtime Activation Plan

- 状态：`draft_only`
- 当前只读检查：
  - business_subtype mapping
  - question_card binding
  - business_feature_card binding
  - prompt_assets binding
  - validator_contract binding
  - material_bridge_mapping
  - runtime_mapping
- mock 小闭环中 `can_run_formal_generation=false`。
- 计划不修改 `question_runtime.yaml`、generation、validator、prompt 或 runtime 主链。

### Readiness Gate

mock 小闭环结果：`blocked`

主要阻塞：

- `question_card_binding_missing`
- `runtime_mapping_missing`
- `formal_generation_requires_writeback_plan_and_regression`
- `explicit_approval_available`

这说明 gate 没有把草案误判为可正式写回。

### UI

`distill_demo` 新增区块：

- `5D. 用户反馈证据`

用户可填写：

- reviewer
- target_scope
- target_artifacts
- raw_feedback

输出：

- `agent_review_feedback_input.json`

边界文案已写明：

- 用户反馈是 evidence
- 不直接写回
- 不直接改题卡 / 材料卡 / prompt / validator / runtime

## 测试结果

已运行：

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：`Ran 82 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

结果：`Ran 11 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

结果：`Ran 10 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

结果：`Ran 4 tests ... OK`

## 明确未做

- 没有正式写回。
- 没有写 `card_specs`。
- 没有 formalize `material_card`。
- 没有写 runtime mapping。
- 没有写 prompt assets。
- 没有写 validator。
- 没有修改 generation 主链。
- 没有 passage_service ingest。
- 没有 material promotion。
- 没有新增正式 promotion target。

## 下一步

最合理的下一刀不是 executor，而是把 `new_leaf_formalization_packet` 和 `formalization_readiness_gate` 接入 system debug control plane / adapter registry，使总控台能看到“新题包正式化送审包”的状态、阻塞点、下游 writeback plan 入口。

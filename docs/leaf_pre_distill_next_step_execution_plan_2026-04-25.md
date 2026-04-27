# 叶族预蒸馏下一步执行计划

日期：2026-04-25

## 目标

把离线 `leaf_pre_distill` 产物接入现有蒸馏台的 review / patch / promotion 链。

本轮目标不是做完整 API，也不是自动写回题卡，而是完成：

```text
leaf_pre_distill artifact
-> distill patch target
-> review allow_promote
-> promotion bundle
```

使预蒸馏报告可以被正式审计、批准、打包。

## 总体策略

采用最小侵入式路线：

1. 不改数据库表。
2. 不改正式题卡配置。
3. 不自动写回 card_specs。
4. 只扩展 patch / promotion target 和前端选项。
5. 通过 alias normalize 保证旧数据兼容。

## 阶段 1：正式化 artifact contract

新增文档：

```text
docs/leaf_pre_distill_artifact_contract.md
```

内容包括：

- `manifest.json`
- `samples.jsonl`
- `behavior_traces.jsonl`
- `field_candidates.json`
- `slot_projection_draft.yaml`
- `report.md`

每个 artifact 说明：

- 文件用途；
- 必填字段；
- 是否可作为 promotion patch 证据；
- 是否允许进入正式配置；
- 人审时要看什么。

完成标准：

- 文档明确 `leaf_pre_distill_report` 是证据，不是配置；
- 文档明确 `schema_gap_report` 是缺口，不是 schema 已变更；
- 文档明确 `slot_projection_draft` 是落位草案，不是正式题卡。

## 阶段 2：统一 target 名称

### 2.1 新增 canonical targets

在 `prompt_skeleton_service/app/schemas/distill.py` 中扩展：

```python
DistillPromotionTarget = Literal[
    "question_card",
    "business_feature_card",
    "material_card",
    "signal_layer",
    "runtime_mapping",
    "prompt_assets",
    "validator_contract",
    "material_mapping",
    "leaf_pre_distill_report",
    "schema_gap_report",
]
```

### 2.2 支持 legacy alias

输入接受：

```text
prompt_config -> prompt_assets
material_strategy -> material_mapping
```

建议实现一个小函数：

```python
def normalize_distill_target(value: str) -> DistillPromotionTarget:
    aliases = {
        "prompt_config": "prompt_assets",
        "material_strategy": "material_mapping",
    }
    return aliases.get(value, value)
```

三个入口都使用它：

- `DistillRunReviewRequest.promotion_targets`
- `DistillRunPatchRequest.target`
- `DistillPromotionRequest.targets`

完成标准：

- 用户传旧名不报错；
- 内部保存和 response 尽量输出 canonical target；
- promotion 判断不会因为 alias 不一致而失败。

## 阶段 3：扩展前端 target 选项

修改：

```text
prompt_skeleton_service/app/demo_static/distill_demo.html
```

三处都要补：

1. review promotion targets checkbox；
2. patch target select；
3. promote targets checkbox。

建议展示分组：

```text
配置落位：
question_card
business_feature_card
material_card
signal_layer
runtime_mapping

证据与契约：
leaf_pre_distill_report
schema_gap_report
prompt_assets
validator_contract
material_mapping
```

短期可以不做复杂 UI 分组，只补 option/checkbox。

完成标准：

- UI 能选择 `leaf_pre_distill_report`；
- UI 能选择 `schema_gap_report`；
- UI 能选择 `validator_contract`；
- 旧 target 不再作为首选展示，但后端仍接受。

## 阶段 4：扩展 promotion 测试

修改：

```text
prompt_skeleton_service/tests/test_distill_workbench.py
```

新增测试：

### 4.1 legacy alias normalize

输入：

```python
promotion_targets=["question_card", "prompt_config"]
```

期望：

```python
promotion_targets=["question_card", "prompt_assets"]
```

或至少 promotion 可以用 `prompt_assets` patch 成功。

### 4.2 leaf report promotion

流程：

1. 创建 completed run；
2. review 允许 `leaf_pre_distill_report` 和 `schema_gap_report`；
3. 添加两个 patch；
4. promote；
5. 检查 promotion bundle 存在并包含两个 target。

### 4.3 missing patch guard 仍有效

允许 `schema_gap_report`，但只添加 `leaf_pre_distill_report` patch，promotion 应失败。

完成标准：

```powershell
python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

相关测试通过。

## 阶段 5：接入离线 artifact 的使用姿势

不新增 API，只规定 patch payload 格式：

```json
{
  "artifact_type": "leaf_pre_distill_report",
  "artifact_path": "data/leaf_pre_distill/smoke_sentence_order_timeline_20260425/report.md",
  "field_candidates_path": "data/leaf_pre_distill/smoke_sentence_order_timeline_20260425/field_candidates.json",
  "slot_projection_draft_path": "data/leaf_pre_distill/smoke_sentence_order_timeline_20260425/slot_projection_draft.yaml",
  "summary": {
    "leaf_label": "日常逻辑-时间脉络",
    "sample_count": 50,
    "high_confidence_fields": [
      "ordering_logic=timeline_progression"
    ]
  }
}
```

完成标准：

- patch 可以挂 artifact path；
- promotion bundle 可以保留 artifact path；
- 不要求后端读取 artifact 内容。

## 阶段 6：冒烟测试

用已经生成的本地 artifact 做一次完整人审链路模拟：

1. 创建 distill dataset / session / run，或使用 stub generation runner 测试；
2. review 允许：

```text
leaf_pre_distill_report
schema_gap_report
material_card
```

3. 添加 patch：

```text
leaf_pre_distill_report
schema_gap_report
material_card
```

4. promote；
5. 检查 bundle。

期望 bundle 包含：

- `leaf_pre_distill_report`
- `schema_gap_report`
- `material_card`
- artifact path；
- summary；
- patch ids。

## 不做什么

本轮明确不做：

- `POST /api/v1/distill/leaf-preprocess/jobs`
- 文件上传；
- artifact registry 数据表；
- 自动读取 `data/leaf_pre_distill`；
- 自动写回 card_specs；
- 前端报告预览器；
- LLM 自动裁判。

这些留到下一轮。

## 回滚策略

因为不改数据库、不改题卡主配置，回滚很简单：

1. 回退 schema target 扩展；
2. 回退前端选项；
3. 删除新增测试；
4. 已生成的 promotion bundle 如果包含新 target，也只是 JSON artifact，不影响旧运行链。

## 预计改动文件

```text
docs/leaf_pre_distill_artifact_contract.md
prompt_skeleton_service/app/schemas/distill.py
prompt_skeleton_service/app/demo_static/distill_demo.html
prompt_skeleton_service/tests/test_distill_workbench.py
```

可能微调：

```text
prompt_skeleton_service/app/services/question_repository.py
prompt_skeleton_service/app/schemas/distillation.py
```

其中 `question_repository.py` 只在需要更改默认 target 时动，不是必须。

## 验收标准

### 功能验收

- 后端接受新 target；
- 旧 target alias 仍可用；
- review / patch / promote 三段 target 一致；
- promotion bundle 可包含 leaf pre-distill artifact。

### 测试验收

至少跑：

```powershell
python -m unittest prompt_skeleton_service.tests.test_distill_workbench
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

如果环境允许，再跑：

```powershell
python -m unittest discover -s prompt_skeleton_service/tests -p "test_distillation*.py"
```

### 文档验收

- artifact contract 文档存在；
- next-step report 中说明 legacy alias；
- 明确不自动写回正式配置。

## 执行顺序

推荐严格按以下顺序：

1. 写 artifact contract。
2. 在 `distill.py` 加 target normalize。
3. 更新 `test_distill_workbench.py`，先让后端测试通过。
4. 更新 `distill_demo.html` 的 target 选项。
5. 做完整冒烟。
6. 写执行报告。

## 最终判断

这一步值得做，而且是叶族预蒸馏从“离线工具”进入“正式蒸馏链”的关键一步。

它不会改变题卡规则本身，只会让预蒸馏产物能被系统正式记录和审核。只要 alias normalize 做好，风险主要是 UI 和测试同步，不是核心架构风险。

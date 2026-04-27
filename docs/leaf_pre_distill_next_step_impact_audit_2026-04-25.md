# 叶族预蒸馏下一步影响审计

日期：2026-04-25

## 下一步要做什么

下一步不是继续增强离线算法，而是把离线产物接入现有蒸馏台的 review / patch / promotion 链。

目标是让以下产物成为正式可审计对象：

- `leaf_pre_distill_report`
- `schema_gap_report`
- `slot_projection_draft`

并允许它们在蒸馏台里被：

- review 批准；
- patch 显式记录；
- promotion bundle 打包；
- 后续人工写回题卡 / 业务卡 / 材料卡 / validator contract。

## 影响范围总览

| 层级 | 影响 | 风险 |
|---|---|---|
| schema | 扩展 promotion / patch target 枚举 | 中 |
| service | promotion 校验可接受新 target | 中低 |
| repository | 基本无迁移，字段是 TEXT/JSON | 低 |
| frontend | 蒸馏页 checkbox / select 需要新增选项 | 中低 |
| tests | 现有 prompt_config / material_strategy 测试要兼容 | 中 |
| docs | 需要正式 artifact contract | 低 |

## 当前状态

### 1. `distill.py` 的 target 太窄

当前位置：

```text
prompt_skeleton_service/app/schemas/distill.py
```

当前定义：

```python
DistillPromotionTarget = Literal["question_card", "prompt_config", "material_strategy"]
```

这个枚举被用于：

- `DistillRunReviewRequest.promotion_targets`
- `DistillRunPatchRequest.target`
- `DistillPromotionRequest.targets`
- response summary 中的 targets

问题：它无法表达叶族预蒸馏的真实落位目标，例如：

- `leaf_pre_distill_report`
- `schema_gap_report`
- `business_feature_card`
- `material_card`
- `runtime_mapping`
- `validator_contract`

### 2. `distillation.py` 已经有另一套 target

当前位置：

```text
prompt_skeleton_service/app/schemas/distillation.py
```

当前定义：

```python
PatchTarget = Literal["question_card", "prompt_assets", "validator_contract", "material_mapping"]
```

这和 `distill.py` 不一致：

| distill.py | distillation.py | 含义 |
|---|---|---|
| `prompt_config` | `prompt_assets` | 提示词资产 |
| `material_strategy` | `material_mapping` | 材料策略/映射 |
| 无 | `validator_contract` | 校验契约 |

风险：如果继续扩展两套枚举，会让 promotion 目标越分越乱。

### 3. repository 不需要数据库迁移

`question_repository.py` 中：

```sql
distill_run_patches.target TEXT NOT NULL
distill_promotions.payload_json TEXT NOT NULL
```

promotion targets 实际保存在 payload JSON 里，patch target 同时落 TEXT 和 JSON。

结论：新增 target 不需要改表，不需要迁移旧数据库。

注意点：`save_distill_run_patch()` 默认值是：

```python
str(payload.get("target") or "prompt_config")
```

如果未来把 `prompt_config` 视作 legacy alias，这个默认值应改成新的 canonical target，例如 `prompt_assets`，或者保留但统一 normalize。

### 4. 前端蒸馏页写死了 target 选项

当前位置：

```text
prompt_skeleton_service/app/demo_static/distill_demo.html
```

当前写死：

```html
question_card
prompt_config
material_strategy
```

出现位置：

- review promotion targets checkbox
- patch target select
- promote targets checkbox

如果后端先扩展，而前端不扩展，用户仍然无法在 UI 里选 `leaf_pre_distill_report` 或 `schema_gap_report`。

### 5. 现有测试会受影响

当前位置：

```text
prompt_skeleton_service/tests/test_distill_workbench.py
```

现有测试显式使用：

- `prompt_config`
- `question_card`

如果直接改 canonical 名称，会破坏旧测试。

推荐策略：先兼容旧名，再逐步迁移。

### 6. promotion 机制本身是正确的

`DistillWorkbenchService.promote_run()` 已经有好机制：

- 必须先有 approved review；
- review 必须 allow_promote；
- promotion target 必须在 review 允许列表里；
- 每个 promotion target 必须有对应 patch；
- promotion 会打 bundle。

这些都不需要重写。我们只需要扩展 target 类型和 alias normalize。

## 推荐新增 target

建议 canonical target：

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

Legacy alias：

| 旧名 | 新名 |
|---|---|
| `prompt_config` | `prompt_assets` |
| `material_strategy` | `material_mapping` |

是否立刻替换旧名，有两种方案。

### 方案 A：保留旧名作为合法 target

优点：

- 最稳；
- 测试改动少；
- 前端不用一次性迁移。

缺点：

- target 名称继续不统一；
- 后续报告里会同时出现旧名和新名。

### 方案 B：输入接受旧名，内部统一成新名

优点：

- 系统内部干净；
- 后续所有 bundle 都用 canonical target；
- 为正式化打好基础。

缺点：

- 需要在 Pydantic model validator 或 service 里 normalize；
- 现有测试需要调整期望值。

推荐：方案 B。

## 可能影响到的文件

### 后端 schema

```text
prompt_skeleton_service/app/schemas/distill.py
prompt_skeleton_service/app/schemas/distillation.py
```

影响：

- 扩展 target literal；
- 增加 legacy alias normalize；
- 保证 response 里输出 canonical target。

### 后端 service

```text
prompt_skeleton_service/app/services/distill_workbench.py
```

影响：

- patch / review / promote 流程大体不变；
- 可能需要在保存前 normalize targets；
- promotion bundle 输出 canonical target。

### repository

```text
prompt_skeleton_service/app/services/question_repository.py
```

影响：

- 不需要表迁移；
- 建议把 default target 从 `prompt_config` 调整为 canonical target，或确保上层永远传入 target。

### 前端

```text
prompt_skeleton_service/app/demo_static/distill_demo.html
prompt_skeleton_service/app/demo_static/distill_demo.js
```

影响：

- 新增 target checkbox；
- patch target select 新增选项；
- promote target checkbox 新增选项；
- JS 主要是收集 checkbox value，不需要大改。

### 测试

```text
prompt_skeleton_service/tests/test_distill_workbench.py
```

影响：

- 新增 leaf report / schema gap promotion 测试；
- 旧 `prompt_config` 测试要么保留 alias 输入，要么改为 `prompt_assets` 期望。

可能还要检查：

```text
prompt_skeleton_service/tests/test_distillation_promotion_service.py
prompt_skeleton_service/tests/test_distillation_diff_service.py
```

这些是另一个 `distillation.py` 协议的测试，目标是让两套 target 口径靠近，而不是互相打架。

## 风险清单

### P1. alias 处理不一致

如果 review 阶段保存 `prompt_config`，patch 阶段保存 `prompt_assets`，promotion 会判断缺少 patch。

必须保证三个入口共用同一套 normalize：

- review promotion_targets；
- patch target；
- promotion targets。

### P1. 前端仍发送旧 target

短期不可避免。后端必须接受旧 target。

### P1. promotion bundle 历史兼容

旧 bundle 里可能已有：

- `prompt_config`
- `material_strategy`

读取旧数据时不能报错。可以在 model validate 时接受旧值并输出 canonical，或者保留旧值为 legacy display。

### P2. target 扩展后被误认为“自动写回”

新增 `business_feature_card`、`material_card` 等 target，不代表系统自动修改这些文件。

文档和 UI 必须强调：

```text
promotion bundle 是候选沉淀包，不是自动写回主配置。
```

### P2. leaf report 和 schema gap 与 patch 混淆

`leaf_pre_distill_report` 是证据产物，不是配置变更。

`schema_gap_report` 是缺口说明，不是 schema 已变更。

patch payload 里要明确：

```json
{
  "artifact_path": "...",
  "artifact_type": "leaf_pre_distill_report",
  "recommended_targets": ["material_card", "schema_gap_report"]
}
```

### P2. 前端目标太多，UI 变乱

第一版不需要做复杂设计，只把目标分成两组：

- 配置落位：question_card / business_feature_card / material_card / runtime_mapping / signal_layer
- 证据与契约：leaf_pre_distill_report / schema_gap_report / validator_contract / prompt_assets / material_mapping

### P3. 离线 artifact 未进入 repository

短期可以只通过 patch payload 挂 artifact path，不需要建表。

风险是 artifact 路径移动会断。第一阶段可接受，后续再做 artifact registry。

## 审计结论

下一步可以做，影响面可控。

最应该小心的是 target 规范化，而不是数据库或 service 主流程。

推荐最小改动路线：

```text
统一 target 枚举
-> 加 alias normalize
-> 前端补 target 选项
-> 增加 promotion 测试
-> 写 artifact contract
```

暂时不要做：

- 数据库迁移；
- 自动写回 card_specs；
- 新增复杂 UI；
- API 上传文件；
- 把 leaf_pre_distill job 存成正式表。

# 叶族预蒸馏实验台加入计划

日期：2026-04-24

## 目标

把最近验证有效的“从干净叶族题包反推字段”的方法，纳入现有蒸馏实验台，形成稳定入口：

```text
新叶族题包
-> 题目抽取
-> 行为痕迹标注
-> 聚合统计
-> 候选字段蒸馏
-> 题卡/业务卡/材料卡/overlay/schema gap 投影
-> 进入现有 trial / review / patch / promotion 流程
```

该模块的核心产物不是正式题卡，而是候选报告。正式落位仍由现有人工审核与 promotion 机制控制。

## 设计原则

1. 预蒸馏不直接写主配置。
2. 预蒸馏产物必须可复现。
3. 每个候选字段必须绑定证据、支持率和落位建议。
4. schema 对不上的内容先进入 `schema_gap_report`，不能硬塞现有 slot。
5. 叶族字段优先，子族和母族只补充共享结构。
6. 所有最终落位都必须经过 review / patch / promotion。

## 新增模块名称

建议目录与服务名：

```text
leaf_pre_distill_lab
```

建议中文名：

```text
叶族预蒸馏实验台
```

## 产物契约

### 1. `leaf_pack_manifest`

描述一个新叶族题包的来源和边界。

```yaml
manifest_id: leaf_pack_20260424_xxx
mother_family_id: sentence_order
expected_child_family_id: sentence_order_sequence
leaf_label: 日常逻辑-时间脉络
source_files:
  - path: ...
    format: docx
clean_leaf_boundary: true
operator: ...
notes: []
```

### 2. `parsed_leaf_samples`

每道题的结构化结果。

```yaml
sample_id: ...
source_file: ...
qid: ...
stem: ...
passage_or_units: ...
options: {}
answer: ...
analysis: ...
exam_points: ...
correct_rate: ...
raw_text_hash: ...
parse_warnings: []
```

### 3. `behavior_trace`

把题目转成“可观测解题动作”。

```yaml
sample_id: ...
observed_actions:
  - action: detect_opening_anchor
    evidence: ["确定首句", "背景引入"]
  - action: detect_binding_pair
    evidence: ["关联词", "捆绑"]
  - action: detect_closure_position
    evidence: ["尾句", "结论"]
uniqueness_source:
  - reference_dependency
  - closure_position
distractor_modes:
  - wrong_opening
  - block_swap
confidence: medium
```

### 4. `leaf_field_candidate_report`

字段候选报告。

```yaml
leaf_label: 日常逻辑-时间脉络
sample_count: 50
field_candidates:
  - field_path: ordering_logic
    proposed_value: timeline_progression
    support_rate: 1.0
    confidence: high
    target_layer: business_feature_projection
    evidence_count: 281
    evidence_examples:
      - 时间顺序
      - 时间脉络
    ablation_question: 去掉该字段后，是否仍能稳定排除 block_swap 错项？
  - field_path: middle_structure_type
    proposed_value: local_binding
    support_rate: 0.98
    confidence: medium
    target_layer: canonical_slot
schema_gaps:
  - field: timeline_progression_as_middle_structure
    reason: current middle_structure_type allowed values do not include timeline_progression
    suggested_resolution: encode as ordering_logic or material_card_overlay
```

### 5. `slot_projection_draft`

面向题卡体系的落位草案。

```yaml
target_question_card_id: question.sentence_order.standard_v1
target_business_feature_card_id: sentence_order__timeline_action_sequence__abstract
canonical_slot_updates:
  middle_structure_type: local_binding
  local_binding_strength: medium_high
overlay_updates:
  ordering_logic: timeline_progression
  distractor_modes:
    - block_swap
    - local_adjacency_break
validator_contract_candidates:
  - require_time_or_action_progression_evidence
  - reject_topical_grouping_only
promotion_targets:
  - business_feature_card
  - material_card
  - validator_contract
```

## 接入现有蒸馏台

### 阶段 0：保留离线脚本，固定报告格式

先把这几轮手工实验沉淀成通用脚本：

```text
tools/leaf_pre_distill/
  parse_docx_pack.py
  extract_behavior_traces.py
  aggregate_field_candidates.py
  render_leaf_candidate_report.py
```

输入：

- docx / json / csv 题包；
- mother_family_id；
- leaf_label；
- 可选 child_family_id；
- 可选人工 seed markers。

输出：

- `leaf_pack_manifest.json`
- `parsed_leaf_samples.jsonl`
- `behavior_traces.jsonl`
- `leaf_field_candidate_report.md`
- `slot_projection_draft.yaml`

完成标准：

- 能复现已有三份实验报告的核心统计；
- 对中心理解、语句填空、语句排序都可跑；
- 不依赖具体文件名写死字段。

### 阶段 1：加入 distill artifact，但不改数据库

在现有 promotion bundle 旁边新增 artifact 目录：

```text
data/leaf_pre_distill/{job_id}/
```

并在 distill run patch 中允许引用：

```json
{
  "target": "leaf_pre_distill_report",
  "scope_key": "sentence_order.timeline_progression",
  "patch": {
    "artifact_path": "data/leaf_pre_distill/..."
  }
}
```

完成标准：

- 预蒸馏报告能作为现有 distill session 的 evidence；
- review 可以批准或驳回该报告；
- promotion bundle 能携带报告路径。

### 阶段 2：扩展 promotion target

统一 `distill.py` 与 `distillation.py` 的 target 口径。

建议新增：

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

兼容旧值：

```text
prompt_config -> prompt_assets
material_strategy -> material_mapping
```

完成标准：

- 老测试不破；
- 新 target 能被 review / patch / promotion 承载；
- promotion bundle 中每个 target 都必须有显式 patch。

### 阶段 3：新增 API

建议 API：

```text
POST /api/v1/distill/leaf-preprocess/jobs
GET  /api/v1/distill/leaf-preprocess/jobs/{job_id}
POST /api/v1/distill/leaf-preprocess/jobs/{job_id}/report
POST /api/v1/distill/leaf-preprocess/jobs/{job_id}/attach-to-session
```

第一阶段可以只支持服务器本地路径，后续再做文件上传。

请求示例：

```json
{
  "title": "语句排序-时间脉络预蒸馏",
  "mother_family_id": "sentence_order",
  "child_family_id": "sentence_order_sequence",
  "leaf_label": "日常逻辑-时间脉络",
  "source_files": [
    "C:/.../日常逻辑-时间脉络.docx"
  ],
  "clean_leaf_boundary": true,
  "operator": "human"
}
```

完成标准：

- API 能产生 artifact；
- 不直接写 card_specs；
- 可绑定到 distill session；
- 可在前端展示核心统计。

### 阶段 4：候选字段落位器

新增一个纯函数式服务：

```text
LeafSlotProjectionService
```

职责：

- 读取 question card / type config / material cards / runtime mapping；
- 判断候选字段应该落在哪层；
- 标出 schema gap；
- 生成 slot projection draft；
- 不写回配置。

落位规则：

| 候选类型 | 落位 |
|---|---|
| 已在母族 `slot_schema` 中 | `canonical_slot` |
| 对应某张业务特征卡 | `business_feature_projection` |
| 更像选材/结构原型 | `material_card_overlay` |
| 只影响校验 | `validator_contract_candidate` |
| 无法表达 | `schema_gap` |

完成标准：

- 语句排序“时间脉络”被正确判成 `ordering_logic` / material overlay，而不是硬塞 `middle_structure_type`；
- 语句填空“承上启下”能落到 `function_type=bridge` 与 `bidirectional_validation=high`；
- 中心理解“对策/转折/并列”能落到 business feature card 或 material card。

### 阶段 5：校验器接入

预蒸馏字段必须能产生校验问题，例如：

```yaml
validator_contract_candidates:
  - check_name: require_opening_anchor_evidence
    applies_when:
      opening_anchor_type: background_intro
  - check_name: require_binding_pair_explanation
    applies_when:
      local_binding_strength: high
  - check_name: reject_topical_grouping_only
    applies_when:
      ordering_logic: timeline_progression
```

完成标准：

- 每个高置信候选字段至少对应一个可测校验点；
- validator 只消费候选契约，不自己发明新规则；
- 低置信字段不能进入 validator contract。

### 阶段 6：前端工作台接入

建议新增一个轻量 tab：

```text
叶族预蒸馏
```

显示：

- 题包列表；
- 解析题量；
- 叶族内支持率；
- 候选字段；
- schema gap；
- 推荐落位；
- 一键创建 distill session；
- 一键生成 patch draft。

第一版不要做复杂编辑器，只做报告预览和进入 review。

## 阈值建议

字段候选分级：

| 等级 | 条件 |
|---|---|
| high | support_rate >= 0.85 且样本数 >= 30 |
| medium | support_rate >= 0.60 且样本数 >= 15 |
| low | support_rate >= 0.35 或样本数不足 |
| reject | support_rate < 0.35 且无强人工证据 |

晋升建议：

| 候选等级 | 可进入 |
|---|---|
| high | slot_projection_draft / validator_candidate |
| medium | report only / needs ablation |
| low | evidence appendix |
| reject | rejected_candidates |

## 消融实验要求

每个准备落位的字段都要回答：

1. 去掉该字段，唯一性是否下降？
2. 去掉该字段，错项是否变弱？
3. 去掉该字段，生成题是否更容易跑偏？
4. 它是否只改善格式，而不改善题目质量？
5. 它是否只在当前叶族有效，不能上升到子族/母族？

只有通过至少 1-3 的字段，才建议进入正式 patch。

## 数据层建议

短期不建表，先 artifact 化：

```text
data/leaf_pre_distill/{job_id}/manifest.json
data/leaf_pre_distill/{job_id}/samples.jsonl
data/leaf_pre_distill/{job_id}/behavior_traces.jsonl
data/leaf_pre_distill/{job_id}/field_candidates.json
data/leaf_pre_distill/{job_id}/slot_projection_draft.yaml
data/leaf_pre_distill/{job_id}/report.md
```

中期若稳定，再建表：

- `leaf_pre_distill_jobs`
- `leaf_pre_distill_samples`
- `leaf_pre_distill_candidates`
- `leaf_pre_distill_reviews`

## 测试计划

### 单元测试

- docx 解析能抽出题号、题干、选项、答案、解析、考点；
- 叶族标记不依赖文件名唯一规则；
- support rate 计算稳定；
- schema gap 能正确识别；
- slot projection 不写回正式配置。

### 回归测试

用已有四组实验作为 golden set：

- 中心理解四包；
- 语句填空四包；
- 语句排序四包。

要求核心字段复现率：

| 题型 | 最低复现要求 |
|---|---:|
| 中心理解 | >= 80% |
| 语句填空 | >= 80% |
| 语句排序 | >= 85% |

### 集成测试

- 预蒸馏 job 生成 artifact；
- artifact attach 到 distill session；
- run review 可以引用 artifact；
- patch target 可以写入 `leaf_pre_distill_report`；
- promotion bundle 保留 artifact path。

## 推荐落地顺序

### 第 1 步：整理离线工具

把 `tools/analyze_sentence_order_leaf_fields.py` 扩展为通用工具，不再只服务语句排序。

建议拆成：

```text
tools/leaf_pre_distill/docx_reader.py
tools/leaf_pre_distill/sample_parser.py
tools/leaf_pre_distill/behavior_marker.py
tools/leaf_pre_distill/field_candidate_builder.py
tools/leaf_pre_distill/report_renderer.py
```

### 第 2 步：定义 artifact schema

先写 schema 文档，不急着写 API。

文件建议：

```text
docs/leaf_pre_distill_artifact_contract.md
```

### 第 3 步：接入 distill patch target

扩展 `DistillPromotionTarget`，加入：

- `leaf_pre_distill_report`
- `schema_gap_report`
- `validator_contract`
- `business_feature_card`
- `material_card`
- `runtime_mapping`

### 第 4 步：做最小 API

先做本地路径版本：

```text
POST /api/v1/distill/leaf-preprocess/jobs
```

只跑 job 并生成 artifact，不做 UI。

### 第 5 步：做前端报告页

只展示：

- 样本数；
- 字段候选；
- 支持率；
- 推荐落位；
- schema gap；
- attach to distill session。

### 第 6 步：进入正式调试链

每个新叶族的正式流程变成：

```text
预蒸馏报告
-> 人工确认候选字段
-> 创建 distill session
-> trial
-> review
-> patch
-> promotion
-> 人工写回 card_specs
```

## 最小可行版本

MVP 只需要做 5 件事：

1. 通用 docx 题包解析。
2. 行为痕迹标注。
3. 字段候选聚合。
4. slot projection draft。
5. 生成 Markdown 报告和 JSON artifact。

MVP 不需要：

- 数据库表；
- 自动改 card_specs；
- 完整 UI；
- 文件上传；
- LLM 自动裁判。

## 最终判断

可以加入，而且应该加入。

但它应该作为“候选字段初始化层”，不是“最终协议生成层”。它和现有系统的关系应该是：

```text
叶族预蒸馏负责提出可证据化候选
现有蒸馏工作台负责试跑与评审
promotion 负责记录可沉淀改动
题卡体系负责成为最终规则来源
```

这样，你的系统就能把“初始字段从哪来”解释清楚：不是模型灵感，不是人工玄学，而是从干净叶族样本中抽取稳定解题动作，再经过落位、消融和人审后进入协议。

# 蒸馏协议与题卡落位审计报告

日期：2026-04-24

## 结论

当前系统已经具备“题卡驱动 + 蒸馏工作台 + 人审 promotion”的主体骨架，可以承接叶族预蒸馏实验，但还缺一个明确的“新叶族进入系统前的预处理层”。

我对当前成熟度的判断是：

| 模块 | 成熟度 | 判断 |
|---|---:|---|
| 题卡主权协议 | 高 | 文档边界清楚，原则正确 |
| 母族 / 子族 / 叶族运行映射 | 中高 | 已有 leaf primary / parent supplement 逻辑 |
| 蒸馏工作台 | 中高 | 适合 replay、调参、人审、promotion |
| 行为蒸馏 | 中 | 能从历史使用行为回收 patch hints |
| 新叶族预处理 | 低 | 目前主要靠临时脚本和人工报告 |
| promotion 目标层级 | 中低 | 目标类型不够覆盖题卡生态 |
| 字段候选落位机制 | 中 | 有 slot / overlay / material card 基础，但缺候选字段报告契约 |

一句话：现在的系统已经能做“已有协议的拟合与回流”，但还没有把“未知新叶族如何生成初始字段”产品化。

## 已经做对的地方

### 1. 规则主权边界是对的

`docs/card_driven_protocol.md` 已经把核心边界写清楚：

- 题卡决定组合规则；
- 母族决定公共协议；
- 业务卡决定特征投影；
- service / prompt / validator 只执行，不私自定义题意。

这对叶族预蒸馏特别重要。因为预蒸馏会产出很多“看起来合理”的字段，如果没有这个边界，很容易把实验结果直接写进 service，最后系统变成一堆硬编码分支。

### 2. 蒸馏工作台已有正式闭环

`prompt_skeleton_service/app/schemas/distill.py` 中已有：

- dataset
- session
- trial / run
- human review
- patch
- promotion

`prompt_skeleton_service/app/services/distill_workbench.py` 也已经实现了：

- 数据集创建；
- train/dev/test 切分；
- trial 运行；
- truth fit summary；
- review gate；
- patch gate；
- promotion bundle。

这意味着“叶族预蒸馏”不需要重造一套实验系统，而应当成为现有蒸馏台的前置阶段。

### 3. 运行时已经存在叶族优先的 overlay 口径

`card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml` 已经明确：

```text
leaf is primary, child supplements shared structure, mother supplements family boundary
```

`prompt_skeleton_service/app/services/distill_runtime_overlay.py` 也已经能从母族、子族、material card、prompt extras 推导 overlay。

这说明你的系统不是只有“母族大卡”，而是已经承认叶族是最小硬逻辑单元。叶族预蒸馏可以很自然地接到这里。

### 4. 题卡本身有足够的落位层级

以语句填空和语句排序为例，当前题卡已经有：

- `structure_schema`
- `slot_schema`
- `base_slots`
- `material_card_overrides`
- `validator_contract`
- `distill_runtime_overlay`
- `preferred_material_cards`
- `upstream_contract`

这些层级足够承载我们最近实验里蒸出来的字段。例如：

- 语句填空的 `blank_position / function_type / bidirectional_validation / semantic_scope`
- 语句排序的 `opening_anchor_type / local_binding_strength / closing_anchor_type / ordering_logic / uniqueness_source`

## 主要问题

### P1. 当前没有“叶族预蒸馏”正式对象

现在 `DistillDatasetSampleInput` 只接收结构化后的 `truth_source_question`、`generation_request`、split、metadata 等。它适合已有样本进入 replay，但不负责：

- 批量解析 docx 题包；
- 识别叶族边界；
- 聚合解析/考点/解题动作；
- 生成候选字段；
- 标出 schema gap；
- 产出 slot projection draft。

所以我们刚刚做的中心理解、语句填空、语句排序复现实验，本质上还在“外部临时脚本 + 人工报告”层。

风险：如果不把它纳入实验台，后续每个新叶族都会重复手工拆包、手工统计、手工写报告，初始化解释依然无法稳定复现。

### P1. promotion target 不足以表达题卡生态

当前 `prompt_skeleton_service/app/schemas/distill.py` 的 promotion target 是：

```python
Literal["question_card", "prompt_config", "material_strategy"]
```

但另一个蒸馏结果协议 `prompt_skeleton_service/app/schemas/distillation.py` 的 patch target 是：

```python
Literal["question_card", "prompt_assets", "validator_contract", "material_mapping"]
```

这两个口径已经不完全一致。

而叶族预蒸馏至少还需要表达：

- `business_feature_card`
- `material_card`
- `signal_layer`
- `runtime_mapping`
- `validator_contract`
- `prompt_assets`
- `leaf_pre_distill_report`
- `schema_gap_report`

风险：预蒸馏能发现问题，但 promotion 不能正确承载落位目标，最后会被迫塞进 `question_card` 或 `material_strategy` 这种宽泛桶里，审计链会变脏。

### P1. 当前行为蒸馏只适合“后验回收”，不适合“新叶族初始化”

`DistillationBehaviorService` 是从生成后的 item version、review action、usage event 中抽取行为信号。它解决的是：

```text
用户怎么改我们已经生成的题
```

但叶族预蒸馏要解决的是：

```text
一个新叶族题包本身强迫模型/人类做哪些稳定解题动作
```

这两个任务相邻，但不是同一个。

风险：如果把新叶族初始化强行塞进行为蒸馏，会混淆“真题内在结构”与“用户后验修题行为”。

### P2. `distillation.py` 仍然是 sentence_fill 专用最小协议

`prompt_skeleton_service/app/schemas/distillation.py` 里：

```python
DistillationFamilyId = Literal["sentence_fill"]
```

并且 difficulty dimensions 固定为语句填空的四个维度：

- `local_binding_complexity`
- `global_context_dependency`
- `distractor_similarity`
- `blank_function_ambiguity`

这对早期封板是合理的，但现在已经跑过中心理解、语句填空、语句排序三类叶族，继续用它做统一入口会不够。

风险：新增叶族时，字段会被迫翻译成 sentence_fill 维度，造成错误归因。

### P2. source question analyzer 里仍有较多业务映射硬编码

`prompt_skeleton_service/app/services/source_question_analyzer.py` 中存在：

- `_SENTENCE_ORDER_CARD_IDS`
- `_SENTENCE_FILL_CARD_IDS`
- `_project_leaf_taxonomy`
- 多组题型 marker 与 business card 映射

这些对现阶段运行有价值，但从长期题卡主权看，它们属于“服务层携带业务口径”的风险点。

风险：叶族预蒸馏如果继续往 analyzer 里加 marker，会和 `docs/card_driven_protocol.md` 的原则冲突。更好的做法是让 analyzer 读取外部 leaf behavior schema / signal config，而不是继续扩展硬编码。

### P2. overlay 能表达运行补充，但不能保存蒸馏证据

`DistillRuntimeOverlayService.resolve()` 能返回：

- mother family
- child family
- leaf key
- material card
- business card
- slot defaults
- prompt guard lines

但它不保存：

- support rate
- evidence count
- sample coverage
- schema gap
- rejected candidates
- human decision
- field confidence

风险：运行时知道“用哪个 leaf”，但不知道这个 leaf 字段当初是怎么蒸出来的。长期维护会丢失可解释性。

### P2. 题卡 schema 已经能承载很多字段，但缺“候选状态”

现在题卡字段大多是正式字段。叶族预蒸馏产物不应该一开始就进入正式字段，而应先进入候选层，例如：

```yaml
candidate_fields:
  - field_path: base_slots.opening_anchor_type
    proposed_value: background_intro
    support_rate: 1.0
    confidence: high
    target_layer: question_card
    status: draft
```

风险：没有候选层，会让实验结果要么不能进系统，要么过早污染正式协议。

### P3. 当前 docx / 题包解析还不是通用能力

我们这几轮实验是用临时脚本解析 docx。系统里有 `SourceQuestionParserService`，但它面向单题 raw text，不是面向题包批量导入、叶族分组、统计聚合。

风险：入口不产品化，就无法形成“每个新叶族都走同一套预处理”的制度。

## 叶族预蒸馏该放在哪一层

推荐新增一个前置模块：

```text
leaf_pre_distill_lab
```

它的定位是：

```text
新叶族题包
-> 结构化抽取
-> 行为痕迹标注
-> 字段候选蒸馏
-> schema 投影
-> 人审与消融前的候选报告
```

它不直接做：

- 自动写回 question card；
- 自动写回 business feature card；
- 自动修改 validator；
- 自动修改 prompt；
- 自动替代人工归纳。

## 审计建议

### 1. 新增预蒸馏对象，而不是复用 run

新增对象建议叫：

- `leaf_pre_distill_job`
- `leaf_pre_distill_sample`
- `leaf_field_candidate`
- `leaf_slot_projection_draft`
- `schema_gap_report`

它们可以先以 JSON artifact 形式落地，不急着建数据库表。

### 2. 统一 patch / promotion target 口径

建议将 target 扩展为：

```python
Literal[
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

并保留兼容 alias：

- `prompt_config` -> `prompt_assets`
- `material_strategy` -> `material_mapping`

### 3. 把候选字段分为四种落位结果

| 落位类型 | 含义 |
|---|---|
| `canonical_slot` | 可直接进入母族/题卡已有 slot |
| `business_feature_projection` | 适合成为业务卡 `slot_projection` |
| `material_card_overlay` | 更像材料卡 / 中间结构卡特征 |
| `schema_gap` | 现有 schema 无法表达，需要新字段或换层 |

例如语句排序“时间脉络”不应强塞 `middle_structure_type=timeline_progression`，更合理是：

```yaml
middle_structure_type: local_binding
ordering_logic: timeline_progression
business_feature_overlay: timeline_action_sequence
```

### 4. 预蒸馏报告必须包含反证和消融入口

每个字段候选至少要有：

- support rate；
- evidence examples；
- negative examples；
- expected validator check；
- ablation question；
- target layer；
- confidence；
- human review decision。

### 5. 不要把新叶族 marker 继续塞进 analyzer

短期可以保留现有 analyzer，但新增叶族应该优先走配置化规则：

```text
leaf_behavior_signal_schema.yaml
```

而不是继续往 service 文件里加 `_XYZ_MARKERS`。

## 总体评估

当前系统可以加入叶族预蒸馏实验台，但应该按“候选产物层”接入，而不是按“自动落位层”接入。

最稳的路径是：

```text
leaf_pre_distill_lab 产出候选报告
-> distill workbench 绑定候选报告做 trial
-> review 批准
-> patch 明确目标
-> promotion bundle
-> 人工写回正式 card_specs / configs
```

这条路和你现有的协议精神是一致的：模型负责提出候选，系统负责记录证据，人负责决定晋升，题卡负责成为最终规则来源。

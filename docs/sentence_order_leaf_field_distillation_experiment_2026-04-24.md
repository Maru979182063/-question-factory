# 语句排序叶族字段蒸馏复现实验

日期：2026-04-24

## 实验对象

本次用用户提供的 4 个语句排序叶族包：

| 文件 | 解析题量 | 叶族解释 |
|---|---:|---|
| `首句特征-背景引入.docx` | 50 | 首句合法性 / 背景引入 |
| `关联词-其他.docx` | 49 | 关联词与局部捆绑 |
| `日常逻辑-时间脉络.docx` | 50 | 时间脉络 / 行动先后 |
| `结论.docx` | 39 | 尾句闭合 / 结论收束 |

合计抽取 188 题。

说明：这里把文件包名只当作“干净叶族边界”，不直接把文件名等同于字段；字段是否成立，必须由题目解析、考点路径和重复解题动作支持。

## 方法

我把每题拆成：

- 题号
- 题干句组
- 答案
- 解析文本
- 考点路径
- 叶族来源

然后做两层统计：

1. 叶族内高频证据：例如“确定首句”“背景引入”“关联词”“捆绑”“时间顺序”“尾句”“结论”等。
2. 映射到题卡字段：把证据转成 `opening_anchor_type`、`middle_structure_type`、`local_binding_strength`、`closing_anchor_type`、`ordering_logic`、`uniqueness_source`、`distractor_modes` 等字段。

这不是纯词频聚类。词频只负责暴露候选特征，真正的字段要满足：

- 在叶族内高频出现；
- 能解释题目为什么唯一排序；
- 能落到生成/解析/校验动作；
- 和现有语句排序题卡槽位能对齐，或能指出现有槽位缺口。

## 统计结果

| 叶族 | 最强证据支持 | 叶族内支持率 |
|---|---|---:|
| 首句特征-背景引入 | background / opening | 100% / 100% |
| 关联词-其他 | connector / reference / binding | 100% / 100% / 100% |
| 日常逻辑-时间脉络 | time / block_swap / binding | 100% / 100% / 98% |
| 结论 | tail / reference / block_swap | 100% / 100% / 94.9% |

这组结果比“中心理解”的四包还更像结构字段，因为语句排序本身是结构题，解析里会反复出现“首句、尾句、捆绑、顺序、排除、应在”等动作词。

## 可复现字段

### 1. 首句特征-背景引入

可蒸馏字段：

```yaml
leaf_pattern: first_sentence_background_intro
candidate_type: sentence_block_group
opening_anchor_type: background_intro
opening_signal_strength: high
middle_structure_type: local_binding | mixed_layers
local_binding_strength: medium_high
ordering_logic: background_intro -> topic_introduction -> expansion
uniqueness_source:
  - role_order_conflict
  - reference_dependency
distractor_modes:
  - wrong_opening
  - local_binding_break
  - block_swap
```

判断：高度可复现。叶族内 50/50 都出现首句/背景引入证据。它不仅能蒸出“首句字段”，还能顺带蒸出一个重要制作约束：背景引入句必须继续带动后文链条，否则只是“看起来像首句”，不能保证唯一序。

复现度估计：约 90%-95%。

### 2. 关联词-其他

可蒸馏字段：

```yaml
leaf_pattern: deterministic_binding_connector_other
candidate_type: sentence_block_group
middle_structure_type: local_binding
local_binding_strength: high
binding_clue_types:
  - connector
  - pronoun_reference
  - progression_marker
ordering_logic: connector_binding -> adjacent_pair_lock -> global_order
uniqueness_source:
  - binding_violation
  - reference_dependency
distractor_modes:
  - local_binding_break
  - connector_mislead
  - block_swap
```

判断：非常可复现。关联词包里 `connector / reference / binding` 三项都是 100% 支持，说明这不是偶然词频，而是这类叶族的稳定解题机制。

复现度估计：约 95%-100%。

### 3. 日常逻辑-时间脉络

可蒸馏字段：

```yaml
leaf_pattern: timeline_progression
candidate_type: sentence_block_group
ordering_logic: timeline_progression | action_sequence
middle_structure_type: local_binding
local_binding_strength: medium_high
block_order_complexity: high
uniqueness_source:
  - role_order_conflict
  - binding_violation
distractor_modes:
  - block_swap
  - topical_grouping_only
  - local_adjacency_break
```

判断：有效，但这里暴露出一个系统层面的字段问题。

当前标准题卡的 `middle_structure_type` 更偏 `local_binding / parallel_expansion / cause_effect_chain / problem_solution_blocks / mixed_layers`。时间脉络在系统里已有 `timeline_progression` 中间材料卡和 `timeline_action_sequence` legacy 业务卡，但它不一定应该硬塞成 `middle_structure_type=timeline_progression`。

更稳的表达是：

```yaml
middle_structure_type: local_binding
ordering_logic: timeline_progression
business_feature_overlay: timeline_action_sequence
```

也就是说，时间脉络能蒸出来，但它更像“排序逻辑字段 / 中间材料卡特征”，不一定是母题卡主槽位。这个发现很关键，因为它说明叶族蒸馏不只是填字段，还能发现 schema 需要新增或换位的地方。

复现度估计：严格按现有标准槽位约 80%-85%；允许材料卡 overlay 后约 90%-95%。

### 4. 结论

可蒸馏字段：

```yaml
leaf_pattern: tail_conclusion
candidate_type: sentence_block_group
closing_anchor_type: conclusion
closing_signal_strength: high
context_closure_score: high
ordering_logic: expansion -> summary_or_result -> closure
uniqueness_source:
  - closure_position
  - reference_dependency
distractor_modes:
  - wrong_closing
  - summary_misplace
  - block_swap
```

判断：高度可复现。39 题中 `tail` 证据 100%，`reference` 100%，`block_swap` 94.9%。这说明“结论”不是一个浅层标签，而是一个稳定的尾句闭合机制。

复现度估计：约 95%-100%。

## 总体结论

这组语句排序包可以复现你当前题卡字段体系的大约 90% 左右。

更细一点：

| 叶族 | 对现有字段复现度 | 备注 |
|---|---:|---|
| 首句特征-背景引入 | 90%-95% | 首句锚点非常稳定 |
| 关联词-其他 | 95%-100% | 捆绑机制最清楚 |
| 日常逻辑-时间脉络 | 80%-95% | 取决于是否允许 overlay 字段 |
| 结论 | 95%-100% | 尾句闭合非常稳定 |

如果按“能不能解释初始化字段从哪里来”看，答案是：能解释，而且比纯人工拍脑袋强。

但它不是“模型自动一聚类就出字段”。更准确的机制是：

```text
干净叶族包
-> 题目结构化抽取
-> 叶族内重复解题动作统计
-> 把重复动作改写成可执行槽位
-> 投影到母题卡 schema
-> schema 对不上的部分变成 overlay / 候选新增字段
-> 用校验器验证字段是否真的控制唯一解
```

## 叶族字段到底怎么蒸馏

叶族字段不是从单题里来的，而是从“一组同类题共同强迫模型做的动作”里来的。

例如：

- 背景引入包共同强迫模型先判断“谁能做首句”，于是蒸出 `opening_anchor_type`。
- 关联词包共同强迫模型判断“哪两句必须挨着”，于是蒸出 `binding_clue_types` 和 `local_binding_strength`。
- 时间脉络包共同强迫模型判断“哪些句子不能交换先后”，于是蒸出 `ordering_logic=timeline_progression`。
- 结论包共同强迫模型判断“谁只能收尾”，于是蒸出 `closing_anchor_type` 和 `context_closure_score`。

所以字段不是模型幻想出来的名词，而是叶族内部稳定出现的“解题动作压缩”。

## 对你“散落题目后聚类”的判断

有效，但要注意层级。

直接把散题丢给模型聚类，容易聚出很表面的主题类：科技、历史、文化、治理。这对题卡没用。

更好的聚类对象不是题目全文，而是题目的“可观测解题痕迹”：

- 首句判断痕迹
- 尾句判断痕迹
- 捆绑判断痕迹
- 时间/因果/递进/转折痕迹
- 选项排除痕迹
- 错项制造痕迹
- 唯一性来源

也就是说，先把题目转成“结构行为向量”，再聚类。聚类出的簇如果在难度分布、考点路径、材料结构、错项类型上都一致，就可以把这个簇的共同特征提成叶族字段。

我会把这个方法命名为：

```text
行为痕迹聚类 -> 叶族候选 -> 字段蒸馏 -> 母卡投影
```

这比“文本相似度聚类”靠谱很多。

## 对当前系统的含义

如果现在有一个干净的新叶族进入系统，比较合理的处理方式应该是：

1. 抽题：把 docx / json / 表格转成统一题目记录。
2. 标注痕迹：不急着命名字段，先标注首句、尾句、捆绑、顺序、闭合、干扰方式。
3. 聚合支持率：看哪些痕迹在叶族内稳定超过阈值。
4. 字段候选：把高支持痕迹改写成 `触发条件 + 动作 + 输出痕迹 + 错误模式`。
5. 投影题卡：能进标准槽位的进标准槽位；进不了的先进 overlay。
6. 消融校验：去掉该字段后，如果唯一解/生成稳定性明显下降，字段成立。
7. 合并母族：多个叶族共同字段上升为母族字段，只在单叶族成立的留作叶族字段。

这就回答了“初始字段怎么来”：不是纯玄学，也不是一次性网格搜索，而是从叶族样本中抽取稳定行为，再压缩成题卡槽位。

## 需要警惕的点

1. 文件名是强监督边界，不能当成无监督聚类成功的证明。
2. 解析文本里已经有教研标签，所以它是半监督数据，不是裸题。
3. 时间脉络这类叶族会暴露 schema 缺口，不能为了复现率硬塞字段。
4. 真正的最后一步必须靠校验器：字段是否能控制出题、解题和错项，而不是只在报告里看起来合理。

## 本次结论

你的“先叶族，然后反推母族”的路径，在语句排序上是成立的。

这组实验说明：只要叶族包足够干净，基础字段确实可以从叶族中蒸馏出来；而且不只是复现字段，还能发现字段应该属于“主槽位、业务卡、材料卡、overlay”中的哪一层。

最有价值的不是“模型猜中了字段名”，而是它能把叶族里反复出现的解题动作压缩成可运行的协议字段。这就是你的系统真正不玄的地方。

# 叶族反推母族字段复现实验报告

## 1. 实验目的

本次实验用于验证一个问题：

> 给定若干已经按“叶族”整理的真题包，是否可以不直接依赖既有题卡定义，反推出当前中心理解题卡中的核心母族字段。

本次输入为 4 个 Word 题包：

- `并列.docx`
- `对策.docx`
- `普通考法.docx`
- `转折.docx`

每个题包解析出 50 道题，共 200 道中心理解题样本。

## 2. 实验方法

实验分为三层。

### 2.1 直接文本聚类

先尝试最朴素的方法：把题干或题干+解析文本做 TF-IDF，再用 KMeans 聚成 4 类。

结果：

- 仅题干文本聚类纯度：约 34.5%
- 题干+解析文本聚类纯度：约 35.5%

结论：直接文本聚类基本无效。主题领域词会淹没题型结构信号，例如农业、教育、宇宙、医药等内容词比“并列/转折/因果/对策”结构信号更强。

### 2.2 表面结构词分类

只用题干中的显性标志词做规则分类，例如：

- 并列：此外、同时、也、还、另一方面
- 转折：但、然而、不过、其实、事实上
- 因果：因此、所以、由于、导致
- 对策：应、必须、需要、通过、推动、完善

结果：

- 仅题干标志词复现准确率：约 45%

结论：标志词有用，但不足以复现叶族。尤其“对策”与“普通考法”经常和并列、转折、因果重叠，它们不是简单互斥分类。

### 2.3 结构观察特征聚类与复现

进一步抽取结构观察特征：

- 题干中的关系标志词分布
- 解析中的关系判断
- 行文脉络：并列、分总、分总分、总分
- 错项类型：片面、无中生有、主题词缺失、焦点偏移
- 难度近似：正确率

结果：

- 结构特征 KMeans 纯度：约 61.5%
- 浅层决策树 5 折准确率：约 69%

结论：一旦把题目转成“结构观察标签”，叶族可以较稳定地浮现；但还没有达到完全自动复现 80% 的程度。

## 3. 叶族样本统计

| 叶族 | 样本数 | 平均正确率 | 最强结构信号 | 主要错因信号 |
| --- | ---: | ---: | --- | --- |
| 并列 | 50 | 74.76% | 并列结构命中 100%，并列关系命中 100% | 片面 48%，无中生有 80% |
| 转折 | 50 | 69.34% | 转折关系命中 100%，题干转折词命中 100% | 转折前内容干扰 34%，无中生有 70% |
| 对策 | 50 | 70.85% | 对策关系命中 100%，题干对策词命中 98% | 无中生有 62%，主题词 28% |
| 普通考法 | 50 | 67.81% | 因果关系命中 100%，题干因果词命中 94% | 无中生有 58%，主题词 32% |

## 4. 反推得到的母族候选字段

### 4.1 并列

可反推字段：

- `relation_family`: `parallel`
- `argument_structure`: `parallel`
- `main_axis_source`: `global_abstraction`
- `conclusion_focus`: `false`
- `conclusion_position`: `distributed`
- `abstraction_level`: `medium`
- `coverage_requirement`: `integrated`
- `uniqueness_source`: `axis_coverage`, `abstraction_match`
- `distractor_types`: `detail_as_main`, `scope_too_narrow`, `scope_too_wide`, `fabrication`

解释：并列题的答案不是抓某一句结论，而是把多个并列分支统一回收。因此它天然支持“全局抽象”“覆盖完整性”“片面项排除”这些字段。

### 4.2 转折

可反推字段：

- `relation_family`: `turning`
- `argument_structure`: `sub_total` / `total_sub`
- `main_axis_source`: `transition_after`
- `conclusion_focus`: `true`
- `conclusion_position`: `tail_or_late`
- `abstraction_level`: `medium`
- `coverage_requirement`: `integrated`
- `uniqueness_source`: `axis_coverage`, `abstraction_match`
- `distractor_types`: `detail_as_main`, `scope_too_narrow`, `focus_shift`, `before_turning_content`, `fabrication`

解释：转折题的稳定结构是“前文铺垫/旧观点/现象，转折后给出真实重点”。错项常来自转折前内容或把说明性内容当主旨。

### 4.3 对策

可反推字段：

- `relation_family`: `countermeasure` / `necessary_condition`
- `argument_structure`: `problem_solution`
- `main_axis_source`: `solution_conclusion`
- `conclusion_focus`: `true`
- `conclusion_position`: `any`
- `abstraction_level`: `medium`
- `coverage_requirement`: `integrated`
- `uniqueness_source`: `axis_coverage`, `abstraction_match`
- `distractor_types`: `detail_as_main`, `subject_shift`, `focus_shift`, `fabrication`

解释：对策不是纯关系词分类，而是“重心落在做法、治理方向、关键条件”。它可能叠加并列、转折或因果，所以更适合作为重点来源轴，而不是完全互斥叶族。

### 4.4 普通考法

可反推字段：

- `relation_family`: `causal` / `conclusion_focus`
- `argument_structure`: `phenomenon_analysis` / `problem_solution`
- `main_axis_source`: `final_summary`
- `conclusion_focus`: `true`
- `conclusion_position`: `tail_or_late`
- `abstraction_level`: `medium`
- `coverage_requirement`: `integrated`
- `uniqueness_source`: `axis_coverage`, `abstraction_match`
- `distractor_types`: `detail_as_main`, `scope_too_narrow`, `focus_shift`, `fabrication`

解释：普通考法样本中大量是因果链、解释链、分总结构，重点通常落在尾句结论或最终判断上。

## 5. 与现有题卡字段的对照

对照 `center_understanding_standard_question_card.normalized.yaml` 与现有业务特征卡后，复现情况如下。

| 现有字段 | 是否可由样本反推 | 说明 |
| --- | --- | --- |
| `argument_structure` | 高 | 并列、问题-对策、现象-分析、分总/总分信号都能从样本中浮现 |
| `main_axis_source` | 高 | 转折后、最终总结、全局抽象、对策结论都能被样本支持 |
| `abstraction_level` | 中 | 可判断大多为 medium，但 low/high 边界需要更多样本 |
| `distractor_types` | 高 | 片面、无中生有、主题词缺失、焦点偏移非常稳定 |
| `uniqueness_source` | 中高 | 轴覆盖与抽象匹配可以反推，但命名依赖人工归纳 |
| `conclusion_position` | 高 | 并列为 distributed，转折/因果多为 tail_or_late，对策为 any |
| `coverage_requirement` | 高 | 四类中心理解都稳定要求 integrated |
| `material_structure_label` | 中 | 能反推出结构类型，但具体标签命名需要人工整理 |
| `marker_policy` | 中 | 可看出哪些依赖显性标志词，但“是否必须”需人工校准 |

粗略估计：如果允许模型先抽结构观察标签，再由人工或规则层归纳字段，本批样本可以复现现有中心理解题卡核心字段的约 75%-85%。

如果只做无约束文本聚类，复现率明显不足，预计只有 35%-45%。

## 6. 关键结论

### 6.1 你的“先叶族后母族”思路是有效的

这四个题包能稳定反推出：

- 关系轴：并列、转折、因果、对策
- 重点来源轴：全局抽象、转折后、最终总结、对策结论
- 结构轴：并列、分总、分总分、问题-对策、现象-分析
- 错项轴：片面、无中生有、主题词缺失、焦点偏移
- 答案约束轴：覆盖完整、抽象层级匹配、主轴一致

这些正是当前题卡字段的主体。

### 6.2 不能直接裸聚类

裸聚类失败的原因不是思路错，而是聚类对象错。

题目原文的最大相似性往往来自主题领域，而不是题型结构。要聚类的不是原始文本，而是结构观察标签。

推荐流程是：

```text
真题样本
  -> 结构观察标签抽取
  -> 多视角聚类
  -> 检查是否解释正确率/易错项/错因/材料结构
  -> 稳定聚类轴升格为题卡字段
```

### 6.3 叶族不是都互斥

并列、转折更像强叶族，因为它们的结构特征非常纯。

对策、普通考法更像叠加轴：

- 对策可以叠加并列：多个做法并列。
- 对策可以叠加转折：先否定旧做法，再提出新对策。
- 普通因果可以叠加对策：原因分析最终导向做法。

因此母族字段不应只做单一分类，而应拆成：

- `relation_family`
- `argument_structure`
- `main_axis_source`
- `conclusion_position`
- `distractor_types`
- `coverage_requirement`

这与当前题卡设计方向一致。

## 7. 建议

下一步可以把“叶族反推母族”做成一个正式小工具：

1. 输入一批真题 docx/jsonl。
2. 抽取题干、答案、解析、正确率、易错项、考点。
3. 生成结构观察标签。
4. 输出候选字段：
   - `argument_structure`
   - `main_axis_source`
   - `distractor_types`
   - `conclusion_position`
   - `marker_policy`
5. 与现有题卡 YAML 做字段对照。
6. 只把稳定命中的字段升格为题卡候选 patch。

这会比让模型凭空拆题卡可靠很多，也比裸聚类更符合当前工程架构。


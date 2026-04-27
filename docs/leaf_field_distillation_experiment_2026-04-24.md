# 叶族字段自动蒸馏试验报告

## 1. 试验问题

本次试验验证：

> 如果给系统 4 个干净叶族题包，是否能从题包本身蒸馏出叶族字段，从而解释题卡初始化字段不是拍脑袋来的。

输入题包：

- `并列.docx`
- `对策.docx`
- `普通考法.docx`
- `转折.docx`

每包解析 50 题，共 200 题。

## 2. 方法

这次没有做裸文本聚类，而是模拟“叶族字段蒸馏”流程：

```text
题包
-> 单题结构观察
-> 叶族内统计
-> 高支持率字段提升
-> 与现有题卡字段对照
```

单题结构观察包括：

- `relation_family`
- `argument_structure`
- `main_axis_source`
- `conclusion_position`
- `abstraction_level`
- `coverage_requirement`
- `marker_policy`
- `uniqueness_source`
- `distractor_types`

字段提升规则：

- 叶族内多数值作为候选字段值。
- 记录支持率、正例、反例、分布。
- 与现有题卡/业务特征卡中的预期字段做对照。

## 3. 总体结果

| 叶族 | 样本数 | 平均正确率 | 字段精确匹配 | 错项字段重合 | 综合估计 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 对策 | 50 | 70.85% | 7/7 | 100% | 100.0% |
| 并列 | 50 | 74.76% | 7/7 | 75% | 93.8% |
| 普通考法 | 50 | 67.81% | 6/7 | 100% | 89.3% |
| 转折 | 50 | 69.34% | 7/7 | 100% | 100.0% |

结论：在“已知这是一个干净叶族包”的前提下，叶族核心字段可以被较稳定地蒸馏出来。这个结果足以支持“初始化字段来自题目分布”这一解释。

## 4. 各叶族蒸馏结果

### 4.1 并列

蒸馏字段：

```yaml
relation_family: parallel
argument_structure: parallel
main_axis_source: global_abstraction
conclusion_position: distributed
abstraction_level: medium
coverage_requirement: integrated
marker_policy: explicit_marker_helpful
uniqueness_source:
  - axis_coverage
  - abstraction_match
distractor_types:
  - fabrication
  - detail_as_main
  - scope_too_narrow
  - subject_shift
  - focus_shift
```

关键支持率：

- `relation_family=parallel`: 90%
- `argument_structure=parallel`: 98%
- `main_axis_source=global_abstraction`: 90%
- `conclusion_position=distributed`: 98%
- `coverage_requirement=integrated`: 100%

解释：并列叶族非常稳定。它的核心不是某个尾句结论，而是多个分支共同构成主轴，所以自然蒸出 `global_abstraction` 和 `distributed`。

### 4.2 转折

蒸馏字段：

```yaml
relation_family: turning
argument_structure: sub_total
main_axis_source: transition_after
conclusion_position: tail_or_late
abstraction_level: medium
coverage_requirement: integrated
marker_policy: explicit_marker_strong
uniqueness_source:
  - axis_coverage
  - abstraction_match
distractor_types:
  - fabrication
  - focus_shift
  - detail_as_main
  - scope_too_narrow
  - subject_shift
```

关键支持率：

- `relation_family=turning`: 88%
- `main_axis_source=transition_after`: 88%
- `conclusion_position=tail_or_late`: 86%
- `marker_policy=explicit_marker_strong`: 88%
- `coverage_requirement=integrated`: 100%

解释：转折叶族的字段最清楚。转折词不仅是表面标志，更稳定改变了主轴来源：重点落在转折后。

### 4.3 对策

蒸馏字段：

```yaml
relation_family: countermeasure
argument_structure: problem_solution
main_axis_source: solution_conclusion
conclusion_position: any
abstraction_level: medium
coverage_requirement: integrated
marker_policy: explicit_marker_helpful
uniqueness_source:
  - axis_coverage
  - abstraction_match
distractor_types:
  - fabrication
  - subject_shift
  - focus_shift
  - detail_as_main
  - scope_too_narrow
```

关键支持率：

- `relation_family=countermeasure`: 80%
- `argument_structure=problem_solution`: 66%
- `main_axis_source=solution_conclusion`: 80%
- `conclusion_position=any`: 78%
- `coverage_requirement=integrated`: 100%

解释：对策字段能蒸出来，但它比并列/转折更容易混合其他结构。它的强字段不是固定位置，而是“主轴落在做法/治理/关键条件”。

### 4.4 普通考法

蒸馏字段：

```yaml
relation_family: causal
argument_structure: sub_total
main_axis_source: final_summary
conclusion_position: tail_or_late
abstraction_level: medium
coverage_requirement: integrated
marker_policy: explicit_marker_helpful
uniqueness_source:
  - axis_coverage
  - abstraction_match
distractor_types:
  - subject_shift
  - fabrication
  - focus_shift
  - detail_as_main
  - scope_too_narrow
```

关键支持率：

- `relation_family=causal`: 64%
- `argument_structure=sub_total`: 46%
- `main_axis_source=final_summary`: 64%
- `conclusion_position=tail_or_late`: 74%
- `coverage_requirement=integrated`: 100%

解释：普通考法能蒸出 `final_summary` 和 `tail_or_late`，但 `argument_structure` 不够纯。它不像一个强叶族，更像“因果/结论重点/分总结构”的混合包。

## 5. 对初始化问题的解释力

这次试验能解释一件事：

> 初始题卡字段不是必须凭空想出来，可以由干净叶族包的稳定分布反推。

字段来源可以这样解释：

| 初始化字段 | 题包中的来源 |
| --- | --- |
| `relation_family` | 解析/考点/题干标志词的高频一致性 |
| `argument_structure` | 解析中的行文脉络判断 |
| `main_axis_source` | 答案重点落点：转折后、对策句、并列整体、尾句总结 |
| `conclusion_position` | 重点句位置或分布方式 |
| `distractor_types` | 解析中的错项排除理由 |
| `coverage_requirement` | 中心理解题普遍要求整体覆盖 |
| `uniqueness_source` | 正确项区别于错项的稳定来源：主轴覆盖与抽象匹配 |

所以初始化不必解释为“人类灵感”。更准确的说法是：

```text
叶族样本分布
-> 单题结构观察
-> 叶族内稳定字段
-> 题卡初始化字段
```

## 6. 重要发现

### 6.1 并列和转折是强叶族

并列和转折的字段支持率很高，适合作为叶族字段初始化来源。

### 6.2 对策是重点来源轴，不完全是互斥叶族

对策会叠加并列、转折、因果，但它的 `main_axis_source=solution_conclusion` 很稳定。

### 6.3 普通考法不是很干净

普通考法能蒸出 `final_summary`，但 `argument_structure` 混杂。它更适合作为候选桶继续细分，而不是直接固化成一个稳定叶族。

## 7. 建议的正式蒸馏协议

后续可以把叶族字段蒸馏写成正式协议：

```yaml
field_candidate:
  field_name: main_axis_source
  field_value: transition_after
  support_rate: 0.88
  positive_examples:
    - "#10319905"
    - "#18475375"
    - "#18475459"
  negative_examples:
    - qid: "#17102242"
      observed_value: solution_conclusion
  promotion_status: strong
  promotion_reason: 叶族内高频稳定，且能解释错项来自转折前内容
```

建议阈值：

- `support_rate >= 0.80`：可作为叶族强字段。
- `0.60 <= support_rate < 0.80`：作为候选字段，需要人工审核或继续拆叶族。
- `support_rate < 0.60`：不应固化，说明该叶族内部混杂。

按这个标准：

- 并列：可固化。
- 转折：可固化。
- 对策：主轴字段可固化，结构字段需带混合说明。
- 普通考法：不建议作为完整叶族固化，建议继续拆分。

## 8. 结论

本次试验支持你的核心判断：

**先叶族，后反推母族，是有效的。**

更准确地说：

**干净叶族包可以自动蒸出大部分初始化字段；人不需要负责凭空创造字段，只需要审核低支持率字段和命名字段。**

这套机制可以解释题卡初始化的来源，也能把“玄学初始块”改造成“有样本支持率的字段提升”。


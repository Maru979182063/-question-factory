# 语句填空叶族字段自动蒸馏试验报告

## 1. 试验目的

本次试验用于验证：

> 中心理解上的“干净叶族包 -> 字段支持率 -> 初始化字段”逻辑，能否迁移到语句填空。

输入题包：

- `横线在开头-概括后文.docx`
- `横线在结尾-总结前文（原为 结论）.docx`
- `横线在中间-承上启下.docx`
- `横线在中间-承上.docx`

其中前三个题包各解析出 50 题；`横线在中间-承上.docx` 实际只解析出 8 题，样本量不足，结论需保守。

## 2. 蒸馏字段

本次从每题中抽取以下观察字段：

- `blank_position`
- `function_type`
- `logic_relation`
- `context_dependency`
- `bidirectional_validation`
- `semantic_scope`
- `reference_dependency`
- `abstraction_level`
- `uniqueness_source`
- `correct_answer_shape`
- `distractor_modes`

这组字段与现有 `sentence_fill` 标准题卡高度一致。

## 3. 总体结果

| 叶族 | 样本数 | 平均正确率 | 核心字段复现 |
| --- | ---: | ---: | ---: |
| 开头-概括后文 | 50 | 66.27% | 5/5 |
| 结尾-总结前文 | 50 | 67.54% | 5/5 |
| 中间-承上启下 | 50 | 63.02% | 5/5 |
| 中间-承上 | 8 | 64.34% | 4/4 |

结论：语句填空比中心理解更适合叶族字段蒸馏，因为位置与功能字段更强，支持率更高。

## 4. 各叶族蒸馏字段

### 4.1 开头-概括后文

蒸馏结果：

```yaml
blank_position: opening
function_type: summary
logic_relation: summary
context_dependency: high
bidirectional_validation: forward_only_high
semantic_scope: paragraph_level
reference_dependency: low
abstraction_level: high
uniqueness_source:
  - function_mismatch
  - scope_mismatch
correct_answer_shape: original_sentence_or_clause
distractor_modes:
  - function_mismatch
  - single_dimension_only
```

关键支持率：

- `blank_position=opening`: 100%
- `function_type=summary`: 100%
- `logic_relation=summary`: 100%
- `bidirectional_validation=forward_only_high`: 100%
- `semantic_scope=paragraph_level`: 100%
- `abstraction_level=high`: 100%

解释：开头概括后文的本质是“看后文，提炼总领句”。它不需要承接前文，但强依赖后文整体信息，因此自然蒸出 `forward_only_high` 与 `paragraph_level`。

### 4.2 结尾-总结前文

蒸馏结果：

```yaml
blank_position: ending
function_type: conclusion
logic_relation: summary
context_dependency: high
bidirectional_validation: backward_only_high
semantic_scope: paragraph_level
reference_dependency: low
abstraction_level: high
uniqueness_source:
  - function_mismatch
  - scope_mismatch
correct_answer_shape: original_sentence_or_clause
distractor_modes:
  - weak_backward_link
  - single_dimension_only
  - function_mismatch
```

关键支持率：

- `blank_position=ending`: 100%
- `function_type=conclusion`: 100%
- `logic_relation=summary`: 100%
- `bidirectional_validation=backward_only_high`: 100%
- `semantic_scope=paragraph_level`: 100%
- `abstraction_level=high`: 100%

解释：结尾总结前文的本质是“看前文，压缩为收束句”。它不需要引出下文，但强依赖前文主线，因此自然蒸出 `backward_only_high`。

### 4.3 中间-承上启下

蒸馏结果：

```yaml
blank_position: middle
function_type: bridge
logic_relation: continuation
context_dependency: high
bidirectional_validation: high
semantic_scope: sentence_level
reference_dependency: medium
abstraction_level: medium
uniqueness_source:
  - function_mismatch
  - reference_failure
  - scope_mismatch
correct_answer_shape: original_sentence_or_clause
distractor_modes:
  - weak_backward_link
  - weak_forward_link
  - function_mismatch
  - single_dimension_only
  - topic_shift
```

关键支持率：

- `blank_position=middle`: 100%
- `function_type=bridge`: 100%
- `logic_relation=continuation`: 100%
- `context_dependency=high`: 100%
- `bidirectional_validation=high`: 100%
- `semantic_scope=sentence_level`: 100%
- `reference_dependency=medium`: 96%
- `uniqueness_source=function_mismatch/reference_failure/scope_mismatch`: 96%

解释：承上启下叶族字段非常稳定。它不是只看上文或只看下文，而是要求前后双向成立，因此 `bidirectional_validation=high` 是最关键字段。

### 4.4 中间-承上

蒸馏结果：

```yaml
blank_position: middle
function_type: carry_previous
logic_relation: continuation
context_dependency: medium
bidirectional_validation: backward_high_forward_low
semantic_scope: local
reference_dependency: medium
abstraction_level: medium
uniqueness_source:
  - function_mismatch
  - reference_failure
  - scope_mismatch
correct_answer_shape: original_sentence_or_clause
distractor_modes:
  - weak_backward_link
  - topic_shift
  - weak_forward_link
```

关键支持率：

- `blank_position=middle`: 100%
- `function_type=carry_previous`: 100%
- `context_dependency=medium`: 100%
- `bidirectional_validation=backward_high_forward_low`: 100%
- `semantic_scope=local`: 100%
- `reference_dependency=medium`: 100%
- `logic_relation=continuation`: 62.5%

解释：承上叶族样本只有 8 题，因此不能过度定论。但它已经能蒸出一个清晰方向：重心在承接前文，后文约束弱于承上启下。

## 5. 与现有题卡字段的关系

现有 `sentence_fill` 标准题卡的核心字段包括：

- `blank_position`
- `function_type`
- `logic_relation`
- `context_dependency`
- `bidirectional_validation`
- `reference_dependency`
- `semantic_scope`
- `abstraction_level`
- `distractor_modes`
- `uniqueness_source`

本次四个叶族包基本能把这些字段自动蒸出来。

尤其强的字段：

| 字段 | 是否可稳定蒸馏 | 说明 |
| --- | --- | --- |
| `blank_position` | 高 | 开头/中间/结尾几乎直接由叶族定义决定 |
| `function_type` | 高 | 概括后文、总结前文、承上启下、承上都能稳定映射 |
| `bidirectional_validation` | 高 | 语句填空的关键控制字段，尤其区分开头/结尾/桥接 |
| `semantic_scope` | 高 | 开头/结尾多为段落级，中间承上多为局部或句间级 |
| `uniqueness_source` | 中高 | 桥接类会自然引入 reference failure，概括类更偏 function/scope mismatch |
| `distractor_modes` | 中 | 能蒸出方向，但错项类型更依赖解析写法和选项设计 |

## 6. 对初始化问题的解释

语句填空的初始化字段可以这样解释：

```text
叶族名/题包来源
-> 空位位置
-> 空位功能
-> 上下文依赖方向
-> 语义作用范围
-> 错项失效机制
-> 题卡字段初始化
```

例如：

```text
横线在中间-承上启下
-> middle
-> bridge
-> bidirectional_validation=high
-> semantic_scope=sentence_level
-> uniqueness_source=function_mismatch/reference_failure/scope_mismatch
```

这解释了为什么 `sentence_fill` 题卡里必须有：

- `blank_position`
- `function_type`
- `logic_relation`
- `bidirectional_validation`
- `semantic_scope`

这些字段不是凭空想出来的，而是从叶族样本的稳定分布里自然长出来的。

## 7. 重要结论

### 7.1 语句填空比中心理解更适合自动蒸馏

中心理解的叶族常常是关系轴、主轴来源、错项机制混合；语句填空则天然有位置和功能，因此字段更容易稳定。

### 7.2 叶族包必须足够干净

前三个 50 题包支持率非常高。`中间-承上` 只有 8 题，虽然方向正确，但不足以直接固化为强字段。

建议阈值：

- `n >= 30` 且 `support_rate >= 0.80`：可固化为强叶族字段。
- `n < 30`：只能作为候选字段，需要补样本。
- `support_rate < 0.65`：说明叶族混杂或字段定义不够清楚。

### 7.3 “承上”和“承上启下”必须分开

本次结果显示：

- 承上启下：`bidirectional_validation=high`
- 承上：`bidirectional_validation=backward_high_forward_low`

这正好支持你把它们拆成不同叶族，而不是都归为“中间填空”。

## 8. 结论

这轮试验支持你的设想：

**语句填空可以通过干净叶族包复现题卡初始化字段，而且复现效果比中心理解更强。**

最强解释是：

> 语句填空的基础字段不是人拍脑袋定义的，而是由“空位位置 + 空位功能 + 上下文依赖方向”三件事共同逼出来的。

这可以作为初始化字段的工程解释。


# sentence_fill 叶族控制箱：横线在开头-话题引入

状态：historical draft / superseded by failed boundary
日期：2026-04-21
适用范围：`sentence_fill / 横线在开头-话题引入`
本轮定位：这是拟合前的控制箱草案，不是当前晋级结论。后续拟合结果已将该叶族降级为 `failed boundary / diagnostic reference`，不得再按 candidate 成果对外表述。

当前正式口径以以下文件为准：

- `docs/difficulty_journey_and_stage_results.md`
- `docs/difficulty_assets_closure.md`
- `docs/topic_intro_difficulty_failure_diagnosis.md`
- `reports/difficulty_control/topic_intro_control_box_test/topic_intro_control_box_fit_report.md`

审计结论：

```text
话题引入当前未过 promotion gate。
本文件只保留为“曾经尝试过哪些控制箱”的历史材料。
```

## 1. 为什么单独做这个叶族

`横线在开头-话题引入` 在前序实验里有两个明显特征：

- 全量结构轴容易低估它的真实难度。
- 人工阅读样本显示，难点常常不在“横线在开头”本身，而在引语、诗句、格言、价值判断和后文主旨之间的映射。

因此，这个叶族不适合继续只用 `global_context_dependency` 或 `blank_function_ambiguity` 描述。它需要自己的控制箱。

## 2. 外部研究给我们的启发

本轮外搜只用于启发控制箱，不直接作为权重证据。

- Cloze 题难度可以从 gap 和 distractor 两侧控制，尤其要控制干扰项有效性，不能只看空位本身。参考：[Controlling Cloze-test Question Item Difficulty with PLM-based Surrogate Models for IRT Assessment](https://arxiv.org/abs/2403.01456)。
- 阅读题难度预测可以从题目语言特征、测试特征、上下文特征共同建模，而不是只靠文本表层。参考：[Prediction of Item Difficulty for Reading Comprehension Items by Creation of Annotated Item Repository](https://arxiv.org/abs/2502.20663)。
- 语境填空/选择中，语义相关和语境相关的干扰项都会显著影响难度；对 gap-filling 题尤其要区分目标相关和上下文相关错项。参考：[Relationship between types of distractor and difficulty of multiple-choice vocabulary tests in sentential context](https://link.springer.com/article/10.1186/2229-0443-3-16)。
- Cloze 任务里，候选答案概率和语境约束都会影响反应时间；高约束语境会让答案更快浮现。参考：[The influence of cloze probability and item constraint on cloze task response time](https://www.sciencedirect.com/science/article/pii/S0749596X15000236)。
- 中文非字面表达的处理受熟悉度和语境共同影响；低熟悉表达更依赖从字面义推导隐喻义，高熟悉表达更容易直接激活隐喻义。参考：[The Roles of Familiarity and Context in Processing Chinese Xiehouyu](https://link.springer.com/article/10.1007/s10936-020-09753-0)。
- 中文成语/习语阅读理解中，字面义和真实语义不一致会造成理解挑战，近义关系可以缓解这种不一致。参考：[Synonym Knowledge Enhanced Reader for Chinese Idiom Reading Comprehension](https://arxiv.org/abs/2011.04499)。

## 3. 叶族核心机制

这个叶族的核心不是“开头”，而是：

```text
引入表达 -> 后文话题框架 -> 价值/论证方向
```

学生会错，通常不是因为没看后文，而是因为选项都像“能引入”，但只有一个能精确落到后文的价值方向。

## 4. 新控制箱

### 4.1 post_context_constraint_strength

定义：后文对开头引入句的约束强度。

易题画像：

- 后文连续复现同一关键词或同一语义场。
- 引入句和后文首句之间有直接复述关系。
- 错项很快被后文排除。

难题画像：

- 后文约束分散，需要读完整段才能确定。
- 后文先举例、再转入主旨，开头句需要提前概括。
- 多个选项都能解释一部分后文。

控制方式：

- `easy`：后文前 1-2 句给出强锚点。
- `medium`：后文需要整合 2-3 个语义锚点。
- `hard`：后文锚点分散，正确项要覆盖隐性话题框架。

### 4.2 quote_idiom_mapping_load

定义：引语、诗句、格言、成语从字面义到文段主旨的映射负荷。

易题画像：

- 引语本身高熟悉。
- 字面义和后文主题接近。
- 不需要额外文化背景。

难题画像：

- 引语/诗句有隐喻义或历史语境。
- 字面义会诱导错误方向。
- 后文主题和引语之间隔着抽象价值词，例如“革新、求索、更新、坚韧、顺势”。

控制方式：

- `easy`：使用高熟悉、强直译可解的表达。
- `medium`：表达熟悉，但需做一次价值抽象。
- `hard`：表达熟悉度或隐喻义不稳定，且错项也属于相近价值场。

### 4.3 value_direction_precision

定义：正确项的价值方向是否必须精确匹配后文。

常见价值方向：

- 更新/迭代
- 求索/探索
- 坚韧/奋斗
- 谨慎/反思
- 开放/包容
- 治理/规范

易题画像：

- 后文价值方向单一。
- 正确项和错项价值方向差异大。

难题画像：

- 多个选项都积极、宏大、正确。
- 错项只是价值方向偏一点，例如“求索” vs “更新”，“奋斗” vs “变革”。

控制方式：

- `easy`：错项价值方向明显不合。
- `medium`：错项同为积极价值，但行动方向不同。
- `hard`：错项与正确项同语域、同价值极性，只在时间方向、主体关系或论证重心上错位。

### 4.4 opening_register_competition

定义：选项作为开头句时的语域、气势、文风相似度。

易题画像：

- 只有正确项文风和后文一致。
- 错项过口语、过文学、过政策化或过空泛。

难题画像：

- 所有选项都像“适合放在开头”。
- 错项也具备题干要求的格言感、政策感、论述感。
- 学生会被“漂亮开头”吸引，而不是回到后文约束。

控制方式：

- `easy`：错项在语域上明显失配。
- `medium`：错项语域相近但主题偏。
- `hard`：错项语域、长度、句式都像正确项，只在主旨映射上错。

### 4.5 generic_positive_trap_strength

定义：错项是否是“听起来正确但不贴文段”的泛正向表达。

这个控制箱专门处理话题引入题里最常见的陷阱：选项都很好，但只有一个是这段话需要的好。

易题画像：

- 泛正向错项较少。
- 错项明显不贴后文关键词。

难题画像：

- 多个错项都是可宣传、可作文、可开头的表达。
- 错项价值正确但没有锁定后文主题。

控制方式：

- `easy`：最多 1 个泛正向错项。
- `medium`：2 个泛正向错项。
- `hard`：3 个错项都具有泛正向吸引力，其中 1 个和正确项价值方向非常接近。

## 5. 和既有四轴的关系

| 原轴 | 在本叶族中的改写 |
| --- | --- |
| `local_binding_complexity` | 弱化；改为开头表达与后文首个锚点的贴合。 |
| `global_context_dependency` | 改写为 `post_context_constraint_strength`，不再泛称全文依赖。 |
| `distractor_similarity` | 拆成 `opening_register_competition` 和 `generic_positive_trap_strength`。 |
| `blank_function_ambiguity` | 改写为引入功能类型：格言引入、现象引入、价值判断引入、论题框定。 |

## 6. Prompt 控制建议

生成时不要只说“生成一道话题引入题”。应显式选择控制箱：

```yaml
leaf_control_box:
  leaf_family: 横线在开头-话题引入
  post_context_constraint_strength: medium
  quote_idiom_mapping_load: hard
  value_direction_precision: hard
  opening_register_competition: medium
  generic_positive_trap_strength: hard
```

prompt 应要求：

- 先确定后文主旨的价值方向。
- 再选择或生成一个能精确映射该方向的开头表达。
- 干扰项必须同样像开头句，但分别错在价值方向、话题框架、语域或泛正向。
- 解析必须解释“为什么这个开头只适合这段话”，而不是只解释其他选项无关。

## 7. Validator 控制建议

validator 不应只检查答案是否合理，还应输出：

- `topic_frame_match`: 正确项是否覆盖后文话题框架。
- `value_direction_match`: 正确项价值方向是否精确。
- `quote_mapping_valid`: 引语/诗句/格言的隐喻义是否和后文一致。
- `generic_positive_distractor_count`: 泛正向错项数量。
- `near_miss_distractor`: 最强错项错在哪里。

## 8. Backtest 观察指标

下一轮标注不要一次上 40 个叶族维度。这个叶族先只标 5 个控制箱：

- `post_context_constraint_strength`
- `quote_idiom_mapping_load`
- `value_direction_precision`
- `opening_register_competition`
- `generic_positive_trap_strength`

建议最小样本：

- 本叶族不少于 30 道。
- 每个难度档不少于 8 道。
- 单独记录是否为诗句/成语/格言引入。

拟合判定：

- 若单叶族 5-fold Spearman > 0.45 且 MAE 低于叶族均值基线 0.03 以上，可以升格为正式 leaf axes。
- 若只在训练集提升，不进入正式协议，只保留为 prompt 诊断项。

## 9. 本轮结论

`横线在开头-话题引入` 最可能遗漏的不是一个单轴，而是一组控制箱：

```text
后文约束强度
引语/成语映射负荷
价值方向精度
开头语域竞争
泛正向陷阱强度
```

这组控制箱比此前的 `topic_entry_abstraction / quote_idiom_mapping / value_direction_precision` 更可执行，因为它们分别对应 prompt 生成、validator 检查和 backtest 标注字段。下一步应只围绕这个叶族扩大标注，而不是把所有叶族同时铺开。

# 话题引入难度拟合失败复盘与下一轮实验设计

状态：postmortem / next experiment design
日期：2026-04-21
范围：`sentence_fill / 横线在开头-话题引入`

## 1. 本轮失败说明了什么

前序实验连续测试了：

- 原结构四轴
- 全局经验轴
- 话题引入控制箱
- 正确项 vs 最大易错项 pairwise 轴
- 细胞层分类

结果均未稳定超过叶族均值基线。

这不应被解释为“话题引入没有难度机制”，而应解释为：**当前实验默认的难度机制太窄**。

当前默认假设是：

```text
难度 = 题内可观测结构信号 + 正确项/最大易错项的局部对抗
```

但 `话题引入` 的主导难度很可能来自更大的机制层：

```text
完整选项集竞争
考生先验熟悉度
认知任务类型
命题质量与措辞工程
```

## 2. 当前实验漏掉的层

### 2.1 完整选项集竞争

当前 pairwise 实验只看：

```text
正确项 vs 最大易错项
```

但学生实际面对的是四选一竞争场。

可能存在：

- 多个错项互相分流，导致单个易错项不代表真实竞争。
- 三个错项共同形成伪主题，压缩正确项可见度。
- 错项之间互补，分别覆盖后文的不同局部证据。
- 正确项单看不弱，但放在完整选项集中显得“不够像答案”。

下一轮应新增的选项集层字段：

- `distractor_cluster_coherence`：三个错项是否共享同一个伪主题。
- `distractor_complementarity`：三个错项是否分别命中不同局部证据。
- `correct_option_visibility_in_set`：正确项在四个选项中是否显眼。
- `correct_option_crowding_pressure`：错项群是否共同挤压正确项。
- `option_set_decoy_balance`：错项之间是否均衡，还是只有一个强错项。

### 2.2 解析易错项不等于真实误选分布

目前的 `easy_wrong_option` 来自解析文本，可能代表：

- 教辅作者认为最值得讲的错项。
- 命题解析中最有解释价值的错项。
- 某种教学口径，而非真实学生误选分布。

因此，基于 `correct vs easy_wrong` 的标注可能拟合的是：

```text
讲解层显著性
```

而不是真正的：

```text
作答层分流机制
```

下一轮如果没有完整选项分布，就必须把 `easy_wrong_option` 降级为弱参考，不再当作唯一竞争对象。

### 2.3 考生先验熟悉度

`话题引入` 特别依赖题外先验：

- 诗句/格言/成语熟悉度
- 政策话语熟悉度
- 作文模板/备考表达暴露频率
- 社会议题背景知识
- 某类表达在特定年份是否常见

这些不是题内结构，也不是选项局部贴合度。

可标注代理字段：

- `expression_familiarity_proxy`：表达是否常见、常考、常作为作文/申论模板。
- `cultural_prior_dependency`：是否依赖文化典故或隐喻先验。
- `policy_register_familiarity`：是否依赖政策/治理话语熟悉度。
- `template_exposure_risk`：选项是否像常见备考模板表达。

注意：这些只能作为代理，不是真实学生先验。最终最好接入语料频率或历史题库曝光度。

### 2.4 识别难度 vs 下定决心难度

有些题不是“看不出正确方向”，而是“看出方向但不敢选”。

当前轴多在测：

```text
识别难度
```

但 `话题引入` 还需要测：

```text
选择置信度难度
```

可标注字段：

- `correct_option_selectability`：正确项是否让考生敢选。
- `correct_option_understatement`：正确项是否过于克制、平淡、保守。
- `distractor_answer_likeness`：错项是否更像标准答案口吻。
- `confidence_gap_correct_vs_decoy`：正确项和最强错项在“像答案”程度上的差距。

### 2.5 选项集风格工程

当前只有语义/语域轴，但没有把命题表面工程单独建层。

可标注字段：

- `option_length_balance`：四个选项长度是否均衡。
- `option_syntactic_completeness_balance`：四个选项语法完成度是否均衡。
- `standard_answer_tone_trap`：错项是否更像标准答案语气。
- `correct_option_surface_plainness`：正确项是否太平、太不显眼。
- `rhetorical_polish_competition`：错项是否因更有气势而吸引考生。

### 2.6 认知任务类型，而不是素材表面类型

此前 cell 层按素材拆：

- 诗句/成语引入
- 普通话题句引入
- 价值判断引入
- 案例/现象引入

但这不一定是真难度层。

下一轮应按认知动作拆：

- `theme_naming`：主题命名型，看后文到底谈什么。
- `stance_setting`：立场定调型，给后文价值方向铺底。
- `rhetorical_mapping`：修辞映射型，把诗句/成语和具体话题对上。
- `abstraction_induction`：抽象归纳型，把后文若干现象抽成总开头。
- `discourse_launching`：语篇启动型，只需自然起句，不是严格语义归纳。

### 2.7 年份/地区/命题口径漂移

49 道题可能不是同一分布。

潜在漂移包括：

- 年份不同
- 地区/卷系不同
- 正确率口径不同
- 学生群体不同
- 命题风格不同
- 训练暴露程度不同

如果题包可以解析 `所属试卷`，下一轮应至少输出：

- `exam_source`
- `year`
- `province_or_exam_line`
- `source_style_hint`

即使不入模，也应在报告中按来源切片。

### 2.8 题目质量与难度混杂

低正确率不一定等于好题难。

可能是：

- 正确项不够自然
- 错项太脏或太强
- 证据不稳定
- 解析牵强
- 多个选项都可辩护

可标注字段：

- `answer_key_stability`
- `explanation_force`
- `option_balance_quality`
- `ambiguity_risk`
- `quality_adjusted_difficulty_flag`

这层必须和难度分开，否则会把“题质不稳”误当作“高难”。

### 2.9 正确项的“不过度”机制

话题引入题里，正确项常常不是最亮眼，而是最稳。

需要建模：

- 不过度
- 不抢结论
- 不越位
- 不装腔
- 不提前价值定性

可标注字段：

- `correct_option_non_overclaim_fit`
- `distractor_overclaim_strength`
- `premature_conclusion_trap`
- `too_polished_to_be_correct_trap`

## 3. 下一轮不要继续加宏观轴

下一轮不建议继续扩展“话题引入控制箱”。

应该改成三层实验：

```text
完整选项集竞争层
认知任务类型层
题质/表面工程层
```

并只保留少量字段，避免 49 道样本打 40 个维度。

## 4. 推荐下一轮最小实验

### 4.1 标注字段

只标 12 个字段：

完整选项集竞争：

- `distractor_cluster_coherence`
- `distractor_complementarity`
- `correct_option_visibility_in_set`
- `correct_option_crowding_pressure`

认知任务类型：

- `primary_cognitive_task`
- `cognitive_task_purity`

选择置信度：

- `correct_option_selectability`
- `distractor_answer_likeness`

题质/表面工程：

- `answer_key_stability`
- `option_balance_quality`
- `correct_option_non_overclaim_fit`
- `distractor_overclaim_strength`

### 4.2 模型比较

必须比较：

- 叶族均值基线
- 选项集竞争层
- 认知任务均值基线
- 选择置信度层
- 题质层
- 组合模型

### 4.3 升格门槛

进入正式协议前必须满足：

- 5-fold MAE 比叶族均值基线降低至少 `0.025`
- 5-fold Spearman 至少 `0.25`
- 至少两个 fold 指标方向一致
- 不能只靠 `answer_key_stability` 提升，否则说明是在识别题质，而不是难度

## 5. 本轮架构结论

`话题引入` 的失败不是坏结果，它把问题边界推清楚了：

```text
母族 = 协议层
叶族 = 功能层
细胞层 = 未必是难度层
真正的难度层可能是：
  选项集竞争
  考生先验
  认知任务
  题质/措辞工程
```

下一次尝试如果还做 `话题引入`，必须从“完整选项集竞争 + 选择置信度 + 题质剥离”开始，而不是继续添加语义匹配轴。

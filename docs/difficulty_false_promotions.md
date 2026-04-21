# 难度控制失败库 / 防误升格清单

状态：active guardrail
日期：2026-04-21

## 目的

记录哪些路线不能被包装成正式难度控制，防止交接后误用。

## 1. sentence_fill 全局结构轴

现象：

- 结构轴有解释价值，但全局拟合弱。
- 不同叶族机制混在一起后，结构信号被抵消。

风险：

- 把全局结构分数误当成全题型难度控制。

处置：

- 保留为 baseline 和诊断项。
- 不升格为正式难度权重。

## 2. sentence_fill / 话题引入

现象：

- 最优模型为 `mapping_type_mean`，CV Spearman 约 `0.2215`。
- 多轮细化后，精细轴没有稳定提升。
- pairwise、细胞层、选项集风格层均没有形成强拟合。

核心判断：

```text
话题引入的难度不主要来自表面结构，而来自总领命题对位、考生先验、引句映射和选项寄生竞争。
```

风险：

- 把“话题引入控制箱”误认为已可正式控制难度。

处置：

- 保留为失败边界案例。
- 可作为后续探索对象，但不得进入正式权重。

## 3. center_understanding / 主题词

现象：

- pairwise 轴有轻信号。
- 但 CV 增益不稳定。

风险：

- 因为与 `程度词` 同属中心理解，就直接复用 `local_detail_distractor_strength`。

处置：

- 只能重新建叶族实验。
- 优先测 `decisive_evidence_visibility_load` 和 `exclusion_reasoning_load`。

## 4. sentence_order / 4句、7句

现象：

- 当前结构轴、句数、order_type、正确序列与易错序列距离均未稳定打过均值基线。

风险：

- 因为排序题看起来“结构化”，就认为它天然容易控制难度。

处置：

- 暂不作为 demo 主样板。
- 后续如果扩样，应重新定义排序叶族，不要沿用当前轴。

## 5. all_reading_axes 堆变量

现象：

- 在 `center_understanding / degree_word` 中，`all_reading_axes` 组级消融反而低于均值基线。

风险：

- 以为变量越多越高级。

处置：

- demo 中只保留主旋钮和 guardrail。
- 弱轴只能进诊断，不进 projection。

## 防误升格检查

升格前必须回答：

- 是否落到叶族？
- 是否有隐藏真值？
- 是否打过叶族均值基线？
- 是否做过 repeated CV？
- 是否做过消融？
- 是否可被 prompt 控制？
- 是否可被 validator 复查？
- 是否有失败边界？
- 是否只是 candidate，而被讲成 formal？

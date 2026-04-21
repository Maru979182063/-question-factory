# center_understanding 叶族控制箱：程度词

状态：candidate protocol
日期：2026-04-21
适用范围：`center_understanding / 程度词`
本轮定位：把难度控制落到叶族层，形成可量化、可投影、可进入 prompt / validator 的最小控制箱；不自动回写主配置。

## 1. 为什么选这个叶族

这轮对 `中心理解题` 与 `语句排序题` 做了隐藏正确率实验。结论是：

- `sentence_order / 特殊题型-4句、7句` 没有跑出稳定控制信号，均值基线仍然最强。
- `center_understanding` 全局有弱信号，但合并 `主题词` 和 `程度词` 后会被压平。
- `center_understanding / 程度词` 内，`local_detail_distractor_strength` 与真实难度的训练内 Spearman 为 `0.3709`，5-fold CV Spearman 为 `0.2204`，相对叶族均值基线 MAE 增益为 `0.0152`。

因此它不能被包装成“强拟合完成”，但可以作为 demo 里的 leaf-level candidate control box：有实际作用潜质，映射也足够简单。

## 2. 核心判断

`程度词` 题不是单纯考“主题词是否出现”，而是在考：

```text
文段主次/范围/程度判断
→ 正确项是否覆盖中心
→ 易错项是否抓住局部细节但越位成主旨
```

学生掉坑的主要机制不是“完全没读懂”，而是把局部有效信息误判成全文中心。

## 2.1 相关性与拟合过程补充

完整统计报告见：

`reports/difficulty_control/highfit_probe/degree_word_correlation_analysis.md`

本轮补做了三类检验：

- 单轴相关性：Spearman / Pearson / 置换检验 / Bootstrap 置信区间。
- 多重比较控制：Benjamini-Hochberg q 值。
- 重复 5-fold CV：200 次随机分折，观察 MAE 增益和 CV Spearman。

纳入的特征不只包括选项，也包括：

- 文段侧：`main_claim_visibility`、`discourse_turn_complexity`、`scope_degree_decision_load`
- 正确项侧：`correct_option_abstraction_gap`
- 选项集侧：`option_competition_density`、`theme_term_overlap_trap`
- 易错项侧：`local_detail_distractor_strength`
- pairwise 侧：`decisive_evidence_visibility_load`、`exclusion_reasoning_load`、`easy_wrong_main_claim_proximity` 等
- 文本辅助项：篇幅、分句数、选项长度差等

关键结果：

| 特征 | 类型 | Spearman | perm_p | BH q | 重复 CV MAE 增益 |
| --- | --- | ---: | ---: | ---: | ---: |
| `local_detail_distractor_strength` | 易错项/局部细节 | 0.3709 | 0.0047 | 0.0855 | 0.0133 |
| `decisive_evidence_visibility_load` | pairwise/决胜证据 | 0.2132 | 0.1352 | 0.7555 | 0.0023 |
| `exclusion_reasoning_load` | pairwise/排除负荷 | 0.1970 | 0.1685 | 0.7555 | 0.0017 |
| `easy_wrong_main_claim_proximity` | pairwise/主旨接近 | 0.1798 | 0.2069 | 0.7555 | -0.0004 |
| `correct_option_abstraction_gap` | 正确项/抽象差距 | 0.1518 | 0.2967 | 0.7555 | -0.0032 |
| `discourse_turn_complexity` | 文段/行文转折 | 0.0878 | 0.5374 | 0.7555 | -0.0031 |

组级消融结果：

| 模型组 | 特征数 | 重复 CV MAE 增益 | CV Spearman 均值 |
| --- | ---: | ---: | ---: |
| `distractor_primary` | 1 | 0.0132 | 0.2253 |
| `candidate_control_index` | 3 | 0.0051 | 0.2105 |
| `passage_only` | 3 | -0.0074 | -0.2027 |
| `pairwise_only` | 5 | -0.0108 | -0.1298 |
| `all_reading_axes` | 12 | -0.0245 | 0.0663 |

解释：

- 不是没有测文段项；文段项在当前 50 道样本里没有稳定战胜均值基线。
- 也不是 pairwise 完全无用；它们更适合 hard guardrail，而不是主投影轴。
- 真正有叶族控制潜质的是 `local_detail_distractor_strength`，因为它同时满足方向一致、单轴可解释、重复 CV 有正增益、prompt/validator 容易落地。
- 多重比较校正后 q 值仍未低于 0.05，所以本协议保持 `candidate`，不升格为正式权重。

## 3. 最小控制轴

### 3.1 local_detail_distractor_strength

定义：易错项是否抓住原文局部细节、例子、原因、结果、补充说明中的真实内容，并因此具有表面合理性。

这是本叶族当前主轴。

分值画像：

| 分值 | 控制含义 | 样本数 | 真实平均难度 |
| --- | --- | ---: | ---: |
| 1 | 易错项明显不是中心，只是弱相关或偏离 | 7 | 0.1716 |
| 2 | 易错项有局部依据，但比较容易被主旨排除 | 26 | 0.3348 |
| 3 | 易错项局部依据较强，容易和中心混淆 | 16 | 0.3814 |
| 4 | 易错项几乎可以作为局部小结，必须靠主次判断排除 | 1 | 0.8345 |

控制建议：

- `easy`：目标分值 `1`。
- `medium`：目标分值 `2`。
- `hard`：目标分值 `3`，并叠加至少一个 pairwise guardrail。

### 3.2 decisive_evidence_visibility_load

定义：排除易错项、确认正确项的决胜证据是否隐藏在转折、尾句、程度词、主次关系或跨句综合中。

用途：hard guardrail，不单独作为主轴。

经验观察：

- 分值 `5` 时，样本平均难度为 `0.5363`。
- `local_detail >= 2 and decisive_evidence >= 5` 的命中样本平均难度为 `0.5363`，高于其余样本 `0.3195`。

### 3.3 easy_wrong_main_claim_proximity

定义：易错项距离文段真正中心/意图的接近程度。

用途：hard guardrail。

经验观察：

- 分值 `5` 时，样本平均难度为 `0.5658`。
- 适合和 `local_detail_distractor_strength >= 3` 组合使用。

### 3.4 exclusion_reasoning_load

定义：排除易错项需要几步推理，是否必须先识别主旨、再区分局部信息和中心信息。

用途：validator 诊断轴。

经验观察：

- 分值 `5` 时，样本平均难度为 `0.5050`。
- 单独拟合不如 `local_detail_distractor_strength` 稳，但适合解释“为什么学生会错”。

## 4. 控制投影

建议先使用三档 leaf projection，不上复杂模型：

```text
control_index =
  0.58 * local_detail_distractor_strength
  + 0.22 * decisive_evidence_visibility_load
  + 0.20 * easy_wrong_main_claim_proximity
```

经验分箱：

| control_index | 控制档 | 样本数 | 真实平均难度 |
| ---: | --- | ---: | ---: |
| < 2.45 | easy-control | 21 | 0.2655 |
| 2.45 - 3.45 | medium-control | 24 | 0.3476 |
| >= 3.45 | hard-control | 5 | 0.5847 |

这个分箱不是最终难度曲线，但已经能作为 demo 级控制映射：easy/medium/hard 有可解释的方向差异，且 hard 档明显抬升。

## 5. Prompt 消费方式

生成 `center_understanding / 程度词` 时，不要只要求“生成一道中心理解题”。应显式给出：

```yaml
leaf_control_box:
  family: center_understanding
  leaf_family: degree_word
  target_band: hard
  local_detail_distractor_strength: 3
  decisive_evidence_visibility_load: 4
  easy_wrong_main_claim_proximity: 4
```

prompt 应要求：

- 正确项必须覆盖全文中心、主次关系或作者意图。
- 至少一个易错项必须取自原文真实局部信息，但不能覆盖全文中心。
- hard 档必须让易错项“局部正确”，而不是无中生有。
- 解析必须说明易错项为什么只是局部、次要、范围偏小或程度不当。

## 6. Validator 消费方式

validator 不只检查答案是否正确，还应输出：

- `local_detail_distractor_strength`
- `decisive_evidence_visibility_load`
- `easy_wrong_main_claim_proximity`
- `exclusion_reasoning_load`
- `degree_scope_gap`
- `actual_leaf_control_band`

最低可接受判定：

- easy 题不得出现 `local_detail_distractor_strength >= 3`。
- hard 题必须满足 `local_detail_distractor_strength >= 3`，并且 `decisive_evidence_visibility_load >= 4` 或 `easy_wrong_main_claim_proximity >= 4`。
- 若 hard 题只靠无中生有、绝对化、主题词缺失制造难度，判为 invalid hard。

## 7. 本轮不能夸大的地方

这组控制箱还不是正式强拟合：

- 样本只有 50 道。
- hard 档样本偏少。
- CV Spearman 仍未达到 `0.25` 候选门槛。
- 它适用于 `中心理解-程度词`，不能平移成中心理解全局规则。

交付口径应为：

```text
本 demo 已具备叶族级难度控制候选能力。
当前最可靠控制旋钮是“局部细节错项强度”。
它已显示出与真实学生正确率一致的方向性，但仍需扩大样本后再升级为正式权重。
```

## 8. 后续升级路径

1. 扩大 `中心理解-程度词` 样本到至少 120 道。
2. hard 档至少补到 30 道，避免当前 hard 分箱样本过少。
3. 标注时只保留 4 个轴，避免弱轴污染拟合。
4. 若 repeated CV Spearman 稳定超过 `0.30` 且 MAE 增益超过 `0.025`，可升级为正式 leaf difficulty protocol。
5. 再平移到 `中心理解-主题词`，但主题词优先测试 `decisive_evidence_visibility_load` 和 `exclusion_reasoning_load`，不要直接复用程度词主轴。

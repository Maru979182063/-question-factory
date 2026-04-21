# Technical Appendix：degree_word 高密图

状态：appendix only
日期：2026-04-21
用途：给内行审查 degree_word 的数据证据，不作为首页叙事主图。

## 1. 相关性热力图

![degree_word correlation heatmap](../reports/difficulty_control/degree_word_leaf_experiment_report/assets/degree_word_correlation_heatmap.svg)

最短说明：

```text
这张图用于检查变量之间是否互相替代，避免把一组高度同质的弱轴误写成多个独立控制旋钮。
```

当前主轴 `local_detail_distractor_strength` 的单轴结果：

| 指标 | 数值 |
| --- | ---: |
| Spearman | `0.3709` |
| Pearson | `0.3947` |
| permutation p | `0.0047` |
| BH q | `0.0855` |

## 2. 控制分箱 / 难度带分离图

![degree_word control bins](../reports/difficulty_control/degree_word_leaf_experiment_report/assets/degree_word_control_bins.svg)

最短说明：

```text
hard-control 的平均真实难度已抬高到 0.5847，但当前 hard 样本只有 5 道，只能说明 hard 档有形状，不能说明曲线已经稳定。
```

| band | n | mean actual difficulty |
| --- | ---: | ---: |
| `easy_control` | `21` | `0.2655` |
| `medium_control` | `24` | `0.3476` |
| `hard_control` | `5` | `0.5847` |

## 3. CV 消融图

![degree_word CV ablation](../reports/difficulty_control/degree_word_leaf_experiment_report/assets/degree_word_cv_ablation.svg)

最短说明：

```text
单轴 distractor_primary 最稳；变量堆叠没有自然变好，反而显示过拟合风险。
```

| model | CV MAE | MAE gain | CV Spearman |
| --- | ---: | ---: | ---: |
| `distractor_primary` | `0.1570` | `0.0132` | `0.2253` |
| `candidate_control_index` | `0.1651` | `0.0051` | `0.2105` |
| `all_reading_axes` | `0.1947` | `-0.0245` | `0.0663` |

## 4. 附录结论

```text
degree_word 的证据形态是 candidate_only：
有方向、有分箱、有 CV 正增益；
但样本数、hard 档数量、BH q 和 MAE gain 都还不支持 formal_weight。
```

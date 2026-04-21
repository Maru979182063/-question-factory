# 难度实验工作台与后续接手说明

状态：handoff guide
日期：2026-04-21
对象：后续接手难度资产、复现报告、整理最终 docx 的同事。

## 0. 一句话说明

`difficulty_experiment_workbench` 是叶族难度控制证据链工作台，不是线上训练系统，也不是正式难度总线。

## 1. 先看哪些文件

最短阅读顺序：

1. `docs/difficulty_journey_and_stage_results.md`
2. `docs/difficulty_assets_closure.md`
3. `docs/difficulty_workbench_and_next_steps.md`
4. `docs/difficulty_degree_word_technical_appendix.md`
5. `reports/difficulty_control/degree_word_leaf_experiment_report/degree_word_leaf_experiment_report.md`
6. `reports/difficulty_control/topic_intro_control_box_test/topic_intro_control_box_fit_report.md`
7. `configs/difficulty_experiments/center_understanding_degree_word.json`

辅助文件：

- `docs/leaf_control_box_center_understanding_degree_word.md`
- `docs/topic_intro_difficulty_failure_diagnosis.md`
- `prompt_skeleton_service/configs/prompt_assets/leaf_control_box_center_understanding_degree_word.yaml`
- `reports/difficulty_control/candidate_diffs/center_understanding_degree_word_candidate_diff.md`

## 2. 最短复现命令

先看状态：

```powershell
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage status
```

校验标注：

```powershell
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage validate
```

重跑分析：

```powershell
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage analyze
```

重跑报告：

```powershell
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage report
```

生成候选 diff：

```powershell
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage candidate-diff
```

注意：

```text
candidate-diff 只生成审计用候选 diff，不自动修改主配置。
```

## 3. 本轮已核验结果

| stage | 实测结果 |
| --- | --- |
| `status` | 可运行，expected outputs 均存在 |
| `validate` | `ok: true`，7 份标注输出 schema error 均为 `0` |
| `analyze` | 可运行，returncode `0` |
| `report` | 可运行，返回叶族报告路径 |
| `candidate-diff` | 可运行，输出 candidate diff 路径 |

## 4. 演示顺序

5 分钟演示时按这个顺序打开：

1. `docs/difficulty_journey_and_stage_results.md`
2. `docs/difficulty_three_layer_map.svg`
3. `docs/difficulty_promotion_ladder.svg`
4. `docs/difficulty_baseline_vs_result.svg`
5. `docs/difficulty_degree_word_technical_appendix.md`

推荐讲法：

```text
这不是正式全题型难度权重，而是一套叶族难度控制证据链。
degree_word 是 candidate 成果，topic_intro 是 failed boundary，workbench 用于复现、校验、报告和生成候选 diff。
```

## 5. 不要乱做什么

不要：

- 不要把 candidate YAML 自动写回主配置。
- 不要把 `degree_word` 写成 formal weight。
- 不要把 `topic_intro` 包装成成功叶族。
- 不要把 workbench 写成线上自动学习平台。
- 不要只看训练集指标，必须看 repeated CV、消融和分箱。
- 不要在封板包里继续新增叶族实验。

可以：

- 可以复跑 `status / validate / analyze / report / candidate-diff`。
- 可以把三份主文档和三张主图交给写作者整理最终报告。
- 可以把 technical appendix 作为内行审查页，不放到首页抢叙事。

## 6. 下一阶段优先级

如果后续继续推进，建议按这个顺序：

1. 扩 `center_understanding / degree_word` 样本到 `120`。
2. 补 hard-control 样本到 `30`。
3. 保持主轴收敛，不继续堆弱轴。
4. 用生成样本验证 prompt / validator / diff report 是否真的吃到 `local_detail_distractor_strength`。
5. 再考虑迁移到其他中心理解叶族，且必须重新过同样证据链。

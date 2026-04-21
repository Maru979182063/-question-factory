# Difficulty Experiment Configs

这个目录放叶族难度实验配置。

当前样板：

- `center_understanding_degree_word.json`

模板：

- `template_leaf_experiment.json`

常用命令：

```powershell
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage status
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage validate
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage all --dry-run
python scripts\difficulty_experiment_workbench.py --config configs\difficulty_experiments\center_understanding_degree_word.json --stage candidate-diff
```

交接文档：

- `docs/difficulty_workbench_handoff.md`
- `docs/difficulty_workbench_quickstart.md`
- `docs/difficulty_control_executive_overview.md`
- `docs/difficulty_experiment_workbench_tooling.md`

注意：

- 配置只编排实验，不代表实验结论已晋级。
- `candidate_only` 不允许自动回写主配置。
- 标注输出必须先通过 `validate`，再运行 `analyze` 和 `report`。

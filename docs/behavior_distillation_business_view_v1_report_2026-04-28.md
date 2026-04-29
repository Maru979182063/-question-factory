# behavior_distillation_business_view_v1 执行报告

## 1. 修改文件列表

- `prompt_skeleton_service/app/demo_static/distill_demo.html`
- `prompt_skeleton_service/app/demo_static/distill_demo.js`
- `prompt_skeleton_service/tests/test_demo_shell.py`
- `tools/leaf_pre_distill/behavior_distillation_business_summary.py`
- `tools/leaf_pre_distill/report_renderer.py`
- `tools/leaf_pre_distill/run.py`
- `tests/test_leaf_pre_distill.py`
- `docs/behavior_distillation_business_view_v1_report_2026-04-28.md`

## 2. 业务视图新增内容

新增默认展示的“业务视图：本阶段叶族问题与沉淀建议”。它复用 `behavior_distillation_business_summary.json`，把工程字段翻译成业务可读内容，不默认展示 JSON。

业务视图改为分页展示：

- 第 1 页：当前阶段与叶族。
- 第 2 页：动作与高频问题，展示哪个叶族、哪些题或哪些字段被统一修改，并把动作推断成问题小条目。
- 第 3 页：蒸馏后结果，展示建议沉淀什么、进入哪类资产、风险和证据缺口。
- 第 4 页：前后题目对比，展示旧历史题目与蒸馏后结果，并标红/标绿差异。
- 第 5 页：当前是否可以落位。

前端文案明确说明：这里不是前端现场一秒蒸馏，而是读取已经完成的行为蒸馏结果并渲染业务视图。

新增可选 artifacts：

- `behavior_distillation_business_view.json`
- `behavior_distillation_business_view_report.md`

两者保持 `formalized=false`、`writeback_allowed=false`、`executor_allowed=false`。

## 3. 四个业务核心块如何展示

### 当前阶段 / 叶族

展示当前阶段、叶族或 run 标识、样本数、审核数、修改数、沉淀包数和整体状态。业务文案解释当前处于 proto trial / review / packet / readiness 等阶段。

### 高频问题抽象

把高频修改字段、失败模式和用户反馈合并翻译成问题名称、业务解释、证据来源、支持强度和当前建议。字段名只放入技术详情。

动作层新增：

- `action_clusters`: 记录叶族、集中修改字段、影响题目、动作类型和重复动作。
- `action_problem_items`: 一个问题一个小条目，展示“动作依据 -> 业务判断 -> 当前建议”。

### 蒸馏后结果

把 candidate improvement signals 翻译成“系统建议沉淀什么、建议进入哪类资产、为什么、风险是什么、还缺什么证据”。技术枚举只放在折叠区。

### 前后题目对比

如果输入已有 before/after 对比，则展示同一材料参数、原题版本、修改后版本、修改字段、修改原因、validator 结果变化和人审结论变化。

### 是否落位

展示“能否落位、不能落位原因、下一步建议”。落位被定义为正式写回或正式启用配置；送审包只是 evidence；blocked 不等于失败。

## 4. before/after 数据是否已有

当前 behavior packet / summary 主结构未稳定提供完整 before/after 题目对比。前端和离线 view 都支持可选输入 before/after pairs，但不会伪造。

## 5. 缺哪些 evidence

缺少完整对比时记录：

- `missing_before_after_question_pair`
- `missing_same_material_parameter_trace`
- `missing_validator_before_after_result`

## 6. 技术详情如何折叠

前端把以下内容放入默认折叠的“技术详情”区域：

- `behavior_distillation_business_view.json`
- `behavior_distillation_business_view_report.md`
- `behavior_distillation_business_summary.json`
- `behavior_distillation_business_report.md`

业务视图默认只显示中文结论，不默认展示大 JSON。

## 7. 测试结果

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`: 98 tests OK.
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`: 15 tests OK.
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`: 10 tests OK.
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`: 4 tests OK.

补充检查：

- `python -m py_compile tools/leaf_pre_distill/behavior_distillation_business_summary.py tools/leaf_pre_distill/report_renderer.py tools/leaf_pre_distill/run.py`: OK.
- 静态边界检查：前端 JS 未出现 `writeback_allowed: true`、`formalized: true`、`executor_allowed: true`。

## 8. 明确没有做

- 没有正式写回。
- 没有 executor 调用。
- 没有 card_specs 写回。
- 没有 material_card 写回。
- 没有 prompt_assets 写回。
- 没有 runtime_mapping 写回。
- 没有 validator_contract 写回。
- 没有 generation / validator / prompt / runtime 主链修改。

# Sentence Order Variable Count 与 Difficulty Projection 隔离修复报告

日期：2026-04-27

## 本轮范围

本轮只执行两件事：

1. 将 `sentence_order` 从旧的 fixed-six 叙述统一为 4/5/6 variable-count contract。
2. 隔离 `difficulty_projection`，避免非 `sentence_fill` 题型继续注入 `sentence_fill` 专属 axis projection。

本轮没有做 validator hard/soft 大治理，没有恢复 `center_understanding` / `title_selection` / `sentence_fill` 专项 hard error，也没有改 input decoder、runtime mapping、新题包正式化工厂或材料线。

## 修改文件列表

- `prompt_skeleton_service/configs/types/sentence_order.yaml`
- `card_specs/normalized/question_cards/sentence_order_standard_question_card.normalized.yaml`
- `prompt_skeleton_service/app/services/question_validator.py`
- `prompt_skeleton_service/app/services/difficulty_projection_service.py`
- `prompt_skeleton_service/tests/test_sentence_order_schema.py`
- `prompt_skeleton_service/tests/test_slot_resolver.py`
- `prompt_skeleton_service/tests/test_question_validator.py`
- `docs/sentence_order_variable_count_and_difficulty_projection_fix_2026-04-27.md`

## Sentence Order 最终契约

当前统一为：

- `sentence_order` 支持 4 / 5 / 6 个排序单元。
- 每道题必须声明目标 `sortable_unit_count`。
- 允许值只能是 4、5、6。
- variable-count 不等于任意 count；缺失 declared count、声明值不在 4/5/6、材料/选项/答案链与声明 count 不一致，都会触发 `sentence_count_mismatch`。
- 不再把“所有非 6 句”视为天然错误；错误条件改为“与 declared count 不一致”。

## Config / Card / Note 修改

`prompt_skeleton_service/configs/types/sentence_order.yaml`：

- `formal_runtime_spec.sortable_unit_count.mode` 改为 `variable`。
- 增加 `allowed_values: [4, 5, 6]`。
- 增加 `requires_declared_count: true`。
- 增加 `reject_undeclared_unit_count: true` 和 `reject_count_mismatch: true`。
- `validator_contract.sentence_order` 增加：
  - `allowed_sortable_unit_counts: [4, 5, 6]`
  - `requires_declared_count: true`
  - `reject_count_mismatch: true`

`card_specs/normalized/question_cards/sentence_order_standard_question_card.normalized.yaml`：

- 同步改为 4/5/6 variable-count contract。
- 保留 `fixed_sortable_unit_count: null`。
- `allowed_sortable_unit_counts` 保持 4/5/6。
- 清理了会与当前契约冲突的 fixed-six note，改为 declared-count 一致性说明。

## Validator Count Consistency

`question_validator.py` 中的 sentence_order count 逻辑做了最小调整：

- 从以下来源读取 declared count：
  - `validator_contract.sortable_unit_count`
  - `validator_contract.sentence_order.sortable_unit_count`
  - `validator_contract.structure_constraints.sortable_unit_count`
  - `resolved_slots.sortable_unit_count`
  - `control_logic.sortable_unit_count`
  - `material_source.prompt_extras.sortable_unit_count`
- 默认 allowed count 为 `{4, 5, 6}`。
- 默认要求 declared count。
- `sentence_order_declared_unit_count` check 会记录 count / allowed / required / source。
- `generated_question.original_sentences` 不再被自动 normalize 成 6 个单元。
- material unit count 统计不再自动 merge 到 6。

这只是 count consistency 修复，没有改 `minimum compliance profile`，也没有扩大 sentence_order 其他 hard/soft 规则。

## Difficulty Projection 隔离

`difficulty_projection_service.py` 中：

- 只有 `question_type == "sentence_fill"` 时才调用 `_sentence_fill_axis_projection(...)`。
- 非 `sentence_fill` 题型的 `axis_projection` 为空 `{}`。
- 非 `sentence_fill` 的 `projection_method` 为 `pattern_rules_only`。
- `build_prompt_sections(...)` 不再默认读取 `sentence_fill` prompt lines，而是按当前 `question_type` 查找 family prompt lines。

结果：

- `sentence_fill` 仍保留 sentence_fill axis。
- `main_idea` / `center_understanding` / `sentence_order` / 其他题型不再套用 sentence_fill axis。

## 测试结果

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_sentence_order_schema
```

结果：`Ran 12 tests`，OK。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_slot_resolver
```

结果：`Ran 4 tests`，OK。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_validator
```

结果：`Ran 41 tests`，失败 22。

本轮相关收敛：

- sentence_order fixed-six / variable-count 相关失败已收敛。
- sentence_order contract source 断言已改为 declared-count 语义。
- 剩余 sentence_order 失败为 `test_sentence_order_natural_openers_get_opening_credit`，属于自然开头打分/marker 问题，不属于本轮 variable-count contract。

剩余未处理失败范围：

- `center_understanding` hard/soft boundary。
- `sentence_fill` bridge / countermeasure / function drift / original answer consistency。
- `continuation` prompt marker。
- `title_selection` card-specific checks。
- generic difficulty miss 当前仍在 warning/error 语义上漂移。

这些均留给下一轮 validator hard/soft 主权修复。

## 新工厂 Scoped 回归

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：`Ran 82 tests`，OK。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

结果：`Ran 11 tests`，OK。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

结果：`Ran 10 tests`，OK。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

结果：`Ran 4 tests`，OK。

## 明确未改范围

本轮未修改：

- validator hard/soft 大治理。
- `sentence_fill` validator 专项规则。
- `center_understanding` validator 专项规则。
- `title_selection` validator 专项规则。
- `input_decoder` / runtime mappings / question_card_binding supported set。
- 新题包正式化工厂。
- material line。
- prompt templates。
- formal writeback executor。

## 结论

本轮达成目标：

- `sentence_order` 不再被旧 fixed-six 测试拖回固定 6。
- config、normalized card、测试和 validator count consistency 已统一到 4/5/6 declared-count contract。
- `difficulty_projection` 不再把 `sentence_fill` axis 注入非 `sentence_fill` 题型。
- 新题包正式化工厂 scoped tests 仍然通过。

下一刀建议进入 validator hard/soft 主权修复，优先处理 `sentence_fill` 中文 marker / original answer consistency 与 `center_understanding` 专项错误是否应由 validator_contract 升为 hard error。

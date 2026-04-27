# Validator Marker / Fixture Cleanup Report - 2026-04-27

## Executive Summary

本轮只执行 `validator_marker_fixture_cleanup_v1` 的低风险清账：清理 `question_validator.py` 中明显不可读的中文 marker / mojibake token，并补充少量真实通用中文问法 marker。没有修改 validator hard/soft 主权、minimum compliance profile、HARD_ERROR_CODES、validator_contract、normalized cards、sentence_order 4/5/6 契约、difficulty projection、新题包正式化工厂或材料线。

结果：

- baseline `test_question_validator`：41 tests，22 failures。
- cleanup 后 `test_question_validator`：41 tests，15 failures。
- 新题包正式化工厂 scoped tests 仍通过。

本轮成功消除了“标准中文问法识别不到 / marker 乱码”导致的一批噪声；剩余失败主要属于 hard/soft boundary、validator_contract 主权、title/center 专项契约与 difficulty 旧预期，不在本轮修复范围内。

## Modified Files

- `prompt_skeleton_service/app/services/question_validator.py`
- `docs/validator_marker_fixture_cleanup_report_2026-04-27.md`

未修改测试 fixture。本轮检查到失败相关 fixture 中的中文样例本身可读，主要问题在 validator marker 侧。

## Baseline

Command:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_validator
```

Result:

- Ran 41 tests
- Failures: 22

Baseline 中明确属于 marker / mojibake 风险的失败包括：

- `test_sentence_fill_standard_prompt_is_recognized`
- `test_sentence_fill_requires_original_removed_sentence_when_flag_enabled`
- `test_sentence_fill_prefers_runtime_prompt_extras_over_source_analysis`
- `test_sentence_fill_validator_contract_overrides_source_analysis_without_runtime_extras`
- `test_continuation_exam_style_prompt_is_family_common_not_contract_driven`
- `test_sentence_order_natural_openers_get_opening_credit`
- `test_validator_adds_exam_style_and_material_warnings`

## Cleanup Details

### Sentence Fill Markers

Replaced unreadable `??` prompt and relation markers with conservative Chinese marker sets:

- Standard prompt phrases:
  - `填入画横线部分最恰当`
  - `填入文中横线处最恰当`
  - `填入横线处最恰当`
  - `填入空缺处最恰当`
  - `填入文中画横线处最恰当`
  - `句子填入文中横线处`
- Bridge / both-side reasoning:
  - `承上启下`
  - `承接前文`
  - `回应前文`
  - `照应前文`
  - `引出后文`
  - `引出下文`
  - `衔接上下文`
- Conclusion / countermeasure / backward / forward markers:
  - `因此` / `所以` / `总之` / `综上`
  - `应当` / `应该` / `必须` / `通过` / `完善`
  - `上述` / `前文` / `由此`
  - `接下来` / `下文` / `后文` / `将从`

### Continuation Markers

Replaced unreadable continuation prompt tokens with common continuation exam wording:

- `接下来最可能`
- `接下来可能`
- `下文最可能`
- `作者接下来`
- `接着最可能`
- `后文最可能`
- `接下来将`

### Common Exam / AI-Style Markers

Replaced mojibake meta-tone markers with readable markers:

- `ai生成`
- `chatgpt`
- `根据提供的材料生成`
- `请你选择正确答案`
- `正确答案是`
- `答案解析`
- `本题考查`

### Sentence Order Natural Opener Markers

Replaced unreadable role/opener markers with real Chinese structural markers and reordered `opening_anchor` recognition before broad action markers. This fixed natural opener recognition without changing sentence_order 4/5/6 count contract.

Examples:

- `如果说`
- `在《`
- `虽然`
- `随着`
- `近年来`
- `长期以来`

## Post-Cleanup Validator Result

Command:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_validator
```

Result:

- Ran 41 tests
- Failures: 15

Failures removed:

- `test_continuation_exam_style_prompt_is_family_common_not_contract_driven`
- `test_sentence_fill_prefers_runtime_prompt_extras_over_source_analysis`
- `test_sentence_fill_requires_original_removed_sentence_when_flag_enabled`
- `test_sentence_fill_standard_prompt_is_recognized`
- `test_sentence_fill_validator_contract_overrides_source_analysis_without_runtime_extras`
- `test_sentence_order_natural_openers_get_opening_credit`
- `test_validator_adds_exam_style_and_material_warnings`

## Remaining Failures

### Hard / Soft Boundary

These failures are still present because `_apply_minimum_compliance_profile` is converting the expected error codes into soft warnings or otherwise not treating them as hard. This is explicitly out of scope for the marker cleanup round.

- `test_sentence_fill_bridge_fails_when_only_one_side_holds`
- `test_sentence_fill_countermeasure_requires_specific_action`
- `test_sentence_fill_real_bridge_like_sample_rejects_one_sided_middle_option`
- `test_sentence_fill_runtime_function_drift_fails_for_ending_countermeasure`
- `test_sentence_fill_runtime_function_drift_fails_for_middle_lead_next`
- `test_sentence_fill_runtime_function_drift_fails_for_opening_topic_intro`
- `test_sentence_fill_rejects_paraphrase_when_original_answer_is_required`

### Center Understanding Validator Contract / Hard-Soft Boundary

These failures remain in the center-understanding lane. They need a dedicated `validator_contract_hard_soft_reconciliation` pass rather than marker cleanup.

- `test_center_understanding_turning_rejects_pre_transition_background`
- `test_center_understanding_cause_effect_rejects_single_cause_branch`
- `test_center_understanding_example_to_conclusion_rejects_example_as_main_idea`
- `test_center_understanding_final_summary_rejects_middle_local_point`
- `test_center_understanding_rejects_over_abstract_option`
- `test_center_understanding_runtime_contract_mismatch_fails_explicitly`

### Title Selection Contract / Card-Specific Checks

- `test_title_selection_contract_enables_card_specific_checks`

This appears to be a card-specific validator hard/soft issue or test expectation drift, not a marker recognition problem.

### Difficulty Review Old Expectation

- `test_validator_builds_difficulty_review`

This is related to the current business decision that difficulty should remain a weak signal / review reference instead of a hard control axis. It should be handled in a difficulty contract/test expectation reconciliation pass, not this marker cleanup.

## Scoped Regression

### Leaf Pre-Distill / New Factory

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

- Ran 82 tests
- OK

### Demo Shell

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

Result:

- Ran 11 tests
- OK

### Distill Workbench

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

Result:

- Ran 10 tests
- OK

### Word Usage Proto Mapping

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Result:

- Ran 4 tests
- OK

## Explicit Non-Changes

This round did not modify:

- minimum compliance profile
- HARD_ERROR_CODES
- validator_contract
- normalized cards
- sentence_order 4/5/6 declared-count contract
- difficulty_projection_service
- slot_resolver
- input_decoder
- question_card_binding
- runtime mapping
- prompt templates
- new leaf formalization factory
- material line
- formal writeback executor

## Next Recommended Knife

Next round should be:

`validator_contract_hard_soft_reconciliation_v1`

Recommended focus:

1. Decide which sentence_fill contract violations should remain soft warnings and which must be hard errors.
2. Reconcile center_understanding card-specific checks with validator_contract.
3. Reconcile title_selection card-specific checks.
4. Reconcile generic difficulty miss behavior after difficulty has been downgraded to weak review signal.
5. Avoid changing tests until the source of truth is explicitly settled.

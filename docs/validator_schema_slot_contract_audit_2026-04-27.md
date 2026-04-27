# Validator / Schema / Slot Resolver 契约漂移审计

日期：2026-04-27

## Executive Summary

本轮只做审计，未修改 validator、slot_resolver、sentence_order schema、normalized cards、runtime mapping、prompt templates、question_generation 或新题包正式化工厂逻辑。

当前 scoped tests 已经证明新题包正式化工厂工具层可运行；剩余失败集中在旧三大题型的契约边界：

- `test_question_validator`：41 个测试中 23 个失败。
- `test_sentence_order_schema`：12 个测试中 4 个失败。
- `test_slot_resolver`：4 个测试中 1 个失败。

总体判断：

- 工具层 evidence / packet / readiness gate 不被这些失败直接阻塞。
- runtime activation、formal writeback、旧三大题型封板前必须清理其中的高风险项。
- 不建议为了绿测试直接改断言，也不建议直接放宽 validator。当前失败混合了测试过期、配置漂移、实现漂移、历史硬编码和编码/fixture 质量问题。

## 测试命令与结果

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_validator
```

结果：`Ran 41 tests`，失败 23。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_sentence_order_schema
```

结果：`Ran 12 tests`，失败 4。

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_slot_resolver
```

结果：`Ran 4 tests`，失败 1。

## 当前剩余失败总览

| 测试文件 | 失败数 | 主要区域 | 初步结论 |
|---|---:|---|---|
| `prompt_skeleton_service/tests/test_question_validator.py` | 23 | validator、minimum compliance、中文 prompt marker、sentence_fill/center/title/sentence_order 专项规则 | 混合型漂移，不能机械修断言 |
| `prompt_skeleton_service/tests/test_sentence_order_schema.py` | 4 | sentence_order fixed six-unit contract | 配置/测试契约明显冲突 |
| `prompt_skeleton_service/tests/test_slot_resolver.py` | 1 | difficulty projection | 实现漂移，main_idea 被套用 sentence_fill axis projection |

## question_validator 失败逐项分类

### Center Understanding

失败测试：

- `test_center_understanding_cause_effect_rejects_single_cause_branch`
- `test_center_understanding_example_to_conclusion_rejects_example_as_main_idea`
- `test_center_understanding_final_summary_rejects_middle_local_point`
- `test_center_understanding_rejects_over_abstract_option`
- `test_center_understanding_runtime_contract_mismatch_fails_explicitly`
- `test_center_understanding_turning_rejects_pre_transition_background`

失败形态：期望 `local_point_as_main_axis`、`example_promoted_to_main_idea`、`abstraction_level_mismatch`、`argument_structure_mismatch`、`main_axis_mismatch` 出现在 `result.errors`，实际为空。

相关实现：

- `prompt_skeleton_service/app/services/question_validator.py:2019-2098` 仍有对应 error append 逻辑。
- `prompt_skeleton_service/app/services/question_validator.py:1239-1318` 会经过 `_apply_minimum_compliance_profile`，非 hard error 会降级成 warning。
- `HARD_ERROR_CODES` 目前只硬保留 `ordering_chain_incomplete`、`sentence_count_mismatch`、`binding_violation`、`reference_anchor_missing` 等少量错误。

分类：

```json
{
  "affected_area": "validator",
  "suspected_category": "implementation_drift",
  "risk_level": "high",
  "likely_fix_target": "validator_contract|implementation|test",
  "should_fix_now": false,
  "recommended_next_action": "先确认 center_understanding 专项错误是否应为 hard error；若是，应通过 validator_contract/minimum compliance profile 恢复硬门槛，而不是简单改测试。"
}
```

判断：这些失败会影响旧 `center_understanding` 质量封板，也会影响未来 formal runtime activation 中的 validator 契约可信度。它们不阻塞新题包送审包生成，但阻塞正式写回前的旧题型回归封板。

### Sentence Fill

失败测试：

- `test_sentence_fill_bridge_fails_when_only_one_side_holds`
- `test_sentence_fill_countermeasure_requires_specific_action`
- `test_sentence_fill_prefers_runtime_prompt_extras_over_source_analysis`
- `test_sentence_fill_real_bridge_like_sample_rejects_one_sided_middle_option`
- `test_sentence_fill_rejects_paraphrase_when_original_answer_is_required`
- `test_sentence_fill_requires_original_removed_sentence_when_flag_enabled`
- `test_sentence_fill_runtime_function_drift_fails_for_ending_countermeasure`
- `test_sentence_fill_runtime_function_drift_fails_for_middle_lead_next`
- `test_sentence_fill_runtime_function_drift_fails_for_opening_topic_intro`
- `test_sentence_fill_standard_prompt_is_recognized`
- `test_sentence_fill_validator_contract_overrides_source_analysis_without_runtime_extras`

失败形态：

- 多个测试期望 `position_function_mismatch` / `bidirectional_failure` / `sentence_fill_material_question_consistency_fail` 出现在 `errors`，实际为空或被其他更硬错误替代。
- prompt marker / bridge marker 检测处出现 mojibake 风险，例如 `_validate_sentence_fill` 中 `fill_prompt_markers` 和 bridge analysis marker 多处为乱码 token。

相关实现：

- `prompt_skeleton_service/app/services/question_validator.py:2917` 追加 `sentence_fill_material_question_consistency_fail`。
- `prompt_skeleton_service/app/services/question_validator.py:3152-3302` 追加 `position_function_mismatch` / `bidirectional_failure`。
- `prompt_skeleton_service/app/services/sentence_fill_protocol.py` 仍保留 canonical triad：`blank_position`、`function_type`、`logic_relation`，并在 strict export 中阻断未知 alias。
- `card_specs/normalized/question_cards/sentence_fill_standard_question_card.normalized.yaml` 已声明 canonical triad 与 legacy aliases。

分类：

```json
{
  "affected_area": "validator",
  "suspected_category": "implementation_drift|hardcoded_rule_risk",
  "risk_level": "high",
  "source_of_truth_to_check": "sentence_fill normalized card + sentence_fill_protocol + validator_contract",
  "likely_fix_target": "validator implementation first, then tests only after contract confirmed",
  "should_fix_now": false,
  "recommended_next_action": "先审定 sentence_fill 专项错误是否应绕过 minimum compliance 降级；同时清理中文 marker mojibake，确保标准问法/桥接/对策检测能被真实中文触发。"
}
```

判断：`sentence_fill` canonical triad 仍在，但 validator 内部中文 marker 和 minimum-compliance 降级让测试无法确认硬门槛。这个区域会阻塞旧 `sentence_fill` 正式封板，也会影响未来新题型 validator_contract 写回的可信度。

### Sentence Order Validator

失败测试：

- `test_sentence_order_natural_openers_get_opening_credit`
- `test_sentence_order_prefers_generated_original_sentences_for_runtime_material`

失败形态：

- opener score 中 `ifengshuo` 与 dependent 均为 `0.32`，自然开头没有获得预期加分。
- runtime material source 选择期望 `generated_question.original_sentences`，实际优先用了 `material_source.prompt_extras.sortable_units`。

相关实现：

- `prompt_skeleton_service/app/services/question_validator.py:2144` 明确可能返回 `material_source.prompt_extras.sortable_units`。
- `prompt_skeleton_service/app/services/question_validator.py:2334-2454` 做 sentence_order count/order/alignment 检查。

分类：

```json
{
  "affected_area": "validator|runtime_material_resolution",
  "suspected_category": "test_outdated|implementation_drift",
  "risk_level": "medium",
  "likely_fix_target": "manual_decision",
  "should_fix_now": false,
  "recommended_next_action": "先确认 runtime material 主权：prompt_extras.sortable_units 是否应优先于 generated original_sentences。若 prompt_extras 是材料卡/runtime 输出，应改测试；若 generated_question 才是 gold source，应改 resolver。"
}
```

判断：这不是单纯断言错，涉及运行时材料来源主权。要先定 contract。

### Title Selection / Main Idea Common

失败测试：

- `test_title_selection_contract_enables_card_specific_checks`
- `test_validator_adds_exam_style_and_material_warnings`
- `test_validator_builds_difficulty_review`

失败形态：

- title_selection 长标题规则未进入 errors。
- meta/AI-style phrasing、weak lexical overlap warning 未触发。
- difficulty review 存在，但测试期待 generic difficulty warning 在 errors；当前实现把 difficulty miss 放入 warnings，且 `_apply_minimum_compliance_profile` 不会把它变成 hard error。

相关实现：

- `prompt_skeleton_service/app/services/question_validator.py:1219-1237` difficulty miss 统一 append 到 warnings。
- `prompt_skeleton_service/app/services/question_validator.py:1239-1318` minimum compliance profile 进一步降级非 hard errors。
- `card_specs/normalized/question_cards/title_selection_standard_question_card.normalized.yaml` 已有独立 validator_contract。

分类：

```json
{
  "affected_area": "validator",
  "suspected_category": "test_outdated|implementation_drift",
  "risk_level": "medium",
  "likely_fix_target": "validator_contract|test",
  "should_fix_now": false,
  "recommended_next_action": "明确 title_selection 的长标题/材料贴合是否是 hard error；明确 difficulty miss 在 validator 中是 warning 还是 error。"
}
```

判断：difficulty miss 当前更像设计变更后测试旧了；title_selection 则需要看 card-specific checks 是否被 contract 正确激活。

### Continuation

失败测试：

- `test_continuation_exam_style_prompt_is_family_common_not_contract_driven`

失败形态：标准追问样式未识别。

相关实现：

- `prompt_skeleton_service/app/services/question_validator.py:2111-2123` 的 continuation markers 当前显示为乱码 token。

分类：

```json
{
  "affected_area": "validator",
  "suspected_category": "implementation_drift|fixture_encoding_risk",
  "risk_level": "medium",
  "likely_fix_target": "implementation",
  "should_fix_now": false,
  "recommended_next_action": "单独清理中文 prompt marker 编码，不应放宽 continuation validator。"
}
```

## sentence_order_schema 失败逐项分类

### 固定六句契约冲突

失败测试：

- `test_type_config_fixed_sortable_unit_count_is_six`
- `test_normalized_question_card_carries_six_unit_contract`

失败形态：测试期待：

```yaml
sortable_unit_count:
    mode: fixed
    value: 6
reject_non_six_unit_sequences: true
allowed:
  - 6
fixed_sortable_unit_count: 6
```

当前配置实际为：

- `prompt_skeleton_service/configs/types/sentence_order.yaml:22-30`：`value: null`，`reject_non_six_unit_sequences: false`
- `prompt_skeleton_service/configs/types/sentence_order.yaml:111-119`：slot allowed 为 `4, 5, 6`
- `prompt_skeleton_service/configs/types/sentence_order.yaml:328`：validator_contract `sortable_unit_count: null`
- `card_specs/normalized/question_cards/sentence_order_standard_question_card.normalized.yaml:23-31`：`value: null`，`reject_non_six_unit_sequences: false`
- `card_specs/normalized/question_cards/sentence_order_standard_question_card.normalized.yaml:172-180`：`fixed_sortable_unit_count: null`，allowed `4,5,6`

但同一 normalized card 的 notes/extension_rules 又仍写着“fixed six-sentence runtime spec”以及六句必须失败的描述。

分类：

```json
{
  "affected_area": "sentence_order_schema|normalized_card|validator_contract",
  "suspected_category": "config_drift",
  "risk_level": "critical",
  "source_of_truth_to_check": "产品契约：sentence_order 是否已从固定六句升级为 4/5/6 变体，还是配置误改",
  "likely_fix_target": "normalized_card|type_config|test",
  "should_fix_now": false,
  "recommended_next_action": "先人工决定 sentence_order 正式 runtime 是否固定六句；决定前不要改测试或配置。"
}
```

判断：这是当前最明确的契约冲突。测试、配置、card note 三者不一致。

### Enforcement error 被 ordering_chain_incomplete 覆盖

失败测试：

- `test_sortable_unit_count_mismatch_for_five_and_seven_units`
- `test_role_order_conflict_for_conclusion_in_middle`

失败形态：

- 期望 `sentence_count_mismatch`，实际 `ordering_chain_incomplete`。
- 期望 `role_order_conflict`，实际 `ordering_chain_incomplete`。

相关实现：

- `prompt_skeleton_service/app/services/question_validator.py:2414-2454` 只有在 `expected_sortable_unit_count` 存在时才对 5/7 触发 `sentence_count_mismatch`；当前 contract count 为 null。
- `prompt_skeleton_service/app/services/question_validator.py:2798` 有 `role_order_conflict`，但前序 ordering checks 已先失败。

分类：

```json
{
  "affected_area": "sentence_order_schema|validator",
  "suspected_category": "config_drift|behavior_drift",
  "risk_level": "high",
  "likely_fix_target": "normalized_card|validator_contract first, implementation second",
  "should_fix_now": false,
  "recommended_next_action": "先修或重定 fixed six-unit contract；再判断 role_order_conflict 是否应作为并列 error 保留，而不是被 ordering_chain_incomplete 吞没。"
}
```

## slot_resolver 失败分类

失败测试：

- `test_difficulty_projection_does_not_add_target_bias`

失败形态：同一 config、同一 pattern、同一 slots，仅 difficulty_target 从 easy 到 hard，`difficulty_projection.model_dump()` 不同。

实际差异摘要：

- easy：`target_difficulty=easy`，`axis_projection` 为 sentence_fill easy 轴。
- hard：`target_difficulty=hard`，`axis_projection` 为 sentence_fill hard 轴。
- 但测试 config 的 `question_type` 是 `main_idea`。

相关实现：

- `prompt_skeleton_service/app/services/slot_resolver.py:91-96` 调用 `DifficultyProjectionService.project(...)`。
- `prompt_skeleton_service/app/services/difficulty_projection_service.py:150-156` 无条件调用 `_sentence_fill_axis_projection(...)`。
- `prompt_skeleton_service/app/services/difficulty_projection_service.py:190-232` 为 sentence_fill 专用轴投影。

分类：

```json
{
  "affected_area": "slot_resolver|difficulty_projection",
  "suspected_category": "implementation_drift",
  "risk_level": "high",
  "old_expectation": "slot_resolver 不因 difficulty_target 注入目标偏置 slot/projection，至少非 sentence_fill 不应获得 sentence_fill axis。",
  "current_behavior": "main_idea projection 被写入 sentence_fill axis_projection，并随 easy/hard 改变。",
  "source_of_truth_to_check": "difficulty_control_prompt_assets + question_type_config.difficulty_target_profiles",
  "likely_fix_target": "difficulty_projection_service",
  "should_fix_now": false,
  "recommended_next_action": "下一刀单独修：只有 sentence_fill 使用 sentence_fill axis projection；其他题型需要题型专属轴或空 axis_projection。"
}
```

判断：这是实现漂移，不应通过测试断言放宽解决。它会污染 runtime_activation_plan 对 difficulty / projection 的可信判断。

## 历史硬编码风险扫描结果

### family / subtype 硬编码

已发现合法但需治理的硬编码集中点：

- `prompt_skeleton_service/app/services/input_decoder.py` 中 `QUESTION_FOCUS_MAPPING`、`BUSINESS_SUBTYPE_MAPPING`、`SPECIAL_TYPE_MAPPING`、`SPECIAL_TYPE_ALIASES`、`SUPPORTED_RUNTIME_TARGETS`。
- `prompt_skeleton_service/app/services/question_card_binding.py` 中 `SUPPORTED_RUNTIME_BINDINGS`。
- `prompt_skeleton_service/app/services/question_generation.py` 中 word_usage proto route 常量和专用 `_generate_word_usage_proto_batch`。
- `prompt_skeleton_service/app/services/distillation_runtime_service.py` 当前仍显式限制 distillation runtime 只支持 `sentence_fill`。

风险判断：

- input decoder / card binding 的 supported set 是当前三卡模式保护，不是 bug，但会阻塞新题包 formal runtime activation，必须在 runtime_activation_plan/writeback 之后受控扩展。
- word_usage proto route 有显式 `experimental_proto_route=true` guard，当前是受控实验入口；不能视为正式支持。
- distillation_runtime_service 只支持 sentence_fill 是历史能力边界，新 formalization packet 不应把它说成通用蒸馏 runtime。

### alias 硬编码

已发现：

- `input_decoder.py` 存在 `title_selection`、`center_understanding`、sentence_order/sentence_fill pattern aliases。
- `sentence_fill_protocol.py` 通过 config 的 `legacy_slot_mapping` 做 strict export alias 映射，未知 alias 会 blocked。
- `sentence_order_protocol.py` 对 candidate/opening/closing aliases 有 strict mapping，未知/ambiguous 值会 blocked。

风险判断：

- export protocol 的 alias 映射相对安全，因为有 blocked path。
- input_decoder 的 alias 是路由层硬编码，必须避免继续扩散；新题型应通过 runtime_activation_plan 后再进入受控 mapping。
- 未发现 unknown subtype 静默 fallback；`InputDecoderService` 对 unknown focus/subtype 会抛 `DomainError`。

### sentence_order 六句约束

当前状态：

- schema / normalized card 多处从 fixed six 改成 `null` 或 `4/5/6`。
- validator 可在 contract 给出 `sortable_unit_count=6` 时 enforce 六句。
- normalized card 的 notes 仍声称 fixed six。
- source analyzer 中仍有六句倾向逻辑，例如 `source_question_analyzer.py` 设置/合并 `sortable_unit_count=6`。

判断：六句约束当前不是稳定统一契约，而是“部分配置放开、部分说明仍固定、validator 可按 contract enforce”。这是高风险配置漂移。

### sentence_fill canonical triad

当前状态：

- `blank_position`、`function_type`、`logic_relation` 仍是 normalized card 和 `sentence_fill_protocol.py` 的 canonical triad。
- export gate 对未知 canonical / alias 有 blocked path。
- validator 内部有大量业务检测，但部分 error 被 minimum compliance profile 降级或中文 marker 未触发。

判断：canonical triad 仍在，问题主要是 validator hard/soft boundary 和 marker 编码。

### validator 主权

当前状态：

- validator 读取 `validator_contract`、`material_source.prompt_extras`、`resolved_slots`、`control_logic`。
- 仍有大量服务内题型规则，包括 center_understanding、sentence_fill、sentence_order 的硬编码文本/marker/heuristic。
- `_apply_minimum_compliance_profile` 以服务内 `HARD_ERROR_CODES` 决定哪些 error 仍为 hard。

风险：validator_contract 不是唯一主权来源；服务内 minimum compliance profile 可能覆盖 card/contract 的硬门槛表达。正式写回前应治理。

### slot_resolver 主权

当前状态：

- slot_resolver 严格校验 unknown slots，不会自己创造 type_slots。
- business_subtype 未匹配会抛 `DomainError`。
- 但 difficulty projection service 会对非 sentence_fill 注入 sentence_fill axis projection。

风险：slot_resolver 本身 slot 主权尚可，difficulty projection 存在跨题型污染。

## 题卡主权 / validator_contract / runtime_binding 对齐情况

已对齐的部分：

- `question_card_binding.py` 只加载 supported runtime bindings。
- explicit unknown `question_card_id` 会报错。
- unsupported runtime binding 会 unresolved 或报错，不会自动塞入旧母族。
- sentence_fill/sentence_order strict export protocol 都有 blocked path。

未对齐或漂移的部分：

- sentence_order card/config 对六句契约不一致。
- validator 的 hard/soft boundary 由服务内 `HARD_ERROR_CODES` 控制，未完全由 validator_contract 控制。
- difficulty projection 的 axis projection 与 question_type 不匹配。
- input_decoder / question_card_binding 的 supported set 尚未与新 formalization packet 的 runtime activation 输出连接。

## 对旧三大题型的影响

### sentence_fill

影响等级：高。

原因：canonical triad 在，但 validator hard/soft 边界、中文 prompt marker、bridge/countermeasure/function drift 检测不稳定。正式封板前必须修。

### sentence_order

影响等级：关键。

原因：六句契约存在配置级冲突。必须先定“固定六句”还是“4/5/6 变体”，否则 validator/schema/test 无法统一。

### center_understanding / title_selection

影响等级：高。

原因：center 专项错误不再作为 hard errors 暴露；title_selection card-specific check 是否启用存在漂移。会影响导出和旧题型质量回归。

## 对新题包正式化工厂的影响

| 新工厂环节 | 是否被当前失败阻塞 | 说明 |
|---|---|---|
| `agent_review_feedback` | 否 | 工具层 evidence，不依赖旧 validator。 |
| `new_leaf_formalization_packet` | 否 | 送审包可记录这些 validator/schema 风险为 blockers。 |
| `material_protocol_draft` | 否 | 材料线草案不依赖旧三题型 validator 绿灯。 |
| `runtime_activation_plan` | 部分阻塞 | 计划可生成，但正式激活前必须解决 runtime binding / validator / difficulty projection 高风险项。 |
| `formalization_readiness_gate` | 不阻塞运行，但应给 blocked/review_needed | readiness gate 应把这些作为旧题型污染风险和 runtime activation blocker。 |
| 未来 executor / formal writeback | 阻塞 | 正式写回前必须通过旧三大题型回归和新题型 proto/formal 回归。 |

结论：当前失败不阻塞“送审包工厂”的演示闭环，但阻塞“正式 runtime activation + writeback executor”。

## 推荐修复顺序

### 第一刀：低风险测试期望 / fixture / 编码清账

目标：只处理明显测试过期或 fixture 编码问题，不改业务逻辑。

建议范围：

- 修复 continuation / sentence_fill / center_understanding 测试 fixture 中可能的中文 mojibake 输入。
- 明确 difficulty miss 当前应在 warnings 还是 errors；若设计已变成 warning，则只改对应测试。
- 跑：
  - `test_question_validator`
  - `test_prompt_builder`
  - `test_question_generation`

### 第二刀：sentence_order 六句契约决策与配置修复

目标：先定契约，再改配置或测试。

两条可能路线：

- 路线 A：正式恢复固定六句。改 `sentence_order.yaml`、normalized card、validator_contract，使 `sortable_unit_count=6`，allowed 只保留 6，`reject_non_six_unit_sequences=true`。
- 路线 B：正式支持 4/5/6。改测试与 card notes，明确 `sentence_count_mismatch` 语义从“must equal 6”变成“must match source/contract”。

跑：

- `test_sentence_order_schema`
- `test_question_validator`
- `test_question_generation`

### 第三刀：validator hard/soft 主权修复

目标：让 validator_contract 决定哪些专项错误是 hard，不由服务内最小合规 profile 吞掉关键错误。

建议范围：

- center_understanding 专项错误 hard/soft 定义。
- sentence_fill `position_function_mismatch` / `bidirectional_failure` / material consistency 是否 hard。
- title_selection card-specific checks 是否应 hard。

跑：

- `test_question_validator`
- `test_review_workbench`
- `test_distill_workbench`

### 第四刀：difficulty projection 跨题型污染修复

目标：修复 `DifficultyProjectionService` 对非 sentence_fill 使用 sentence_fill axis projection 的问题。

建议：

- 仅 `question_type == "sentence_fill"` 时调用 `_sentence_fill_axis_projection`。
- 其他题型使用题型专属 axis 或空 projection，并保留 metric projection。

跑：

- `test_slot_resolver`
- difficulty/projection/backtest 相关测试
- `test_question_generation`

### 第五刀：历史硬编码治理

目标：把路由/alias/service 内规则逐步迁回 card/config/contract，不一口气大改。

优先顺序：

1. input_decoder / question_card_binding supported set 与 runtime_activation_plan 对接。
2. sentence_fill / sentence_order alias 继续保持 strict blocked path。
3. word_usage proto route 只在 formalization 后迁移为配置化 mapping。

跑：

- `test_word_usage_proto_mapping`
- `test_distill_workbench`
- `test_demo_shell`
- 旧三大题型全套 scoped tests。

## 哪些地方不能机械修改

- 不能为了 `test_sentence_order_schema` 绿灯直接把 six-unit 改回 6，除非产品契约确认固定六句。
- 不能为了 `test_question_validator` 绿灯把所有专项 error 加入 `HARD_ERROR_CODES`，否则会破坏 minimum compliance 设计。
- 不能为了 `test_slot_resolver` 绿灯删除 difficulty projection；应按题型隔离 projection。
- 不能把 unknown subtype/focus 做静默 fallback。
- 不能把 word_usage proto route 加入正式 supported set，除非 runtime_activation_plan、readiness gate、writeback plan 全部通过。

## 本轮未改动声明

本轮只新增审计文档：

- `docs/validator_schema_slot_contract_audit_2026-04-27.md`

未修改：

- `prompt_skeleton_service/app/services/question_validator.py`
- `prompt_skeleton_service/app/services/slot_resolver.py`
- `prompt_skeleton_service/app/services/difficulty_projection_service.py`
- `prompt_skeleton_service/configs/types/sentence_order.yaml`
- `card_specs/normalized/question_cards/*.yaml`
- `prompt_skeleton_service/app/services/question_generation.py`
- runtime mapping / prompt templates / validator contracts
- 新题包正式化工厂逻辑

## 最终结论

剩余失败已经不是 few-shot、路径、MaterialBridgeV2 签名这类环境噪声，而是旧题型契约漂移的真实信号。

最关键的两个 blocker：

1. `sentence_order` 六句契约在测试、配置、normalized card、note 中互相矛盾。
2. `difficulty_projection_service` 对非 sentence_fill 注入 sentence_fill axis projection。

最需要谨慎处理的是 validator hard/soft boundary：当前 validator 不是“没有规则”，而是规则可能被 minimum compliance profile 降级，或者被中文 marker/fixture 编码问题绕开。下一步应按分刀修，不应为了短期全绿牺牲题卡协议主权。

# 三题卡蒸馏 Casebook

一张卡只挑一个最小闭环 case。这里不把候选资产写成正式配置，也不把 behavior 当成 truth。

## Case 1：`sentence_fill` middle bridge

| 环节 | 证据 |
| --- | --- |
| 输入包 | `reports/distillation_runtime/round1/distillation_input_packet.json`，family 为 `sentence_fill`，包含 truth sample、历史线程摘要、测试快照、四类 runtime snapshot |
| truth distillation 产物 | `reports/distillation_runtime/round1/distillation_result_packet.json`，输出 4 个维度：`local_binding_complexity`、`global_context_dependency`、`distractor_similarity`、`blank_function_ambiguity`；生成 16 个 candidate patches |
| behavior distillation 产物 | `prompt_skeleton_service/app/services/distillation_behavior_service.py` 可从 `question_item_versions` / `question_review_actions` / `question_usage_events` 生成 behavior packet；`prompt_skeleton_service/tests/test_distillation_behavior_service.py` 有合成历史样本验证；当前无充分证据显示 `reports/` 下已有 sentence_fill behavior packet 落盘样例 |
| diff report 指向 | `reports/distillation_runtime/round1/distillation_diff_report.json`；`reports/distillation_runtime/round1/distillation_diff_report.md`，`overall_fit_status=poor`，16 个 patch diff 分布在四类 target |
| promotion bundle 留下了什么 | `reports/distillation_runtime/round1/distillation_promotion_bundle.json`，`bundle_mode=candidate_only`，按 `question_card` / `prompt_assets` / `validator_contract` / `material_mapping` 分组 |
| 当前结论 | 这是当前唯一证据完整的新结构化 runtime 闭环；所有 patch 仍是 candidate-only |

## Case 2：`center_understanding` / `main_idea`

| 环节 | 证据 |
| --- | --- |
| 输入包 | `reports/truth_distillation_assets_center_understanding_2026-04-14.csv`，50 条真题抽取；`reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv`，12 条结构 few-shot 候选 |
| truth distillation 产物 | `reports/center_understanding_truth_blueprint_2026-04-14.md`；`reports/center_understanding_truth_round1_pack_2026-04-14.md`；`reports/center_understanding_truth_round1_results_2026-04-14.csv`，5 条 round1 结果 |
| behavior distillation 产物 | 当前无充分证据显示已有 `center_understanding` 专属 behavior packet / behavior report 落盘；只有通用 behavior service 能按 `question_card_id` 或 `question_type` 抽取 |
| diff report 指向 | 当前无充分证据显示已有新结构化 `DistillationDiffReport` 样式的 `center_understanding` diff report；已有 `reports/round1_fewshot_generation_regression_report_2026-04-12.md` 证明 few-shot 被真实 prompt 路径命中 9/9 |
| promotion bundle 留下了什么 | 当前无充分证据显示已有 `center_understanding` 的结构化 promotion bundle；batch 层有 `reports/distill_batches/center_understanding_*/question_card_draft.yaml`、`prompt_draft.md`、`material_card_draft.yaml` 等候选资产 |
| 当前结论 | 题卡和 prompt 确有蒸馏证据，且 few-shot/guard 已进主生成 runtime；但新 runtime packet/diff/promotion 闭环还未覆盖这张卡 |

## Case 3：`sentence_order`

| 环节 | 证据 |
| --- | --- |
| 输入包 | `reports/truth_distillation_assets_sentence_order_2026-04-14.csv`，50 条真题抽取；`reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv`，10 条结构 few-shot 候选 |
| truth distillation 产物 | `reports/sentence_order_truth_blueprint_2026-04-14.md`；`reports/sentence_order_truth_round1_pack_2026-04-14.md`；`reports/sentence_order_truth_round1_results_2026-04-14.csv`，5 条 round1 结果 |
| behavior distillation 产物 | 当前无充分证据显示已有 `sentence_order` 专属 behavior packet / behavior report 落盘；只有通用 behavior service 能按历史表抽取 |
| diff report 指向 | 当前无充分证据显示已有新结构化 `DistillationDiffReport` 样式的 `sentence_order` diff report；已有 `reports/round1_fewshot_generation_regression_report_2026-04-12.md` 证明 few-shot 被真实 prompt 路径命中 8/8 |
| promotion bundle 留下了什么 | 当前无充分证据显示已有 `sentence_order` 的结构化 promotion bundle；batch 层有 `reports/distill_batches/sentence_order_*/question_card_draft.yaml`、`prompt_draft.md`、`material_card_draft.yaml` 等候选资产 |
| 当前结论 | 题卡和 prompt 确有蒸馏证据，且 few-shot/guard 已进主生成 runtime；但新 runtime packet/diff/promotion 闭环还未覆盖这张卡 |

## Casebook 边界

- `sentence_fill`：有完整结构化离线闭环。
- `center_understanding`：有真题资产、few-shot 资产、batch 候选资产和主 prompt 消费证据；没有新结构化 promotion bundle 证据。
- `sentence_order`：有真题资产、few-shot 资产、batch 候选资产和主 prompt 消费证据；没有新结构化 promotion bundle 证据。

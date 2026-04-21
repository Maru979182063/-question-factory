# 题卡与提示词蒸馏资产索引

本索引只收证据和资产，不扩展新蒸馏设计。状态口径：

- `diagnostic`：诊断、审计、真题抽取、实验记录类资产。
- `candidate`：候选题卡、候选 prompt、候选材料映射、候选 patch。
- `consumed in runtime`：已经被当前服务代码读取或进入真实 prompt/generation 路径。
- `candidate-only not consumed`：仅作为候选包、报告、hint 留存，未自动回写主配置。

## 三个题卡证据

| 题卡 | 当前实际卡/配置 | 蒸馏证据 | 状态 |
| --- | --- | --- | --- |
| `center_understanding` / `main_idea` | `card_specs/normalized/question_cards/center_understanding_standard_question_card.normalized.yaml`；`prompt_skeleton_service/configs/types/main_idea.yaml` | `reports/truth_distillation_assets_center_understanding_2026-04-14.csv`，50 条真题结构字段；`reports/center_understanding_truth_blueprint_2026-04-14.md`；`reports/center_understanding_truth_round1_pack_2026-04-14.md`；`reports/center_understanding_truth_round1_results_2026-04-14.csv`，5 条 round1 运行结果；`reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv`，12 条 few-shot 候选 | `diagnostic` + `candidate` + 部分 `consumed in runtime` |
| `sentence_fill` | `card_specs/normalized/question_cards/sentence_fill_standard_question_card.normalized.yaml`；`prompt_skeleton_service/configs/types/sentence_fill.yaml` | `reports/truth_distillation_assets_sentence_fill_2026-04-14.csv`，50 条真题结构字段；`reports/sentence_fill_truth_blueprint_2026-04-14.md`；`reports/sentence_fill_truth_round3_pack_2026-04-14.md`；`reports/sentence_fill_truth_round3_results_2026-04-14.csv`，5 条 round3 运行结果；`reports/round1_fewshot_sentence_fill_candidates_2026-04-12.csv`，12 条 few-shot 候选；`reports/distillation_runtime/round1/distillation_result_packet.json`，16 个结构化 candidate patches | `diagnostic` + `candidate` + `consumed in runtime` + `candidate-only not consumed` |
| `sentence_order` | `card_specs/normalized/question_cards/sentence_order_standard_question_card.normalized.yaml`；`prompt_skeleton_service/configs/types/sentence_order.yaml` | `reports/truth_distillation_assets_sentence_order_2026-04-14.csv`，50 条真题结构字段；`reports/sentence_order_truth_blueprint_2026-04-14.md`；`reports/sentence_order_truth_round1_pack_2026-04-14.md`；`reports/sentence_order_truth_round1_results_2026-04-14.csv`，5 条 round1 运行结果；`reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv`，10 条 few-shot 候选 | `diagnostic` + `candidate` + 部分 `consumed in runtime` |

## 提示词蒸馏资产

| 资产 | 路径 | 留下了什么 | 当前状态 |
| --- | --- | --- | --- |
| 新蒸馏 runtime prompt assets | `prompt_skeleton_service/configs/prompt_assets/truth_distillation_prompt_assets.yaml` | `sentence_fill` 四个难度维度、四类 patch target、under/over target blueprint、candidate patch policy | `consumed in runtime`，由 `prompt_skeleton_service/app/services/distillation_runtime_service.py` 读取 |
| 主生成链路 prompt assets | `prompt_skeleton_service/configs/question_generation_prompt_assets.yaml` | `round1_fewshot_assets` 三卡 pack 配置；`fewshot_prompt_guards` 三卡提示词守卫；analysis contract / answer grounding / reference constraints | `consumed in runtime`，由 `prompt_skeleton_service/app/services/question_generation_prompt_assets.py` 与 `prompt_skeleton_service/app/services/prompt_builder.py` 读取 |
| round1 few-shot 候选 | `reports/round1_fewshot_sentence_fill_candidates_2026-04-12.csv`；`reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv`；`reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv` | 结构型 few-shot 候选样本，分别覆盖 `sentence_fill` 12 条、`center_understanding` 12 条、`sentence_order` 10 条 | `consumed in runtime`，开启 `use_fewshot` 且 `fewshot_mode=structure_only` 时可进入 prompt |
| leaf/batch prompt 草稿 | `reports/distill_batches/*/prompt_draft.md`；`reports/distill_batches/*/distill_pack_*.md` | 子卡/叶子维度的 prompt 草稿、蒸馏包、手工审计记录 | `candidate`，未见证据表明被统一自动写回主 prompt assets |
| behavior prompt/hint 逻辑 | `prompt_skeleton_service/app/services/distillation_behavior_service.py` | 从历史版本、review action、download/use event 生成 behavior candidate patch hints | `candidate-only not consumed`，可通过 API/UI 生成，但当前未发现落盘样例报告 |

## 结构化运行层样例

| 样例 | 路径 | 说明 | 当前状态 |
| --- | --- | --- | --- |
| 输入包 | `reports/distillation_runtime/round1/distillation_input_packet.json` | `sentence_fill` truth sample / 历史线程摘要 / 测试结果 / runtime snapshot | `diagnostic` |
| 结果包 | `reports/distillation_runtime/round1/distillation_result_packet.json` | 4 个难度维度、`overall_fit_status=poor`、16 个 candidate patches | `candidate-only not consumed` |
| diff report | `reports/distillation_runtime/round1/distillation_diff_report.json`；`reports/distillation_runtime/round1/distillation_diff_report.md` | target/actual 难度差、patch diff、测试摘要 | `diagnostic` + `candidate-only not consumed` |
| promotion bundle | `reports/distillation_runtime/round1/distillation_promotion_bundle.json` | `bundle_mode=candidate_only`，按四类 patch target 分组 | `candidate-only not consumed` |

## 证据缺口

- 当前结构化 `distillation_input_packet -> result_packet -> diff_report -> promotion_bundle` 样例只覆盖 `sentence_fill`，未发现同格式的 `center_understanding` 或 `sentence_order` runtime packet 样例。
- `behavior_distillation` 有服务、API、前端和测试，但当前未发现 `reports/` 下的 behavior packet / behavior report 落盘样例。
- 三卡的 leaf/batch 蒸馏资产很多，但多数是 `candidate` 或 `diagnostic`，不能写成已回写正式题卡。

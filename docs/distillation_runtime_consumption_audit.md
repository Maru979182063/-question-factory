# 蒸馏结果运行层消费审计

本审计只回答“哪些蒸馏结果真的被运行层消费了”。候选 patch 是否存在，不等于已消费。

## 已被消费的落点

| 消费点 | 代码/配置落点 | 消费内容 | 说明 |
| --- | --- | --- | --- |
| truth distillation prompt assets | `prompt_skeleton_service/app/services/distillation_runtime_service.py` -> `load_truth_distillation_prompt_assets()`；`prompt_skeleton_service/configs/prompt_assets/truth_distillation_prompt_assets.yaml` | `sentence_fill` 四维难度定义、patch target、patch blueprints、guardrails | 新蒸馏 runtime 真实读取该 YAML，并用 blueprint 生成 candidate patches |
| structured result packet | `prompt_skeleton_service/app/services/distillation_runtime_service.py` -> `build_result_packet()`；`prompt_skeleton_service/app/schemas/distillation.py` | `DistillationInputPacket` -> `DistillationResultPacket` | 当前只支持 `sentence_fill` |
| diff report | `prompt_skeleton_service/app/services/distillation_diff_service.py` | `difficulty_fit`、`candidate_patches`、test snapshot | 消费 result packet 生成结构化 diff report 和 markdown |
| promotion bundle | `prompt_skeleton_service/app/services/distillation_promotion_service.py` | `candidate_patches` 按 target 分组 | 消费 result packet，但只产出 `candidate_only` bundle，不回写主配置 |
| round1 few-shot assets | `prompt_skeleton_service/app/services/question_generation_prompt_assets.py`；`prompt_skeleton_service/app/services/prompt_builder.py`；`prompt_skeleton_service/configs/question_generation_prompt_assets.yaml` | `sentence_fill`、`center_understanding`、`sentence_order` 三卡 few-shot candidates 与 prompt guards | 当 `use_fewshot=true` 且 `fewshot_mode=structure_only` 时，进入真实 prompt 构建路径 |
| question card binding | `prompt_skeleton_service/app/services/question_card_binding.py`；`card_specs/normalized/question_cards/*.normalized.yaml` | 三张标准 question card | 运行层按 runtime binding 读取标准卡，但不读取 distillation candidate patch |
| material runtime overlay | `prompt_skeleton_service/app/services/distill_runtime_overlay.py`；`card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml`；`card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml` | 母子家族映射、材料卡映射、leaf overlay | 运行层消费的是当前正式 mapping，不是 `reports/distillation_runtime/round1` 里的 material_mapping candidate patch |
| behavior extraction API | `prompt_skeleton_service/app/routers/distill.py` 的 `POST /api/v1/distill/behavior/packets`；`prompt_skeleton_service/app/services/distillation_behavior_service.py` | 历史版本、review action、usage event -> behavior packet/hints/report | 可运行服务已接 API，但当前无充分证据显示有正式 behavior packet 落盘样例 |
| behavior frontend | `prompt_skeleton_service/app/demo_static/distill_demo.html`；`prompt_skeleton_service/app/demo_static/distill_demo.js` | 历史动作蒸馏入口、behavior packet 展示 | 前端可触发 behavior packet 生成；仍不自动回写 |

## 仍是 candidate-only 的内容

| 内容 | 路径 | 原因 |
| --- | --- | --- |
| `sentence_fill` 16 个 candidate patches | `reports/distillation_runtime/round1/distillation_result_packet.json` | result packet 只是结构化候选结果，没有写回主配置 |
| `sentence_fill` promotion bundle | `reports/distillation_runtime/round1/distillation_promotion_bundle.json` | 明确 `bundle_mode=candidate_only`，handoff note 写明不自动回写 |
| `sentence_fill` diff patch excerpts | `reports/distillation_runtime/round1/distillation_diff_report.json` | diff report 是审计/比较产物，不是配置 |
| leaf/batch draft | `reports/distill_batches/*/question_card_draft.yaml`；`reports/distill_batches/*/prompt_draft.md`；`reports/distill_batches/*/material_card_draft.yaml` | 当前无充分证据显示这些 draft 被统一写入正式卡或 prompt assets |
| behavior candidate patch hints | `prompt_skeleton_service/app/services/distillation_behavior_service.py` 输出 | 只作为行为蒸馏建议，不是 truth，也未回写 |

## 仍停留在 hint/report 层的内容

| 内容 | 路径 | 审计结论 |
| --- | --- | --- |
| 三卡真题蒸馏总表 | `reports/truth_distillation_assets_2026-04-14.csv`；`reports/truth_distillation_assets_2026-04-14.jsonl` | 证明抽取过，不等于主配置已更新 |
| 三卡分表 | `reports/truth_distillation_assets_sentence_fill_2026-04-14.csv`；`reports/truth_distillation_assets_center_understanding_2026-04-14.csv`；`reports/truth_distillation_assets_sentence_order_2026-04-14.csv` | 每卡 50 条，可作为后续蒸馏输入 |
| 三卡 round1/round3 结果 | `reports/*_truth_round*_results_2026-04-14.csv` | 证明有实验运行结果，但不是结构化 runtime promotion bundle |
| few-shot 回归报告 | `reports/round1_fewshot_generation_regression_report_2026-04-12.md` | 证明三卡 few-shot 进入真实 prompt 路径，但最终 verdict 仍是 `need_fix` |

## 审计结论

- `prompt_assets` 和 `material_mapping` 有真实运行层消费点。
- `question_card` 的正式卡有运行层消费点，但 distillation candidate patch 未被消费。
- `validator_contract` 的 candidate patch 未被消费；现有 validator 证据主要是回归/审计报告。
- behavior 层已具备 API/UI/service/test，但当前无充分证据显示已有正式落盘行为蒸馏样例。

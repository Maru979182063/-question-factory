# 蒸馏资产交接与下一步

## 接手顺序

1. 先看 `docs/distillation_cards_and_prompts_asset_index.md`，确认三张题卡分别有哪些 truth / prompt / candidate 资产。
2. 再看 `docs/distillation_runtime_consumption_audit.md`，只把已被代码读取的内容当成 runtime-consumed。
3. 如果要审 `sentence_fill` 新闭环，直接从 `reports/distillation_runtime/round1/` 的 input/result/diff/promotion 四件套开始。
4. 如果要审 `center_understanding` 或 `sentence_order`，先从 `reports/truth_distillation_assets_*_2026-04-14.csv`、`reports/*_truth_round*_results_2026-04-14.csv`、`reports/round1_fewshot_*_candidates_2026-04-12.csv` 开始，不要假设它们已有新结构化 runtime bundle。
5. 如果要接 behavior distillation，先通过 `POST /api/v1/distill/behavior/packets` 或前端历史动作蒸馏入口生成包，再决定是否落盘。

## 最重要的文件

- `prompt_skeleton_service/configs/prompt_assets/truth_distillation_prompt_assets.yaml`
- `prompt_skeleton_service/configs/question_generation_prompt_assets.yaml`
- `prompt_skeleton_service/app/services/distillation_runtime_service.py`
- `prompt_skeleton_service/app/services/distillation_behavior_service.py`
- `reports/distillation_runtime/round1/distillation_promotion_bundle.json`

## 不要乱动什么

- 不要把 `reports/distillation_runtime/round1/` 里的 candidate patch 直接写回正式题卡。
- 不要把 `behavior_distillation` 的用户改题信号当成 truth distillation。
- 不要把所有 patch 都归到 `prompt_assets`，至少保持 `question_card` / `prompt_assets` / `validator_contract` / `material_mapping` 四层。
- 不要把 leaf/batch 里的 `*_draft.yaml` 说成正式配置，除非能找到真实消费代码或合并记录。
- 不要扩到线上自动自学习；当前仍是离线闭环和人工审核。

## 下一阶段优先级

| 优先级 | 动作 | 原因 |
| --- | --- | --- |
| P0 | 为 `center_understanding` 与 `sentence_order` 补同格式 runtime packet/diff/promotion 样例 | 目前三卡有蒸馏资产，但新结构化闭环只有 `sentence_fill` 完整 |
| P0 | 落盘一份 behavior packet/report 样例 | behavior 服务已实现，但当前报告资产证据不足 |
| P1 | 人工审核 `sentence_fill` promotion bundle 的 16 个 candidate patches | 它是当前唯一完整 candidate bundle |
| P1 | 明确哪些 `reports/distill_batches/*/prompt_draft.md` 要进入主 `question_generation_prompt_assets.yaml` | 避免 prompt 资产散落 |
| P2 | 给 promotion 增加人工审核记录和回滚包后，再考虑回写 | 当前禁止自动回写是正确边界 |

## 当前不能写得更满的地方

- 当前无充分证据证明 `center_understanding` 和 `sentence_order` 已有新结构化 `distillation_result_packet` / `diff_report` / `promotion_bundle`。
- 当前无充分证据证明 behavior packet/report 已在 `reports/` 下正式落盘。
- 当前无充分证据证明 `reports/distill_batches/*/*_draft.yaml` 已经被自动合并进主配置。

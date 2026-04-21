# 蒸馏 Patch Target 分层清单

本清单按 patch target 分层，而不是按报告分层。当前蒸馏仍是离线闭环：truth / behavior -> candidate patch -> diff report / promotion bundle -> human review，不自动回写主配置。

## `question_card`

| 来源 | 代表问题 | 代表产物 | 当前状态 | 是否已被消费 |
| --- | --- | --- | --- | --- |
| truth | `sentence_fill` 的局部绑定、全局语境、干扰项竞争、空位功能不贴近目标难度 | `reports/distillation_runtime/round1/distillation_result_packet.json` 中 `question_card.*.under_target`；`prompt_skeleton_service/configs/prompt_assets/truth_distillation_prompt_assets.yaml` 中 `patch_blueprints.*.question_card` | `candidate-only not consumed` | 否，未自动写回 `card_specs/normalized/question_cards/sentence_fill_standard_question_card.normalized.yaml` |
| truth | 三卡题卡结构字段从真题中抽取出来，但还需人工决定是否固化 | `reports/truth_distillation_assets_*_2026-04-14.csv`；`reports/*_truth_blueprint_2026-04-14.md`；`reports/distill_batches/*/question_card_draft.yaml` | `diagnostic` + `candidate` | 部分基础卡已存在并被绑定服务读取，但 batch draft 未见自动消费证据 |
| behavior | 用户历史改题集中在 `options`、`analysis`、truth-like 字段时，提示题卡默认约束可能需要收紧 | `prompt_skeleton_service/app/services/distillation_behavior_service.py` 生成 `behavior.question_card.*` hints | `candidate-only not consumed` | 否，当前仅生成 hints |

## `prompt_assets`

| 来源 | 代表问题 | 代表产物 | 当前状态 | 是否已被消费 |
| --- | --- | --- | --- | --- |
| truth | 蒸馏 prompt 需要集中放置，不把基础映射硬编码进 service | `prompt_skeleton_service/configs/prompt_assets/truth_distillation_prompt_assets.yaml` | `consumed in runtime` | 是，`distillation_runtime_service.py` 加载该 YAML 并用其中 blueprint 生成 candidate patches |
| truth | 三卡 prompt 需要吸收 round1 few-shot 和守卫语句 | `prompt_skeleton_service/configs/question_generation_prompt_assets.yaml` 的 `round1_fewshot_assets` 与 `fewshot_prompt_guards` | `consumed in runtime` | 是，`question_generation_prompt_assets.py` / `prompt_builder.py` 在生成 prompt 时读取 |
| truth | leaf/batch 阶段沉淀了更细 prompt 草稿 | `reports/distill_batches/*/prompt_draft.md`；`reports/distill_batches/*/distill_pack_*.md` | `candidate` | 当前无充分证据证明这些草稿被自动并入主 prompt assets |
| behavior | 用户改动轨迹显示某些 prompt guard 应增强，例如干扰项、解析、材料边界 | `distillation_behavior_service.py` 生成 `behavior.prompt_assets.*` hints | `candidate-only not consumed` | 否，当前只通过 API/UI 暴露候选 |

## `validator_contract`

| 来源 | 代表问题 | 代表产物 | 当前状态 | 是否已被消费 |
| --- | --- | --- | --- | --- |
| truth | `sentence_fill` 需要对局部绑定、段落一致性、干扰项表面相似、功能角色一致性加校验建议 | `reports/distillation_runtime/round1/distillation_result_packet.json` 中 `validator_contract.*.under_target` | `candidate-only not consumed` | 否，未见自动写入 validator 主规则 |
| truth | 真实运行中已有三卡验证/回归样例 | `reports/card_validation_fill_realq.json`；`reports/card_validation_main_realq.json`；`reports/card_validation_order_realq.json`；`reports/round1_fewshot_generation_regression_report_2026-04-12.md` | `diagnostic` | 是，作为审计/回归证据；不是 candidate patch 自动消费 |
| behavior | 高频 failed threshold 可转成 validator contract hints | `distillation_behavior_service.py` 中 `top_failed_thresholds -> behavior.validator_contract.*` | `candidate-only not consumed` | 否，当前没有落盘样例和自动回写 |

## `material_mapping`

| 来源 | 代表问题 | 代表产物 | 当前状态 | 是否已被消费 |
| --- | --- | --- | --- | --- |
| truth | 题型与材料卡、母子家族、叶子结构之间要保持映射稳定 | `card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml`；`card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml` | `consumed in runtime` | 是，`distill_runtime_overlay.py` 读取并生成 runtime overlay |
| truth | `sentence_fill` round1 候选指出材料映射可偏向 explicit transition / paragraph axis / parallel shells 等信号 | `reports/distillation_runtime/round1/distillation_result_packet.json` 中 `material_mapping.*.under_target` | `candidate-only not consumed` | 否，未自动写回 runtime mapping YAML |
| truth | 三卡材料侧有 train/test 切分和 batch 资产 | `reports/distill_runs/truth_material_distill_20260414_142852/`；`reports/distill_batches/*/material_card_draft.yaml`；`reports/distill_batches/*/material_samples_*.csv` | `diagnostic` + `candidate` | 部分基础映射被 runtime overlay 消费；batch draft 未见自动消费证据 |
| behavior | 用户改题跨材料边界时，可提示 material mapping 优先级调整 | `distillation_behavior_service.py` 中 `material_boundary_cross_rate -> behavior.material_mapping.*` | `candidate-only not consumed` | 否，当前仅为候选 hint |

## 已消费与未消费边界

- 已消费：`truth_distillation_prompt_assets.yaml` 的 `sentence_fill` blueprint；`question_generation_prompt_assets.yaml` 的三卡 few-shot/guard；两份 runtime mapping YAML；标准 question card YAML。
- 未消费：`reports/distillation_runtime/round1/` 内的 candidate patches；`reports/distill_batches/*/*_draft.yaml`；behavior candidate patch hints。
- 当前无充分证据：behavior packet/report 的正式落盘样例；`center_understanding` 与 `sentence_order` 的新结构化 runtime result/diff/promotion 样例。

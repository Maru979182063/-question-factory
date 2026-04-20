# 蒸馏运行层最小契约

## 1. 目标

本文档定义当前仓库在交接前封板阶段可正式运行的“蒸馏运行层最小闭环”。

本层只服务于：

- `sentence_fill`
- 离线蒸馏
- candidate patch 生成
- 一次 agent 调整建议
- diff report 与测试报表

本层明确不负责：

- 全题型扩展
- 线上自动自学习
- 主配置自动回写
- 全局难度总线
- 精细调参与长期实验调度

## 2. 输入输出对象

### 2.1 `distillation_input_packet`

输入包必须是结构化对象，至少包含 4 组信息：

1. 真题样本
2. 历史线程摘要
3. 测试结果快照
4. 当前运行态快照

`family_id` 当前只能是 `sentence_fill`。

### 2.2 `distillation_result_packet`

结果包必须是结构化对象，至少包含：

1. 归一化后的 sentence_fill 约束视图
2. 目标难度观察
3. 实际难度观察
4. 难度拟合结果
5. candidate patches
6. 一次 agent 调整建议
7. 运行总结

## 3. 运行顺序

本轮封板按以下固定顺序执行：

1. 输入标准化
2. 目标/实际难度结构化
3. candidate patch 生成
4. 一次 agent 调整建议
5. diff report
6. handoff bundle

不允许跳过标准化直接从松散文本产出 patch。

## 4. candidate patch 范围

当前只允许产出以下 4 类 candidate patch：

- `question_card`
- `prompt_assets`
- `validator_contract`
- `material_mapping`

patch 只作为候选修改包存在，不自动写回主配置。

## 5. sentence_fill 最小观察维度

当前只对 `sentence_fill` 补 4 个最小难度观察维度：

- `local_binding_complexity`
- `global_context_dependency`
- `distractor_similarity`
- `blank_function_ambiguity`

所有 diff report 必须比较目标难度与实际难度在上述 4 维度上的拟合情况。

## 6. 与现有分层的边界

- `passage_service` 继续负责材料侧处理与候选材料供给。
- `prompt_skeleton_service` 继续负责出题、评审、版本记录。
- 本蒸馏运行层只消费已有协议与快照，不反向创造新的题型主协议。
- 蒸馏 prompt 统一存放在 `prompt_skeleton_service/configs/prompt_assets/truth_distillation_prompt_assets.yaml`。
- service 不得把基础映射口径重新硬编码回深层逻辑。

## 7. 封板判定

视为“可交接、可运行、可解释”的最小闭环，必须满足：

1. 可从输入包生成结果包
2. 可从结果包产出 candidate promotion bundle
3. 可从输入包与结果包产出 diff report
4. 可用脚本跑通一轮 demo/offline round
5. 有最小测试覆盖 runtime / promotion / diff 三层

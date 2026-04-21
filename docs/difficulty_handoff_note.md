# 难度控制交接说明

## 1. 本轮已经封板的内容

已经补出一条最小可运行主链：

`difficulty_target`
-> `difficulty_projection`
-> `prompt / validator consumption`
-> `actual_difficulty_assessment`
-> `truth-based calibration`
-> `diff / backtest report`

实现重点：

- 总协议正式独立成 schema
- `sentence_fill` 先行落地
- prompt assets 外置到 YAML
- patch 只出 candidate，不自动回写

## 2. 当前实现位置

核心 schema / service：

- [prompt_skeleton_service/app/schemas/difficulty.py](/C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/schemas/difficulty.py)
- [prompt_skeleton_service/app/services/difficulty_projection_service.py](/C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/services/difficulty_projection_service.py)
- [prompt_skeleton_service/app/services/difficulty_assessment_service.py](/C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/services/difficulty_assessment_service.py)
- [prompt_skeleton_service/app/services/difficulty_diff_service.py](/C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/services/difficulty_diff_service.py)
- [prompt_skeleton_service/app/services/difficulty_calibration_service.py](/C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/services/difficulty_calibration_service.py)

挂接位置：

- `slot_resolver` 负责 target -> projection
- `question_generation` 负责 projection -> prompt / validator -> actual / gold / patch
- `question_validator` 负责统一消费 richer `difficulty_fit`

## 3. 设计边界

本轮故意没有做：

- 通用全 family 难度轴框架
- 自动在线学习
- 自动改 prompt assets / 题卡 / validator
- 蒸馏层主导生产逻辑

如果后续要继续扩：

- 优先加 family 协议文档
- 再加 family axis projection / assessment
- 最后接 truth gold 和 backtest 资产

## 4. 已知风险

- `sentence_fill` assessment 目前是最小启发式实现，足够回测，不是最终评审器
- gold assessment 依赖 source question 可被转成 `GeneratedQuestion` 形式
- 现有仓库中还有一批并行蒸馏改动，交接时要避免把“难度控制主干线”再被蒸馏逻辑反向侵入

## 5. 建议的下一步

推荐按下面顺序继续平移：

1. `sentence_order`：先定义 3-4 个结构轴，再做 target/projection/assessment。
2. `main_idea`：围绕主轴来源、抽象层级、干扰项偏移做 family 协议。
3. 回测样本：每个 family 先做小样本 truth pack，再扩规模。
4. patch bundle：仍保持人工确认后再写回配置。

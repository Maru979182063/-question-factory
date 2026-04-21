# 难度控制总协议（主干线最小闭环）

## 1. 本轮目标

本轮只补“题卡驱动系统中的难度控制主干线最小闭环”，目标链路固定为：

`difficulty_target`
-> `difficulty_projection`
-> `prompt / validator consumption`
-> `actual_difficulty_assessment`
-> `truth-based calibration`
-> `diff / backtest report`

蒸馏层本轮不是主工程，只作为：

- 真题难度画像提取工具
- `difficulty_fit_gold` 生成工具
- 协议漂移点发现工具
- patch candidate 产出工具

明确不做：

- 全母族一次性落地
- 在线自动自学习
- 自动回写主配置
- 大规模前端重构

## 2. 统一对象

本轮在 [prompt_skeleton_service/app/schemas/difficulty.py](/C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/schemas/difficulty.py) 中正式统一：

- `DifficultyTarget`
- `DifficultyProjection`
- `ActualDifficultyAssessment`
- `DifficultyFitResult`
- `DifficultyCalibrationPatch`

统一后的核心约束是：

- target 只表达“想要的难度带”和轴目标
- projection 只表达“按题卡/slot/prompt 预计会落在哪”
- assessment 只表达“题目实际生成后读感上落在哪”
- fit 只表达“target / actual / gold 之间是否匹配”
- calibration patch 只表达“候选修补建议”，不直接改配置

## 3. 统一 report / diff 字段

所有 diff、回测结果和后续 debug packet 统一使用以下字段：

- `target_difficulty`
- `actual_difficulty`
- `gold_difficulty`
- `fit_result`
- `axis_diff`
- `structural_changes`
- `validator_status`
- `review_delta`
- `promotion_recommendation`

这组字段的含义约束如下：

- `target_difficulty`：请求层想要的 easy / medium / hard
- `actual_difficulty`：本次生成题的实际评估结果
- `gold_difficulty`：真题或真值回放得到的参考难度
- `fit_result`：`under_target / on_target / over_target / gold_mismatch / unknown`
- `axis_diff`：按难度轴展开的 target / projection / actual / gold 对比
- `structural_changes`：为了达到难度效果引入的结构性变化
- `validator_status`：校验器对该题的最终状态
- `review_delta`：错误数、警告数、偏差数等审阅增量信息
- `promotion_recommendation`：是否适合提升为后续 patch bundle 候选

## 4. 服务分工

### 4.1 `difficulty_projection_service`

职责：

- 吃 `difficulty_target`
- 结合 pattern difficulty rules 与 family axis targets 生成 projection
- 产出 prompt 可消费的难度控制段落
- 产出 validator 可消费的 `difficulty_control` contract

约束：

- prompt 文案必须外置到 YAML
- service 里不硬编码长提示语

### 4.2 `difficulty_assessment_service`

职责：

- 站在“题已经生成出来”的角度做实际难度评估
- 优先读题面、正确项、上下文、干扰项竞争关系
- 在 family 行为未落地时允许 projection fallback

约束：

- 评估应尽量体现读感和结构判断
- 避免退化成纯机械正则打分器

### 4.3 `difficulty_diff_service`

职责：

- 汇总 target / projection / actual / gold
- 统一输出 `DifficultyFitResult`
- 统一生成 report row

### 4.4 `difficulty_calibration_service`

职责：

- 只输出 candidate patch
- patch target 限定为：
  - `question_card`
  - `prompt_assets`
  - `validator`

约束：

- 只给候选建议，不直接写回主配置

## 5. prompt / validator consumption 约束

prompt 侧统一消费：

- 难度总协议提示
- family 级难度轴提示
- 当前 projection axis / metric 摘要

validator 侧统一消费：

- `difficulty_fit`
- `difficulty_control.axis_targets`
- `difficulty_control.projection_axes`
- `difficulty_control.projection_metrics`

注意：

- validator 仍以合法性和结构正确性为主
- 难度只是并行控制维度，不得反客为主

## 6. sentence_fill 作为首个 family 的落地范围

本轮只落四个最小轴：

- `local_binding_complexity`
- `global_context_dependency`
- `distractor_similarity`
- `blank_function_ambiguity`

其中：

- projection 负责从 slot / pattern 先给出预计值
- assessment 负责从已生成题目再估一次实际值
- diff 负责把 target / actual / gold 摆在同一张表里

## 7. truth-based calibration 约束

真值回放只做三件事：

- 给 gold 侧难度画像
- 指出当前协议与真题读感的漂移点
- 输出 patch candidate

不做：

- 自动改卡
- 自动改 prompt assets
- 自动改 validator 阈值

## 8. 后续平移原则

往 `sentence_order`、`main_idea` 平移时，保持不变的是：

- 同一套 target / projection / assessment / fit / patch contract
- 同一套 report / diff 字段
- 同一套“只出 candidate patch、不自动回写”的策略

需要替换的是：

- family difficulty axes
- family assessment heuristics
- family prompt assets
- family truth gold 抽取口径

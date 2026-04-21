# 蒸馏运行层交接说明

## 1. 这次封板做了什么

本次补的是“蒸馏运行层最小闭环”，不是全量蒸馏平台。

新增能力：

- 正式 `distillation_input_packet`
- 正式 `distillation_result_packet`
- `sentence_fill` 四维最小难度观察
- candidate patch 生成
- 一次 agent 调整建议
- diff report
- candidate-only promotion bundle
- 三个离线脚本入口
- 行为蒸馏包：从 `question_item_versions / question_review_actions / question_usage_events` 提取真实修题轨迹
- 行为蒸馏候选 patch hints 与报告

## 2. 这次刻意没做什么

- 没扩到 `main_idea` / `sentence_order`
- 没自动写回主配置
- 没接线上自动实验
- 没做全局难度统一总线
- 没做多轮自动迭代 agent

## 3. 后续维护建议

### 3.1 先保住 packet 契约

后续如果扩题型，优先保住：

- 输入包结构
- 结果包结构
- patch target 边界
- diff report 结构

不要让新题型为了快，重新回到“散文式总结 + 临时脚本”的状态。

### 3.2 先扩 family 协议，再扩 service

如果要扩 `main_idea` 或 `sentence_order`，先补：

- family difficulty protocol
- prompt assets
- schema 中的 family 特定视图

再让 runtime service 消费。

### 3.3 promotion 仍应保持候选态

当前 promotion service 只负责 candidate bundle。

如果后续真的要做主配置回写，建议至少加：

- 人工审核 gate
- patch schema 版本号
- 回写前后 diff 落盘
- 回滚包

## 4. 交接时最重要的提醒

这层的价值不是“更聪明地猜”，而是把蒸馏过程变成：

- 可重复
- 可解释
- 可对比
- 可交接

后续维护者如果需要提速，也应优先保持这四点。

## 5. 行为蒸馏说明

当前仓库里，蒸馏输入已经不只有真题：

- `truth distillation`
  关注“和真题像不像”
- `behavior distillation`
  关注“用户最后实际把题修成了什么样、拿走了哪一版”

行为蒸馏当前走的是离线结构化包，不会直接自动回写主配置。

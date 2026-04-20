# 蒸馏工作台服务说明

## 1. 目标

这层服务不替代 `question_generation`，而是把“拿真题/母题反复试跑、调题卡/材料/提示词、最后交人工审核”的过程正式收口。

它解决的是三个问题：

- 实验过程之前没有正式对象
- train/dev/test 切分之前没有正式归属
- agent 调试成功后缺少明确的人审出口

## 2. 落点

代码位于 `prompt_skeleton_service`：

- router: `app/routers/distill.py`
- schema: `app/schemas/distill.py`
- service: `app/services/distill_workbench.py`
- persistence: `app/services/question_repository.py`

## 3. 核心对象

### 3.1 dataset

一套蒸馏样本集，承载：

- `truth_source_question`
- 可选 `generation_request`
- `split = train / dev / test`
- `question_card_id`
- sample 级 `tags / metadata`

支持两种切分方式：

- `manual`
  每个 sample 显式提供 `split`
- `hash`
  按稳定 hash 自动落到 `train / dev / test`

### 3.2 session

一条蒸馏会话，承载：

- `mode`
- `dataset_id`
- `question_card_id`
- `question_type / business_subtype`
- `baseline_request`
- 会话级目标与备注

它对应“围绕某一类题卡或材料链持续做拟合”的母任务。

### 3.3 run / trial

一次试验记录，承载：

- `run_no`
- `split`
- `sample_ids`
- `hypothesis`
- `request_snapshot`
- `batch_ids / item_ids`
- `sample_results`
- `fit_summary`
- `error`

它对应“这次改了什么、在哪个切片上跑、结果怎么样”。

### 3.4 review

一次人工审核记录，承载：

- `verdict = approved / rejected / revise`
- `summary`
- `reason`
- `notes`
- `reviewer`
- `allow_promote`
- `promotion_targets`

它对应“agent 这轮试验是否被人工接受，以及是否允许沉淀到正式题卡/配置”。

### 3.5 patch

一次显式改动记录，承载：

- `target = question_card / prompt_config / material_strategy`
- `title`
- `summary`
- `scope_key`
- `patch`
- `author`

它对应“这一轮到底改了什么”，不再只靠口头描述或备注。

### 3.6 promotion

一次正式沉淀记录，承载：

- `targets`
- `summary`
- `promoter`
- `patch_ids`
- `artifact_path`

它对应“审核通过后，这轮 run 被打包成可沉淀 bundle”。

## 4. 三种模式

### 4.1 `new_card`

用于新题卡创建阶段。

重点是：

- 给出 `baseline_request`
- 绑定目标题卡
- 在小样本上验证第一版是否能跑通

当前约束：

- 必须提供 `baseline_request`

### 4.2 `card_tuning`

用于已有题卡的拟合与调试。

重点是：

- 固定题卡或题卡族
- 在 `dataset` 的 `dev/test` 上反复跑
- 看题型、材料、成题和解析是否更贴真题

当前约束：

- 需要 `dataset_id` 或 `truth_source_question`

### 4.3 `material_tuning`

用于材料链单独调试。

重点是：

- 固定题卡
- 观察取材、材料卡命中、材料改写和可出题性

当前约束：

- 需要 `dataset_id` 或 `truth_source_question`

## 5. trial 如何运行

当前执行口径：

1. 先定位 `session`
2. 再定位样本来源
   - 如果 session 绑定 `dataset`，按 `split` 或 `sample_id` 取样本
   - 否则回退到 session 内联的 `truth_source_question`
3. 为每个 sample 组装有效请求
   - 优先使用 trial 显式 `request`
   - 否则使用 sample 自带 `generation_request`
   - 再否则使用 session 的 `baseline_request`
4. 如果请求里没有 `source_question`，自动挂载 sample truth
5. 调用现有 `question_generation`
6. 记录 sample 级结果
   - `batch_id`
   - `item_ids`
   - `item_preview`
   - `fit_summary`
   - `error`
7. 聚合成 run 级 `fit_summary`

## 6. fit summary

当前先提供轻量拟合摘要，不直接宣称“拟合成功”，而是给出可回收信号：

- `question_type_match`
- `business_subtype_match`
- `answer_match`
- `stem_similarity`
- `analysis_similarity`
- `option_overlap`
- `material_similarity`
- `fit_band`
- `notes`

run 级 `fit_summary` 是 sample 级结果的聚合摘要。

## 7. Human Review Outlet

run 完成后，可以进入明确的人审出口。

新增 API：

- `GET /api/v1/distill/runs/{run_id}`
- `POST /api/v1/distill/runs/{run_id}/review`

当前约束：

- 只有 `completed` run 才能被标记为 `approved`
- 只有 `approved` review 才能设置 `allow_promote = true`
- 如果 `allow_promote = true`，必须给出至少一个 `promotion_target`

目前支持的 `promotion_targets`：

- `question_card`
- `prompt_config`
- `material_strategy`

## 8. Patch And Promote

新增 API：

- `POST /api/v1/distill/runs/{run_id}/patches`
- `POST /api/v1/distill/runs/{run_id}/promote`

当前约束：

- promotion 必须基于最新一次 `approved` 且 `allow_promote=true` 的 review
- promotion 的目标必须是 review 明确允许的目标
- 每个 promotion target 都必须有至少一条显式 patch 记录

promotion 会在本地生成一个 bundle 文件，默认落到：

- `data/distill_promotions/{promotion_id}.json`

## 9. API

### dataset

- `GET /api/v1/distill/datasets`
- `POST /api/v1/distill/datasets`
- `GET /api/v1/distill/datasets/{dataset_id}`

### session

- `GET /api/v1/distill/sessions`
- `POST /api/v1/distill/sessions`
- `GET /api/v1/distill/sessions/{session_id}`

### trial

- `POST /api/v1/distill/sessions/{session_id}/trials`

### run review

- `GET /api/v1/distill/runs/{run_id}`
- `POST /api/v1/distill/runs/{run_id}/review`

### patch / promote

- `POST /api/v1/distill/runs/{run_id}/patches`
- `POST /api/v1/distill/runs/{run_id}/promote`

### frontend

- `GET /demo/distill`

## 10. 为什么这样切

这次没有继续把蒸馏逻辑塞回 `question_generation.py`，因为当前最缺的不是“再多一个生成分支”，而是：

- 实验过程没有独立对象
- 真题拟合过程缺少正式留痕
- 数据切分没有正式归属
- agent 成功后没有明确的人审出口

所以先把“过程服务化”，再逐步把这些对象继续接进来：

- card patch
- prompt patch
- reviewer verdict
- promotion decision
- split 级报表

# 蒸馏/调试运行体系现状审计

日期：2026-04-27

## 1. 审计范围

本次审计只判断当前仓库中已经存在的运行链、契约、状态记录和报告能力，不新增业务功能，不改生题、材料、题卡、prompt、validator、runtime 主链。

覆盖对象：

- 生题主链：`question_generation`、`question_validator`、`question_review`、`slot_resolver`、`material_bridge_v2`
- 难度控制主链：`difficulty_projection`、`difficulty_assessment`、`difficulty_calibration`、`difficulty_diff`
- 蒸馏运行链：`distillation_runtime_service`、`distill_workbench`、`distillation_diff_service`、`distillation_promotion_service`
- 材料协议分工位流水线：`material_protocol_split_pipeline` 及其 `pipeline_state`、stage report、checkpoint、resume 机制

判断口径：

- `Level 0`：只有想法或文档
- `Level 1`：有业务过程，但没有正式运行时
- `Level 2`：有正式输入输出 contract，可单独运行
- `Level 3`：有状态记录、失败恢复、diff/report，属于可调试流水线
- `Level 4`：已经可被更高层主调度器稳定调用

## 2. 已有调试链清单

### 2.1 生题主链

主要落点：

- `prompt_skeleton_service/app/services/question_generation.py`
- `prompt_skeleton_service/app/services/question_validator.py`
- `prompt_skeleton_service/app/services/question_review.py`
- `prompt_skeleton_service/app/services/slot_resolver.py`
- `prompt_skeleton_service/app/services/material_bridge_v2.py`
- `prompt_skeleton_service/app/services/runtime_observer.py`

当前能力：

- `QuestionGenerationService` 已经是代码级业务编排器，会调用题卡绑定、slot 解析、材料桥接、prompt 组装、LLM 网关、validator、难度投影、难度评估、diff、calibration patch 等服务。
- `runtime_observer` 提供 request trace、stage timing 和 runtime event 持久化能力。
- 生题链内部有局部 retry，例如 alignment retry、quality repair retry。
- `QuestionValidatorService` 有注册式 validator 和 contract-gated checks。
- `MaterialBridgeV2Service` 能基于 runtime materials config、business family、question_card、query_terms、材料策略和 review 状态选择材料。

审计判断：

- 成熟度：`Level 2`
- 理由：它是强业务主链，有明确 schema 和服务边界，也有局部 trace/retry；但没有独立的 durable pipeline state、checkpoint、resume、stage report。它不是一个可恢复的 multi-stage 调试运行时。

### 2.2 Review / Action 链

主要落点：

- `prompt_skeleton_service/app/services/question_review.py`
- `prompt_skeleton_service/app/services/patch_scope_registry.py`

当前能力：

- 能记录 review action、scope、feedback outcome。
- 支持 action boundary 和 patch scope 限制。
- 可作为 human review gate 的一部分。

审计判断：

- 成熟度：`Level 2`
- 理由：有正式业务 contract 和持久化动作，但不是分阶段 pipeline，没有 checkpoint/resume。

### 2.3 难度控制链

主要落点：

- `prompt_skeleton_service/app/services/difficulty_projection_service.py`
- `prompt_skeleton_service/app/services/difficulty_assessment_service.py`
- `prompt_skeleton_service/app/services/difficulty_calibration_service.py`
- `prompt_skeleton_service/app/services/difficulty_diff_service.py`
- `prompt_skeleton_service/app/schemas/difficulty.py`

当前能力：

- `DifficultyProjectionService` 可从生成请求和上下文投影目标难度。
- `DifficultyAssessmentService` 可对实际生成结果做难度评估。
- `DifficultyDiffService` 生成 target/actual/gold 的 diff 结果。
- `DifficultyCalibrationService` 生成候选 patch，例如 `prompt_assets`、`question_card`、`validator` 侧调整建议。

审计判断：

- 成熟度：`Level 2`
- 理由：有较完整的 contract、diff、patch candidate，但当前不是独立 durable runtime；没有统一 state file、stage report、失败恢复或 resume。truth-based calibration / backtest 在文档和局部服务中存在能力基础，但还没有形成 Level 3 的统一调试流水线。

### 2.4 蒸馏运行链

主要落点：

- `prompt_skeleton_service/app/services/distillation_runtime_service.py`
- `prompt_skeleton_service/app/services/distillation_diff_service.py`
- `prompt_skeleton_service/app/services/distillation_promotion_service.py`
- `prompt_skeleton_service/app/services/distill_workbench.py`
- `prompt_skeleton_service/app/schemas/distillation.py`
- `prompt_skeleton_service/app/schemas/distill.py`
- `docs/distillation_runtime_contract.md`

当前能力：

- `DistillationRuntimeService` 定义 `DistillationInputPacket -> DistillationResultPacket` 的最小运行契约，目前主要服务 `sentence_fill`。
- `DistillationDiffService` 可从 input/result packet 生成 diff report。
- `DistillationPromotionService` 能把 candidate patches 分组为 promotion bundle。
- `DistillWorkbenchService` 支持 dataset、session、trial run、review、patch、promote，并写出 promotion bundle artifact。
- `DistillRunReviewRequest`、`DistillRunPatchRequest`、`DistillPromotionRequest` 已有 canonical target 与 legacy alias normalize。
- promotion 必须经过 human review，且每个 promotion target 必须有对应 patch。

审计判断：

- 成熟度：`Level 3-`
- 理由：它具备正式输入输出、run 状态、review gate、patch、promotion bundle 和 artifact 输出，已经是可调试蒸馏 workbench；但它没有通用 stage checkpoint/retry/resume。严格说不是完整 Level 3 pipeline，但比普通 Level 2 服务成熟。

### 2.5 leaf_pre_distill 离线蒸馏链

主要落点：

- `tools/leaf_pre_distill/run.py`
- `tools/leaf_pre_distill/bootstrap_discovery.py`
- `tools/leaf_pre_distill/axis_confirmation.py`
- `tools/leaf_pre_distill/formal_patch_draft.py`
- `tools/leaf_pre_distill/formal_writeback_plan.py`
- `tools/leaf_pre_distill/formal_writeback_executor.py`
- `tools/leaf_pre_distill/truth_gold_regression.py`
- `tools/leaf_pre_distill/gold_reconstruction.py`
- `tools/leaf_pre_distill/source_discovery_preparation.py`
- `tools/leaf_pre_distill/source_candidate_search.py`
- `tools/leaf_pre_distill/source_candidate_review.py`

当前能力：

- 已形成 artifact-driven 离线工作流。
- 多数环节都有 JSON/JSONL/Markdown artifact。
- 写回执行器有 explicit approval、forward/rollback patch、manifest、regression report。
- 题卡线和材料线边界较清楚。

审计判断：

- 成熟度：`Level 3`
- 理由：离线 artifact、report、human decision、draft、writeback plan、executor 边界完整；但各子链之间主要依靠 CLI 参数和人工路径传递，尚未由系统级主调度器统一调用。

### 2.6 材料协议分工位流水线

主要落点：

- `tools/leaf_pre_distill/material_protocol_split_pipeline.py`
- `tools/leaf_pre_distill/material_protocol_split_runtime.py`
- `tools/leaf_pre_distill/material_protocol_split_state.py`
- `tools/leaf_pre_distill/material_protocol_split_stage_report.py`
- `docs/material_protocol_split_pipeline_resilience_execution_report_2026-04-27.md`

工位顺序：

1. `material_evidence_map`
2. `material_semantic_requirements_draft`
3. `material_card_draft`
4. `material_line_prompt_assets_draft`
5. `material_quality_regression_draft`
6. `material_bridge_mapping_draft`

当前能力：

- 每个 stage 成功后立即落盘到 `stages/`。
- `pipeline_state.json` 记录 stage status、output_path、error_summary、retry_count、duration。
- stage-level retry 默认 1 次。
- `--resume` 可跳过已成功 stage，继续未完成 stage。
- 输出 `pipeline_stage_report.json` 和 `pipeline_stage_report.md`。
- checker 保持 draft-only 边界，拒绝 formalized/writeback/verified/crawl_allowed 等越权字段。

审计判断：

- 成熟度：`Level 3`
- 理由：这是当前仓库最接近“multi-like 调试流水线”的代码实现。它有 stage sequence、checkpoint、retry、resume、state file、stage report 和 contract checker。但它仍未接入更高层总调度器，因此不是 Level 4。

## 3. 每条链的成熟度分级

| 链路 | 成熟度 | 依据 |
|---|---:|---|
| 生题主链 | Level 2 | 有业务编排、schema、validator、material bridge、trace 和局部 retry；缺 durable checkpoint/resume/stage report |
| Review / Action 链 | Level 2 | 有 review/action contract 和持久化；缺 pipeline runtime |
| Validator / Slot / Binding 子链 | Level 2 | 可被主链调用，边界清楚；不是独立调试流水线 |
| 难度控制链 | Level 2 | 有 projection/assessment/diff/calibration patch；缺统一状态、resume、stage report |
| 蒸馏 runtime packet 链 | Level 2 | `input_packet -> result_packet -> diff -> candidate bundle` 契约明确；主要限于 sentence_fill |
| Distill workbench 链 | Level 3- | 有 dataset/session/run/review/patch/promotion bundle；缺通用 checkpoint/retry/resume |
| leaf_pre_distill 离线链 | Level 3 | artifact/report/draft/approval/writeback executor 边界完整；主要靠人工串联 |
| 材料协议分工位流水线 | Level 3 | stage、checkpoint、retry、resume、state、stage report 都已存在 |
| 系统级主调度器 | Level 1 | 有文档级总控思路和人工可串联路径；没有代码级总调度 runtime |

## 4. multi-like 特征矩阵

| 链路 | stage sequence | checkpoint | retry | resume | state file | stage report | diff/backtest/report | candidate patch / promotion bundle | human review gate | contract-stable I/O |
|---|---|---|---|---|---|---|---|---|---|---|
| 生题主链 | 半有，代码内隐式阶段 | 无 | 半有，局部 repair retry | 无 | 无统一 state file | 无 stage report | 有 validation/difficulty/trace 结果 | 半有，difficulty calibration patch | 半有，下游 review | 有 |
| 难度控制链 | 有，projection/assessment/diff/calibration | 无 | 无 | 无 | 无 | 无 | 有 diff 与 patch candidate | 有 patch candidate | 半有 | 有 |
| 蒸馏 runtime packet 链 | 有 | 无 | 无 | 无 | 无 | 无 | 有 diff report | 有 candidate bundle | 半有 | 有 |
| Distill workbench 链 | 有，dataset/session/trial/review/patch/promote | 半有，repository 保存 run 状态 | 无 | 无 | 半有，DB + promotion artifact | 无统一 stage report | 有 fit summary / promotion bundle | 有 | 有 | 有 |
| leaf_pre_distill 离线链 | 有，artifact 驱动 | 半有，artifact 落盘 | 局部有 | 局部有 | 半有，按 artifact 记录 | 有各环节 report | 有 regression / draft / writeback diff | 有 draft / patch / evidence | 有 | 有 |
| 材料协议分工位流水线 | 有 | 有 | 有 | 有 | 有，`pipeline_state.json` | 有，`pipeline_stage_report.*` | 有 pipeline report | 无正式 promotion，只有 draft evidence | 半有，要求人审但 runtime 不执行人审 | 有 |
| Formal writeback executor | 有 | 半有，manifest/patch | 无 | 无 | 半有，manifest | 有 regression/report | 有 forward/rollback diff | 写回前 approval | 有 | 有 |

结论：当前仓库已经有多条“子工位链”，其中材料协议分工位流水线具备最完整的 multi-like 调试特征；但这些链尚未被一个统一主调度器自动串联。

## 5. 当前是否存在主 agent / 总调度器雏形

### 5.1 已经存在的代码级 orchestration

存在，但只在局部链内：

- `QuestionGenerationService` 是生题业务主链编排器。
- `DistillWorkbenchService` 是蒸馏 workbench 编排器。
- `material_protocol_split_pipeline` 是材料协议草案分工位 pipeline。

这些都是局部 orchestrator，不是系统级 master agent。

### 5.2 已经存在的文档级总控思路

存在。

仓库中已有大量 audit/plan/execution report，体现了统一节奏：

`audit / plan -> offline artifact -> small smoke -> human review -> draft -> regression -> writeback plan/diff -> explicit approval -> guarded executor`

但这仍是文档和人工流程层面的总控思路，不等同于代码级总调度器。

### 5.3 当前实际运行形态

当前实际形态是：

- 多条链可以人工串联；
- 部分链可以独立运行；
- 部分链有正式 artifact contract；
- 部分链有 report；
- 但没有统一入口来管理全局 run、全局状态、跨链依赖、失败恢复和总报告。

因此，当前还不能称为“已经存在主 agent / 总调度器”。更准确的判断是：

> 已经有多个可调试子链和局部 orchestrator，尚未形成系统级 master orchestration。

## 6. 当前能否串成系统级总调试链

可以人工串成，但不能自动稳定串成。

### 6.1 已经能衔接的输出/输入

- `gold_reconstruction_results.jsonl` 可以进入 `truth_gold_regression` 与 `source_discovery_preparation`。
- `source_discovery_queries.jsonl` 可以进入 `source_candidate_search`。
- `source_candidate_results.jsonl` 可以进入 `source_candidate_review`。
- `source_seed_registry.jsonl`、`crawl_seed_manifest.json` 可以进入材料协议草案 digest。
- `material_protocol_draft_input_digest.json`、`system_alignment_findings.json` 可以进入 `material_protocol_split_pipeline`。
- `leaf_pre_distill_report`、`schema_gap_report` 等 evidence 可以进入 distill workbench patch/promotion bundle。
- distill trial 可以调用生题主链并产生 fit summary。
- 难度 projection/assessment/diff 可以在生题链内部参与生成质量判断。

### 6.2 已经有正式 schema / contract 的地方

- 生题请求/响应：`QuestionGenerateRequest`、`QuestionGenerationBatchResponse`
- 蒸馏 workbench：dataset/session/run/review/patch/promotion schemas
- distillation runtime：input/result packet、diff report、promotion bundle
- 难度控制：projection、assessment、diff、calibration patch schemas
- 材料线离线 artifact：gold reconstruction、source discovery、candidate search/review、seed registry、material protocol draft
- 材料分工位流水线：stage output、state、stage report

### 6.3 仍靠人工拼接的地方

- 跨链 artifact path 传递主要靠 CLI 参数。
- 没有统一 `system_run_id` 或 correlation id 贯穿材料线、蒸馏线、生题线、难度线。
- 没有统一的 chain adapter registry 来声明“某链输出可以作为哪条链输入”。
- 没有统一状态文件记录系统级 run 中每条子链是否完成。
- 没有统一 report aggregator 汇总所有子链状态。

### 6.4 阻断总链成立的点

主要阻断不是单个子链能力不足，而是缺少跨链总控层：

1. 缺 `system_debug_run_manifest`
2. 缺跨链 stage/state 聚合
3. 缺统一 artifact registry 或至少只读 artifact index
4. 缺链间 adapter contract 清单
5. 缺系统级失败恢复策略
6. 缺系统级总调试报告生成器

## 7. 当前能否直接产出总调试报告

不能“直接自动产出”。

可以人工整理出系统级总调试报告，因为已有材料包括：

- 每条链的 execution report
- distill promotion bundle
- material protocol split stage report
- truth gold regression report
- source candidate/search/review report
- formal writeback executor report

但当前没有一个工具自动读取这些 artifact 并输出：

- 当前调试链清单
- 每条链成熟度
- 子链状态
- 上下游可串联关系
- 当前缺失 evidence
- blocked stage
- 下一步最小补刀建议

所以当前结论是：

> 系统级总调试报告具备数据基础，但缺少只读聚合器。

## 8. 缺失点与阻断点

### 8.1 总调度器缺失

当前没有一个代码级 master agent/runtime 负责：

- 选择子链
- 注入输入
- 管理跨链状态
- 跳过已完成链
- 失败后恢复
- 生成总报告

材料分工位流水线内部已经有类似能力，但范围只限于材料协议草案 6 个工位。

### 8.2 状态模型不统一

当前状态分散在：

- SQLite repository
- JSON / JSONL artifact
- Markdown report
- `pipeline_state.json`
- promotion bundle artifact
- runtime event

这些状态都真实存在，但没有统一系统级 index。

### 8.3 链间 contract 没有集中登记

每条链内部 contract 较清楚，但跨链 contract 主要存在于文档、CLI 参数和人工约定中。

例子：

- `source_seed_registry.jsonl` 可进入 material protocol draft，但不是由统一 adapter 注册。
- `leaf_pre_distill_report` 可作为 workbench evidence patch，但附件路径由人工组装。
- difficulty calibration patch 与 distill promotion patch 的关系尚未统一。

### 8.4 生题主链缺 durable debug pipeline

生题主链有 trace、retry 和大量内部阶段，但没有像材料 split pipeline 那样：

- 每阶段落盘
- stage report
- resume
- pipeline state

这会限制系统级 replay/debug。

### 8.5 难度链缺系统级 backtest runtime

难度链已有 projection/assessment/diff/calibration 服务，但缺一个统一的离线 backtest runner，把 gold、generated、axis diff、patch candidate、regression report 固化成 durable artifact。

## 9. 最小补刀建议

最多建议三条，且不扩散为新平台。

### 建议 1：新增只读 `system_debug_run_report` 聚合器

这是最该补的一刀。

目标不是执行子链，而是读取现有 artifact，生成系统级总调试报告。

最小输入：

- artifact root
- distill workbench run/promotion artifact path，可选
- material split `pipeline_state.json`，可选
- truth/material/source reports，自动发现或显式传入

最小输出：

- `system_debug_run_manifest.json`
- `system_debug_report.md`

边界：

- 只读
- 不调用 LLM
- 不执行生题
- 不写 card_specs
- 不写 material_card
- 不新增 promotion target
- 不改变任何主链

为什么优先：

- 当前每条链已经有报告，但用户缺的是“总控视角”。
- 只读聚合器风险最低。
- 它能直接回答“现在跑到哪、哪条链 blocked、下一步该看哪”。

### 建议 2：补一个跨链 artifact adapter 清单

形式可以先是 JSON 或 Markdown，不必做 runtime。

内容：

- 输出 artifact
- 可作为哪条链输入
- 必填字段
- 缺失时降级策略
- 是否允许人工路径传入

这能把当前人工串联变成可审计串联。

### 建议 3：给系统级 run 加统一 correlation id

先不改所有服务，只在新报告聚合器中生成并记录：

- `system_debug_run_id`
- 子链 artifact path
- 子链 run id / session id / promotion id
- 时间戳

后续再逐步让各链写入同一个 id。

## 10. 总结结论

当前项目已经具备“multi-like 子工位链”的基础，尤其是：

- 生题主链：局部 orchestrator
- 蒸馏 workbench：review / patch / promotion evidence 链
- leaf_pre_distill：artifact-driven 离线蒸馏链
- 材料协议分工位流水线：真正具备 checkpoint / retry / resume / stage report 的可调试 pipeline

但当前还没有系统级 master agent。

准确结论：

> 当前不是一个完整 multi-agent 平台，也不是自动总调度系统；它是由多个 contract-stable 子链、局部 orchestrator、离线 artifact pipeline 和人工 review gate 组成的 multi-like 调试体系雏形。

距离“系统级总调试报告”最近的一刀，不是继续新增业务链，而是做一个只读的系统级 report aggregator，把现有链路状态、artifact、成熟度、缺失点和下一步建议汇总起来。


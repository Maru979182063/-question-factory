# 材料线入库前模仿式蒸馏节奏审计与执行计划

日期：2026-04-26

## 1. 用户目标复述

用户要的不是一个独立爬虫项目，也不是把候选网页直接写成材料卡。

用户真正要的是：材料线作为现有蒸馏台里的一个材料蒸馏分支，继续沿用题卡线已经跑顺的工程节奏：

```text
审计 / 计划
-> 离线产物
-> 小样本冒烟
-> 人工审查
-> 草案
-> 回归
-> 写回计划 / 差异预览
-> 显式批准
-> 受控执行器
```

材料线可以有自己的关卡、提示词和评测维度，但不能另起炉灶，不能绕开 evidence / review / draft / regression / approval / executor 的节奏。

材料线最终服务于：

- 从真题包反向复原自然材料来源；
- 找到原文或相似材料候选；
- 理解原文如何被处理成真题材料；
- 沉淀清洗、切片、去噪、定位、质量判断规则；
- 形成材料卡草案；
- 通过真题金标、生成对照和用户反馈持续回归；
- 最后才在显式批准后进入受控写回。

## 2. 当前材料线已经走到哪一步

当前材料线已经走到：

```text
真题样本
-> 模型复原 gold schema
-> 真题金标回归框架
-> 来源发现准备
-> 来源候选搜索
-> 来源候选人工审查
-> 来源种子注册表
```

具体覆盖如下。

| 环节 | 当前产物 | 当前性质 | 是否可入库 |
| --- | --- | --- | --- |
| 模型式 gold 复原 | `gold_reconstruction_results.jsonl` | 真题 gold 语义复原 evidence | 否 |
| 真题回归 | `truth_gold_regression_results.json` / report | 质量评测 evidence | 否 |
| 来源发现准备 | `source_discovery_queries.jsonl` / `initial_material_seed_pack.jsonl` | 去题库化搜索准备 evidence | 否 |
| 来源候选搜索 | `source_candidate_results.jsonl` | 未验证候选来源 evidence | 否 |
| 来源候选人工审查 | `source_candidate_review.json` | 用户审查决策 evidence | 否 |
| 来源种子注册 | `source_seed_registry.jsonl` / `crawl_seed_manifest.json` | seed-only 资产 | 否 |

关键边界仍然成立：

- `source_candidate_results` 不是已确认原文；
- `source_seed_registry` 不是材料库；
- `crawl_seed_manifest.crawl_allowed=false`；
- `verified_original_source=false`；
- 不抓正文；
- 不入库；
- 不写 `material_card`；
- 不影响题卡线。

## 3. 和题卡线现有节奏的一致处

当前材料线已经在多个地方复用了题卡线的节奏。

| 题卡线节奏 | 材料线对应 |
| --- | --- |
| artifact contract | 材料线产物都作为 `leaf_pre_distill_report` 附件 evidence |
| 离线产物优先 | gold reconstruction / source discovery / source candidate search 都是离线产物 |
| 小样本冒烟 | LLM gold reconstruction smoke、web search smoke |
| 人工审查 | source candidate human review |
| draft-only 边界 | initial seed、review decision、source seed 都不直接 formalize |
| promotion evidence | 产物只进入 evidence，不新增 promotion target |
| 显式批准前禁止执行 | crawl manifest 默认 `crawl_allowed=false` |
| 禁止自动污染主链 | 不改 question_card / prompt / validator / runtime |

这说明材料线已经不是“随手搜网页”，而是在当前蒸馏台节奏里长出来的材料分支。

## 4. 还缺什么

当前最大缺口不是材料卡，而是正文和正文后的审计链。

当前已有 URL / 标题 / 摘要 / 域名，但没有：

- 显式抓取批准；
- 网页正文；
- 抓取清单与失败记录；
- 正文 hash / 去重 / 长度 / 域名风险；
- source 与 gold 的对齐；
- 原文到真题材料的转换假设；
- 清洗与切片草案；
- 材料片段候选；
- 材料质量统计；
- 材料卡草案；
- 材料卡回归报告；
- 材料写回计划 / 差异预览 / 回滚方案；
- 显式材料写回批准；
- 受控材料写回执行器。

这些缺口并不意味着要马上做完整爬虫。它们意味着下一步必须先把“是否允许抓正文”做成一等 artifact。

## 5. 后续统一节奏定义

后续每一个材料关卡都必须符合统一模板：

```text
audit_plan
-> input artifacts
-> output evidence artifacts
-> human review point
-> smoke / regression point
-> draft_only boundary
-> writeback plan before formalization
-> explicit approval before executor
-> no card/protocol-line mutation unless separately approved
```

任何材料线能力都不能跳过这些问题：

- 输入证据是什么？
- 输出是否只是 evidence？
- 是否需要人审？
- 是否只允许小样本冒烟？
- 是否禁止直接写库？
- 是否有 regression？
- 是否有 writeback plan / diff？
- 是否需要显式 approval？
- 是否会影响题卡线？

如果某一步回答不清楚，就不能进入执行器。

## 6. 哪些关卡可以有材料线自己的提示词

材料线可以有自己的提示词，但提示词只能服务于材料语义判断和草案生成，不能变成正式裁判。

允许有材料线提示词的关卡：

- gold reconstruction：复原统一 gold schema；
- source/gold alignment：建议来源正文与 gold 材料的语义对齐；
- material transformation hypothesis：提出“原文到真题材料”的转换假设；
- material cleaning recipe draft：提出清洗、去噪、切片、保留边界草案；
- material_card_draft：生成材料卡草案；
- material regression diagnosis：解释材料回归失败原因。

这些提示词的输出必须保持：

- `hypothesis`；
- `draft_only`；
- `formalized=false`；
- `writeback_allowed=false`；
- `needs_human_review` 可显式标记；
- 不允许自动 `verified=true`；
- 不允许自动写材料库；
- 不允许自动写 `material_card`。

## 7. 哪些流程范式绝不能改变

以下范式不能改变：

- 先审计计划，再实现；
- 先离线产物，再接主链；
- 先小样本 smoke，再扩大；
- 先人审，再草案；
- 草案必须 draft-only；
- 写回前必须有 plan / diff / rollback；
- 写回前必须显式批准；
- 执行器必须 allowlist；
- shared config 不能随意写；
- evidence target 不等于 formal config；
- 材料线不能自动修改题卡线；
- 模型输出不能直接 formalize；
- 机械统计不能冒充语义裁决。

## 8. 为什么下一步不是直接 material_card

不能直接进入 `material_card`，原因是：

- 当前只有 URL / title / snippet / domain，没有正文；
- 没有 source/gold alignment；
- 没有确认原文和相似材料的边界；
- 没有理解“原文如何被切成真题材料”；
- 没有清洗、切片、去噪、段落边界草案；
- 没有材料质量统计；
- 没有材料回归；
- 没有材料卡写回计划；
- 没有显式材料卡 approval。

直接 material_card 会把“候选来源”错误升格为“材料机制”，这和之前禁止把 candidate_axes 当 fields 是同一个风险。

## 9. 为什么下一步也不是直接入库

不能直接入库，原因是：

- `source_seed_registry` 只是 seed-only；
- `crawl_seed_manifest.crawl_allowed=false`；
- 用户保留 URL 不等于允许抓取；
- 抓取正文也不等于确认原文；
- 相似材料不能混成 original source；
- 未经清洗与质量回归的正文不能进入生产材料库；
- 未经批准的材料来源可能污染后续题型评测。

入库必须在正文抓取、对齐、清洗、质量统计、材料回归、人审、写回计划和批准之后。

## 10. 为什么下一步应该是 crawl approval + source_body_fetch 的 audit/plan

推荐下一刀是：

```text
crawl_approval + source_body_fetch audit_plan
```

原因：

- source_candidate_human_review 已经完成；
- source_seed_registry 已经存在；
- crawl_seed_manifest 已经给出种子与抓取限制；
- 但当前 `crawl_allowed=false`，说明系统明确还没有抓取授权；
- 没有正文就不能做 source/gold alignment；
- 没有 alignment 就不能做 transformation hypothesis；
- 没有 transformation hypothesis 就不能做 cleaning recipe；
- 没有 cleaning recipe 和质量统计就不能做 material_card_draft。

所以 crawl approval + source_body_fetch 是材料线继续前进的必要下一步，但必须先做审计计划，不能直接写爬虫。

## 11. crawl approval + source_body_fetch 如何保持 evidence artifact

它不应该被做成“爬虫项目”，而应该是当前蒸馏台中的一个 evidence 关卡。

建议输入：

- `source_seed_registry.jsonl`
- `crawl_seed_manifest.json`
- `crawl_approval_decisions.json`

建议输出：

- `crawl_approval.json`
- `source_body_fetch_manifest.json`
- `source_body_fetch_results.jsonl`
- `source_body_fetch_report.md`

边界：

- 只抓明确批准的 URL；
- 每个 URL 必须来自 seed registry 或手动批准补充；
- 默认小样本；
- 记录 URL、domain、hash、状态码、content type、长度、失败原因；
- 不确认原文；
- 不入库；
- 不写 material_card；
- 不影响题卡线；
- 所有正文仍然只是 evidence。

关键字段应包括：

- `crawl_allowed=true` 只存在于批准 artifact 中；
- `approval_scope`；
- `approved_urls`；
- `fetch_body=true` 只对批准 URL 生效；
- `verification_status="fetched_unverified"`；
- `verified_original_source=false`；
- `material_library_write=false`；
- `material_card_write=false`。

## 12. source_body_fetch 之后如何进入 source/gold alignment

正文抓取完成后，也不能直接入库。下一步应该是：

```text
source_body_fetch_results
-> source_gold_alignment
-> alignment evidence
-> human source verification
```

source/gold alignment 的目标是判断：

- 抓到的正文是否与 reconstructed gold 有重合；
- 是否可能是原文；
- 是否只是相似材料；
- 是否是转载、题库页、训练站或噪声页；
- gold 中哪些材料片段能在正文中定位；
- 哪些样本需要人工确认。

但 alignment 仍然不是 verified source。

它只能输出：

- alignment score；
- evidence spans；
- possible original source；
- similar material；
- mismatch；
- needs_human_review；
- warnings。

不能输出：

- `verified=true`；
- `verified_original_source=true`；
- material library write；
- material_card write。

## 13. 后续材料关卡如何映射现有节奏

### A. crawl_approval + source_body_fetch

输入：

- `source_seed_registry.jsonl`
- `crawl_seed_manifest.json`
- 人工 crawl approval JSON

输出：

- `crawl_approval.json`
- `source_body_fetch_manifest.json`
- `source_body_fetch_results.jsonl`
- `source_body_fetch_report.md`

节奏映射：

- 类似 source_candidate_human_review 的人工批准；
- 类似 source_candidate_search 的 bounded pilot；
- artifact 是 evidence，不是 material library；
- 抓取执行必须受 approval 限制。

边界：

- 只抓批准 URL；
- 不确认原文；
- 不入库；
- 不写 material_card；
- 不影响题卡线。

### B. source_gold_alignment

输入：

- `source_body_fetch_results.jsonl`
- `gold_reconstruction_results.jsonl`

输出：

- `source_gold_alignment_results.jsonl`
- `source_gold_alignment_summary.json`
- `source_gold_alignment_report.md`

节奏映射：

- 类似 truth_gold_regression；
- 先做 deterministic overlap + optional model review；
- 结果需要人工 source verification。

边界：

- alignment 不是 verified original source；
- original_source_candidate 仍需人审确认；
- similar material 不能混成原文。

### C. material_transformation_hypothesis

输入：

- aligned source/gold pairs；
- reconstructed gold；
- candidate spans。

输出：

- `material_transformation_hypothesis.json`
- `material_transformation_report.md`

节奏映射：

- 类似 bootstrap_discovery；
- 只提出材料转换轴假设；
- 不能直接变成 material_card 字段。

边界：

- 模型可以提出“原文到真题材料”的转换假设；
- 只能是 hypothesis；
- 不写正式 material_card。

### D. material_cleaning_recipe_draft

输入：

- transformation hypothesis；
- fetched body；
- alignment result。

输出：

- `material_cleaning_recipe_draft.json`
- `material_cleaning_recipe_report.md`

节奏映射：

- 类似 formal_patch_draft；
- 只生成 cleaning/slicing recipe 草案。

边界：

- `draft_only`；
- `formalized=false`；
- `writeback_allowed=false`。

### E. material_quality_stats + material_span_candidates

输入：

- fetched bodies；
- cleaned candidate spans；
- gold material；
- alignment results。

输出：

- `material_quality_stats.json`
- `material_span_candidates.jsonl`
- `material_quality_report.md`

节奏映射：

- 类似 truth_gold_regression；
- 统计是质量 evidence，不是质量真相。

边界：

- 统计不能替代语义判断；
- candidate span 不是生产材料；
- 质量分数不能自动 approve。

### F. material_card_draft

输入：

- cleaning recipe draft；
- material stats；
- source/gold alignment；
- truth_gold_regression；
- user review。

输出：

- `material_card_draft.json`
- `material_card_draft_report.md`

节奏映射：

- 类似 formal_patch_draft；
- 汇总材料机制草案，但不写正式配置。

边界：

- `draft_only`；
- `formalized=false`；
- 不写 `card_specs`；
- 需要 material regression 后才能进入写回计划。

### G. material_writeback_plan / diff / executor

输入：

- approved material_card_draft；
- material regression report；
- human approval。

输出：

- `material_writeback_plan.json`
- `material_writeback_diff.md`
- rollback patch；
- guarded writeback manifest。

节奏映射：

- 必须镜像 formal_writeback_plan / formal_writeback_executor；
- 不允许 draft 直接 writeback；
- executor 只写 allowlist 内目标。

边界：

- 必须 explicit approval；
- 必须 regression pass；
- 必须 rollback；
- 不能改题卡线，除非另有跨线批准。

## 14. material_card 写回前需要什么 regression

材料卡写回前至少需要：

- source/gold alignment regression；
- material span quality regression；
- truth_gold_regression generated comparison；
- insurance holdout 检查；
- source contamination risk 检查；
- duplicate / near-duplicate 检查；
- boilerplate ratio 检查；
- fetched body hash 稳定性检查；
- 旧三大题型 smoke，确认材料线写回不污染旧题型；
- word_usage 新链路回归；
- material generation trial，小样本验证新材料卡不会只复刻原题。

特别注意：

- high overlap 不等于质量好；
- low contamination 不等于原文确认；
- material stats 不等于语义裁决；
- model positive review 不等于 approval。

## 15. 模型 / 机械 / 人工职责边界

### 模型可以做

- source/gold 语义对齐建议；
- 原文到真题材料转换假设；
- cleaning / slicing recipe baseline；
- material_card_draft 草案；
- 失败原因解释；
- 风险提示和需要人审的样本标记。

### 模型不能做

- 自动确认原文；
- 自动入库；
- 自动写 material_card；
- 自动设置 `verified=true`；
- 自动设置 `verified_original_source=true`；
- 自动改题卡线；
- 未经 regression / 人审直接落位。

### 机械可以做

- fetch metadata；
- hash；
- duplicate detection；
- domain risk；
- content length；
- boilerplate ratio；
- overlap score；
- basic segmentation；
- stats aggregation；
- artifact / report 生成。

### 机械不能做

- 判定语义可用；
- 判定原文已确认；
- 把统计当作质量真相；
- 替代人审；
- 把相似材料自动升格为原文。

### 人工必须做

- source review；
- crawl approval；
- source verification；
- risky source approval；
- material_card approval；
- material writeback approval。

## 16. 材料线和题卡线关系

材料线可以产出 evidence，题卡线可以引用 evidence。

允许：

- 题卡线 patch payload 引用材料线 artifact 路径；
- review 时比较材料线 evidence 和题卡线 evidence；
- 人工确认后，把材料线结论纳入 formal_patch_draft 或 material_card_draft；
- material_card_draft 在写回计划里作为独立材料配置候选。

禁止：

- 材料线自动改 `question_card`；
- 材料线自动改 `prompt_assets`；
- 材料线自动改 `validator_contract`；
- 材料线自动改 `runtime_mapping`；
- material_card_draft 自动变正式 material_card；
- source seed 自动进材料库；
- fetched body 自动进 passage_service；
- alignment score 自动触发题卡写回。

所有跨线影响必须经过：

```text
review
-> regression
-> writeback plan / diff
-> explicit approval
-> guarded executor
```

## 17. 如何让用户决策成为一等 artifact

材料线至少应把三类用户决策做成一等 artifact：

1. `source_candidate_review_decisions.json`
   - 用户判断 URL 是原文候选、相似材料、域名种子、题库页、无关或暂缓。

2. `crawl_approval_decisions.json`
   - 用户明确批准哪些 seed 可以抓正文，抓取范围和限制是什么。

3. `material_card_approval.json`
   - 用户明确批准某个 material_card_draft 可以进入写回计划或执行器。

这些 artifact 应和 axis decision 一样：

- 有 reviewer；
- 有 reviewed_at；
- 有 rationale；
- 有 accepted / rejected / deferred；
- 有 limits；
- 不自动 formalize；
- 可被 promotion evidence 引用。

## 18. 如何避免模型材料基线未经验证直接落位

约束方式：

- 所有模型输出必须带 `hypothesis` 或 `draft_only`；
- 所有模型输出必须 `formalized=false`；
- 所有模型输出必须 `writeback_allowed=false`；
- 模型输出只能进入 report / draft；
- formal writeback 必须来自 writeback_plan；
- writeback_plan 必须引用 regression report；
- executor 必须检查 explicit approval；
- executor 必须只写 allowlist；
- shared config 默认拒绝或需要更高批准。

## 19. 如何避免机械统计变成语义裁决

约束方式：

- 每个统计字段必须标 method / limitation；
- report 中明确“统计不是语义确认”；
- source/gold alignment 不能只看 overlap；
- boilerplate ratio / length / hash / domain risk 只能作为风险提示；
- high score 不能自动 approve；
- low score 不能自动 reject；
- final source verification 只能由人工完成；
- material_card approval 只能由人工完成。

## 20. 推荐下一刀

推荐下一刀：

```text
crawl_approval + source_body_fetch audit_plan
```

不是直接实现抓取，而是先写审计与执行计划。

该计划应回答：

- 哪些 seed 可以被批准抓取；
- crawl approval JSON 怎么设计；
- 是否允许 risky seed；
- 抓取范围如何限制；
- 是否允许重定向；
- 是否保存正文；
- 如何 hash / 去重；
- 如何记录失败；
- 如何保证 `verified_original_source=false`；
- 如何生成 `source_body_fetch_results.jsonl`；
- 如何进入 source_gold_alignment；
- 如何避免入库和 material_card 写回。

下一刀成功标准不是“抓到很多网页”，而是：

- 有清晰 approval artifact；
- 有 bounded fetch artifact 设计；
- 有 source body evidence 边界；
- 有不入库、不确认原文、不写材料卡的硬约束；
- 能为下一步 source/gold alignment 提供正文输入。

## 21. 本轮边界声明

本轮只做审计与执行计划文档。

本轮没有：

- 改代码；
- 抓网页正文；
- 实现爬虫；
- 做 source alignment；
- 做 material_card draft；
- 写 material library；
- 写 `card_specs`；
- 新增 API / UI；
- 新增 promotion target；
- 修改 generation / validator / prompt / runtime 逻辑。


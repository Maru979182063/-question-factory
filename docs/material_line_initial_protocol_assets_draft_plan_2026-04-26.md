# 材料线初始协议资产整理与草案生成计划

日期：2026-04-26

## 1. 本轮目标

本轮只整理下一阶段材料蒸馏需要的初始协议资产草案，不执行网络访问，不确认原文，不写正式 `card_specs`，不修改 `generation` / `validator` / `prompt` / `runtime` 主链。

当前材料线已经有一条可审计证据链：

```text
gold_reconstruction
-> source_discovery_preparation
-> source_candidate_search
-> source_candidate_human_review
-> source_seed_registry
```

下一阶段不是新建一个材料服务，而是把这些证据整理成能接入现有 `passage_service` 和 `prompt_skeleton_service` 材料桥接层的协议草案。也就是说，目标是让新题型的材料线能落到已有系统：

- `passage_service`：文章 ingest / segment / tag / process / material search / promote / feedback / crawl。
- `prompt_skeleton_service`：通过 `MaterialBridgeV2` 和 `/materials/v2/search` 请求材料。
- `card_specs/normalized/material_cards`：正式材料卡最终落位处，但本轮不写。
- `card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml`：蒸馏侧题型到材料卡的运行映射最终落位处，但本轮不写。

## 2. 现有材料入库服务落位点

### 2.1 passage_service 现有能力

现有 `passage_service` 已经支持：

- `POST /articles/ingest`：文章入库。
- `POST /articles/{article_id}/segment`：文章切片。
- `POST /articles/{article_id}/tag`：材料标签。
- `POST /articles/{article_id}/process`：处理流水线。
- `POST /articles/{article_id}/review-export`：人工复核导出。
- `POST /materials/search`：旧材料池搜索。
- `POST /materials/v2/search`：V2 材料池搜索。
- `POST /materials/promote`：材料 promotion。
- `POST /materials/reprocess`：材料重处理。
- `POST /materials/feedback`：材料反馈。
- `POST /crawl/run` / `POST /crawl/source/{source_id}/run`：已有爬取入口。

因此材料线后续要做的是生成这些入口需要的证据、决策和配置草案，而不是另起一个 crawler / material library。

### 2.2 生成侧材料桥接点

`prompt_skeleton_service/configs/question_runtime.yaml` 当前材料配置包含：

- `materials.base_url`
- `materials.v2_search_path`
- `materials.default_status`
- `materials.default_release_channel`
- `materials.review_gate_mode`
- `materials.candidate_pool_size`

`MaterialV2SearchRequest` 当前可承载的关键字段包括：

- `business_family_id`
- `question_card_id`
- `business_card_ids`
- `preferred_business_card_ids`
- `query_terms`
- `topic`
- `text_direction`
- `document_genre`
- `material_structure_label`
- `target_length`
- `length_tolerance`
- `structure_constraints`
- `status`
- `release_channel`
- `review_gate_mode`

所以 `material_card_draft` 不应该发明一套孤立字段，而应尽量把字段映射到这些现有检索与桥接参数。

## 3. material_card_draft 字段框架草案

`material_card_draft` 是材料卡草案，不是正式材料卡。建议第一版结构如下：

```json
{
  "draft_version": "v1",
  "asset_type": "material_card_draft",
  "status": "draft_only",
  "formalized": false,
  "writeback_allowed": false,
  "material_card_id_draft": "proto.word_usage.content_word.material.v0",
  "family_binding": {
    "mother_family_id": "word_usage",
    "child_family_id": "word_usage_content_word",
    "business_subtype": "word_usage_content_word",
    "question_focus": "word_usage",
    "question_card_reference": "proto.word_usage.content_word.v0"
  },
  "evidence_refs": {
    "gold_reconstruction_results_path": "",
    "source_discovery_queries_path": "",
    "source_candidate_results_path": "",
    "source_candidate_review_path": "",
    "source_seed_registry_path": "",
    "crawl_seed_manifest_path": "",
    "source_body_fetch_results_path": "",
    "source_gold_alignment_results_path": ""
  },
  "source_policy": {
    "allowed_source_uses": [
      "original_source_candidate",
      "similar_material",
      "domain_seed"
    ],
    "requires_source_verification_before_formalization": true,
    "allow_question_bank_sources": false,
    "verified_original_source_required_for_original_source_claim": true
  },
  "material_requirements": {
    "document_genre_candidates": [],
    "likely_source_type": [],
    "material_structure_label_candidates": [],
    "target_length": null,
    "length_tolerance": 120,
    "context_dependency": "",
    "must_contain": [],
    "must_avoid": [
      "题库页",
      "答案解析页",
      "公考培训站包装文本"
    ],
    "usable_for_family": "word_usage",
    "usable_for_leaf": "word_usage_content_word"
  },
  "cleaning_and_slicing_recipe_ref": {
    "material_cleaning_recipe_draft_path": "",
    "span_candidate_policy_path": "",
    "draft_only": true
  },
  "quality_gate_draft": {
    "min_chars": 150,
    "min_sentences": 4,
    "min_independence_score": 0.48,
    "min_information_density": 0.35,
    "requires_material_quality_regression": true,
    "requires_human_material_review": true
  },
  "material_bridge_mapping_draft": {
    "business_family_id": "word_usage",
    "question_card_id": "proto.word_usage.content_word.v0",
    "business_card_ids": [],
    "preferred_business_card_ids": [],
    "query_terms": [],
    "topic": "",
    "text_direction": "",
    "document_genre": "",
    "material_structure_label": "",
    "structure_constraints": {},
    "review_gate_mode": "stable_relaxed",
    "status": "promoted",
    "release_channel": "stable"
  },
  "regression_requirements": {
    "truth_gold_regression_required": true,
    "material_quality_regression_required": true,
    "insurance_holdout_required": true,
    "generated_comparison_required_before_formal_writeback": true
  },
  "approval_requirements": {
    "source_review_decision_required": true,
    "crawl_approval_required_before_fetch": true,
    "source_verification_required_before_original_claim": true,
    "material_card_approval_required_before_writeback": true,
    "writeback_plan_required": true,
    "rollback_patch_required": true
  }
}
```

关键边界：

- `material_card_draft` 只能是 draft。
- `material_card_id_draft` 可以带 `proto`，但不能写入正式 material card 列表。
- `material_bridge_mapping_draft` 只是未来接入 `MaterialV2SearchRequest` 的映射草案。
- `quality_gate_draft` 可以参考 `passage_service/app/config/material_governance.yaml` 的现有阈值，但不能替代人工质量判断。
- `source_seed_registry` 仍然是 seed-only，不是材料库。

## 4. material_line_prompt_assets 草案

`material_line_prompt_assets` 是材料线提示词草案包，不是正式 prompt assets。本轮只定义草案资产形态：

```json
{
  "prompt_asset_version": "v1",
  "asset_type": "material_line_prompt_assets_draft",
  "status": "draft_only",
  "formalized": false,
  "writeback_allowed": false,
  "prompts": {
    "source_evidence_review": {
      "purpose": "辅助人工判断候选来源是否值得进入 seed registry 或后续 crawl approval。",
      "model_role": "谨慎的材料来源证据审查助手",
      "allowed_actions": [
        "总结 URL/title/snippet/domain 与 reconstructed gold 的关系",
        "指出题库/培训站污染风险",
        "区分 original_source_candidate 与 similar_material",
        "列出需要人工打开网页确认的问题"
      ],
      "forbidden_actions": [
        "确认原文",
        "输出 verified=true",
        "批准抓正文",
        "写 material_card",
        "影响题卡线"
      ]
    },
    "source_gold_alignment": {
      "purpose": "在已有正文后，对 source body 与 reconstructed gold 做语义对齐建议。",
      "model_role": "source/gold 对齐分析助手",
      "allowed_actions": [
        "标记可能重合片段",
        "解释 gold material 可能来自 source body 的哪一段",
        "判断更像原文、转载、相似材料还是不匹配",
        "输出 needs_human_review"
      ],
      "forbidden_actions": [
        "自动确认 verified_original_source",
        "自动入库",
        "自动生成正式 material_card"
      ]
    },
    "material_transformation_hypothesis": {
      "purpose": "提出原文到真题材料的转换假设。",
      "model_role": "材料转换机制分析助手",
      "allowed_actions": [
        "说明原文可能如何被截取、压缩、去噪或改写",
        "提出清洗/切片假设",
        "指出证据不足和人工确认点"
      ],
      "forbidden_actions": [
        "把 hypothesis 当 formal rule",
        "写 validator 规则",
        "写 prompt guard",
        "写正式 material_card"
      ]
    },
    "material_quality_review": {
      "purpose": "辅助人工审查候选材料是否适合该题型的材料生产。",
      "model_role": "材料质量审查助手",
      "allowed_actions": [
        "从可读性、信息密度、上下文完整性、可出题性、污染风险角度提出审查意见",
        "标记高风险样本",
        "建议进入下一轮 regression 的维度"
      ],
      "forbidden_actions": [
        "替代人工审批",
        "自动 promote",
        "自动写入 passage material pool"
      ]
    },
    "material_card_draft": {
      "purpose": "基于已确认 evidence 生成材料卡草案。",
      "model_role": "材料卡草案整理助手",
      "allowed_actions": [
        "整理字段草案",
        "引用 evidence paths",
        "说明待验证项",
        "输出 draft_only JSON"
      ],
      "forbidden_actions": [
        "写正式 card_specs",
        "修改 runtime mapping",
        "修改 question_card/prompt/validator"
      ]
    }
  }
}
```

这些提示词后续可以进入 prompt 资产管理，但必须先经过：

```text
draft
-> small smoke
-> human review
-> regression
-> writeback plan / diff
-> explicit approval
-> guarded executor
```

## 5. 人工审核提示词草案

### 5.1 Source Review 人审提示词

用途：用户审查 `source_candidate_results.jsonl` 里的候选 URL。

建议提示：

```text
请只判断这个候选来源的用途，不要确认它就是原文。

你需要回答：
1. 这个 URL 更像原文候选、相似材料、域名种子、题库/培训站，还是无关页面？
2. 如果保留，保留理由是什么？
3. 是否打开过网页？如果没有，human_opened_url 必须为 false。
4. 是否存在题库、答案解析、公考培训、刷题站污染？
5. 是否允许它进入后续 crawl approval 候选？注意：这不是抓取批准。

允许 decision：
- keep_as_original_source_candidate
- keep_as_similar_material_seed
- keep_as_domain_seed
- reject_question_bank
- reject_irrelevant
- defer

禁止输出：
- verified=true
- verified_original_source=true
- crawl_allowed=true
- material_card approval
```

### 5.2 Source Evidence Review 人审提示词

用途：在正文抓取和 source/gold alignment 之后，用户审查证据是否足够。

建议提示：

```text
请判断 source body 与 reconstructed gold 的证据关系。

你需要区分：
1. 可能原文
2. 转载或改写来源
3. 相似主题材料
4. 题库/解析污染页
5. 不相关页面

即使 alignment score 较高，也不要自动确认原文。
只有当人工打开页面、检查正文、确认来源关系后，后续 source verification 才能进入下一步。

输出必须包含：
- evidence_decision
- rationale
- uncertain_points
- needs_additional_source
- allowed_next_step

禁止直接写 material_card 或材料库。
```

### 5.3 Material Quality Review 人审提示词

用途：审查 candidate span / cleaned material 是否适合进入材料卡草案。

建议提示：

```text
请审查这段候选材料是否适合当前题型的材料生产。

重点看：
1. 是否像自然文章材料，而不是题库包装文本？
2. 上下文是否足够完整？
3. 是否有可出题的语义焦点？
4. 是否有足够信息密度？
5. 是否存在明显背景缺口？
6. 是否过度贴近真题导致过拟合？
7. 是否能支持 word_usage_content_word 的材料需求？
8. 是否需要清洗、截断、补上下文或放弃？

输出只能是 review decision 和修改建议。
不能输出正式 material_card，不能写入材料库。
```

## 6. material_quality_regression 初始评测维度

第一版 `material_quality_regression` 不应宣称“判断真题质量”，它只做可记录、可复盘的材料质量闭环。建议维度如下：

| 维度 | 目的 | 方法 | 局限 |
| --- | --- | --- | --- |
| source_provenance_status | 区分 seed、fetched、aligned、human verified | metadata + human review | 不能单靠 URL 判断原文 |
| question_bank_contamination | 识别题库/解析/培训站污染 | domain/title/snippet/body 关键词 + 人审 | 可能误伤考试评论文章 |
| source_gold_alignment | 判断 source body 与 reconstructed gold 是否有证据重合 | overlap + model alignment + human review | alignment 高不等于 verified |
| material_independence | 判断候选材料是否脱离题库包装 | heuristic + human review | 机械只能提示风险 |
| material_sufficiency | 判断材料长度、上下文、信息密度是否足够 | min chars/sentences/info density | 不代表语义可用 |
| slicing_quality | 判断切片边界是否保留必要上下文 | segmentation stats + model review | 需要人工抽检 |
| family_fit | 判断是否适合目标题型/叶族 | gold evidence + material card draft | 不能替代题卡线确认 |
| distractor_support | 判断材料是否支持构造有效干扰项 | model review + generated comparison | 初期置信度低 |
| overfit_or_copy_risk | 判断是否过度复刻真题 | lexical overlap + holdout comparison | 高相似可能是原文，也可能是污染 |
| bridge_compatibility | 判断是否能映射到 `/materials/v2/search` 参数 | schema check | 只证明可接入，不证明质量好 |
| insurance_holdout_performance | 防止只贴合训练样本 | split regression | 样本少时不稳定 |

每个评分必须保留：

- `method`: `heuristic | model | human | metadata | unavailable`
- `confidence`: `low | medium | high`
- `limitation`
- `needs_human_review`

## 7. material_card 与 question_card / prompt / validator 的引用边界

### 7.1 material_card 可以引用什么

`material_card_draft` 可以引用：

- `question_card_id`，用于说明服务哪个题型，但不能修改 question card。
- `business_family_id` / `business_subtype`，用于材料检索绑定。
- `business_card_ids` / `preferred_business_card_ids`，用于 `MaterialV2SearchRequest`。
- `query_terms` / `topic` / `document_genre` / `material_structure_label`，用于材料池检索。
- `structure_constraints` / `target_length` / `length_tolerance`，用于材料桥接。
- `gold_reconstruction` / `source_seed_registry` / `source_gold_alignment` / `material_quality_regression` 证据路径。

### 7.2 material_card 不能做什么

`material_card_draft` 不能：

- 修改 `question_card`。
- 修改 `prompt_assets`。
- 修改 `validator_contract`。
- 修改 `runtime_mapping`。
- 自动新增 promotion target。
- 自动写 `card_specs/normalized/material_cards`。
- 自动写 `distill_material_card_id_mapping.yaml`。
- 自动 promote passage material。
- 自动把 source seed 当作 verified source。

### 7.3 正式接入时的唯一合理路径

未来如果要把材料卡正式接入，应走：

```text
material_card_draft
-> material_quality_regression
-> material_writeback_plan
-> material_writeback_diff
-> rollback patch
-> explicit material approval
-> guarded material writeback executor
-> targeted regression
```

写回候选位置应优先限制在：

- 新增隔离 proto material card 文件。
- 新增或补充受控 runtime mapping 草案。
- passage service 已有 material card registry 可读取的位置。

共享配置、旧题型材料卡、正式 prompt、正式 validator 都不能在第一批写回中被改动。

## 8. 后续如何用已确认材料来源证据继续迭代

后续迭代应围绕“证据升级”，而不是围绕“马上入库”。

建议证据升级链：

```text
source_seed_registry
-> crawl approval
-> source_body_fetch
-> source_gold_alignment
-> human source verification
-> material_transformation_hypothesis
-> material_cleaning_recipe_draft
-> material_span_candidates
-> material_quality_regression
-> material_card_draft
-> material_writeback_plan / diff
-> explicit approval
-> guarded writeback
```

每一级只允许把证据推进一级：

- seed 只能进入 crawl approval。
- crawl approval 只能允许小范围抓正文。
- fetched body 只能进入 alignment。
- alignment 只能产出 evidence，不自动 verified。
- human source verification 才能把来源关系升级。
- cleaning recipe 只能是 draft。
- material span candidate 不是生产材料。
- material quality regression 不是 formal approval。
- material_card_draft 不是正式 material_card。
- writeback plan 不是 writeback。

这条链的好处是：用户的判断会成为一等 artifact，模型的建议会被回归和人审约束，机械统计只做辅助，不会变成语义裁决。

## 9. 下一阶段建议

下一刀建议不是直接做 material_card，也不是直接写 passage material pool，而是先做：

```text
crawl approval + source_body_fetch audit / plan
```

原因：

- 当前已有 `source_seed_registry`，但 `crawl_seed_manifest.crawl_allowed=false`。
- 没有正文，就不能做 source/gold alignment。
- 没有 alignment，就不能理解原文到真题材料的转换机制。
- 没有转换机制和质量回归，就不能生成可靠的 material_card_draft。
- 已有 `passage_service` 提供 crawl / ingest / process 能力，下一步应当设计受控接入方式，而不是新造服务。

下一刀文档应重点回答：

- 哪些 seed 允许进入 crawl approval？
- crawl approval JSON 需要哪些字段？
- 如何调用或对接已有 `passage_service` crawl / ingest，而不是新写 crawler？
- 抓取正文后如何记录 hash、状态码、content type、长度、失败原因？
- 如何保持 `verified_original_source=false`？
- 如何把 fetch result 作为 evidence 进入后续 source/gold alignment？

## 10. 本轮边界声明

本轮只产出材料线初始协议资产草案。

本轮没有：

- 网络访问。
- 原文确认。
- 正文抓取。
- crawler 执行。
- 材料库写入。
- `material_card` 正式写回。
- `card_specs` 修改。
- `question_card` 修改。
- `prompt_assets` 修改。
- `validator_contract` 修改。
- `runtime_mapping` 修改。
- `generation` / `validator` / `prompt` / `runtime` 主链修改。


# material_protocol_draft LLM 真实返回调试报告

日期：2026-04-27

## 1. 本轮目标

用户希望看到真实 LLM 返回，而不是只看 mock 或 blocked report。

本轮在不写正式配置、不抓正文、不入库、不改主链的前提下，对 `material_protocol_draft` 做了一次最小 prompt hardening，并重新执行 LLM smoke。

## 2. 修改内容

修改文件：

- `tools/leaf_pre_distill/material_protocol_draft_prompt.py`

修改点：

- 要求模型逐字复制 `EVIDENCE_DIGEST.family_context` 到 `material_card_draft.family_binding`。
- 要求 `material_bridge_mapping_draft` 明确包含 `system_alignment_findings_ref="system_alignment_findings.json"`。
- 要求 `mapping_rationale.source="system_alignment_findings"`。

原因：

- 上一次 LLM 已经返回 JSON，但被 checker 拦下；
- 主要问题是模型改写了 family binding，并漏了 system alignment 引用；
- 这属于 prompt 约束不够硬，不是接口不可用。

## 3. LLM 调用结果

输出目录：

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke_prompt_hardened`

生成文件：

- `system_alignment_findings.json`
- `material_protocol_draft_input_digest.json`
- `material_card_draft.json`
- `material_line_prompt_assets_draft.json`
- `material_quality_regression_draft.json`
- `material_bridge_mapping_draft.json`
- `material_review_prompts.md`
- `material_protocol_assets_draft_report.md`

结论：

- 真实 LLM 返回成功；
- JSON 解析成功；
- checker 通过；
- draft artifacts 已落盘；
- 没有写假草案。

## 4. evidence gaps

`material_protocol_draft_input_digest.json.missing_evidence=[]`

本轮完整 evidence 已进入 digest：

- `manifest`
- `gold_reconstruction_results`
- `truth_gold_regression_results`
- `truth_gold_split_manifest`
- `source_discovery_queries`
- `material_source_profile`
- `source_candidate_summary`
- `source_candidate_review`
- `source_seed_registry`
- `crawl_seed_manifest`
- `initial_plan_doc`

## 5. material_card_draft 摘要

真实 LLM 输出保持：

- `status=draft_only`
- `formalized=false`
- `writeback_allowed=false`
- `requires_human_review=true`
- `requires_regression=true`

family binding 已正确复制：

```json
{
  "mother_family_id": "word_usage",
  "child_family_id": "word_usage_content_word",
  "leaf_label": "实词",
  "business_subtype": "word_usage_content_word",
  "question_focus": "word_usage",
  "question_card_reference": null,
  "material_card_id_draft": "proto.word_usage.word_usage_content_word.material.v0"
}
```

真实 LLM 输出中包含的有效信息：

- 识别当前还没有该 family 的 repository-confirmed material card schema；
- 将当前草案定位为 hypothesis-only / proposed-draft；
- 引用了 gold reconstruction、truth gold、source discovery 的证据摘要；
- 标记 source candidate / review / seed registry 仍未 ready for material_card_draft；
- 没有声称 source seed 已 verified；
- 没有声称已有 source body；
- 没有声称已有 source/gold alignment。

需要注意：

- LLM 没有按 mock 草案的 `evidence_refs` 字段列出路径；
- 它改用 `evidence_backed` 与 `draft_fields.*.evidence_basis` 表达证据来源；
- 这说明真实模型语义上引用了 evidence，但结构上仍需要下一步 schema hardening。

## 6. prompt_assets_draft 摘要

真实 LLM 输出保持：

- `status=draft_only`
- `formalized=false`
- `writeback_allowed=false`
- `requires_human_review=true`
- `requires_regression=true`

输出中包含：

- `material_search_intent_template`
- `material_screening_template`

有效信息：

- 明确材料检索目标不能假设 universal family rules；
- 明确不能假设 verified originals already available；
- 明确不能把当前 source candidates 当 production ready；
- 标记后续需要 source body、source-to-gold alignment、human-reviewed fit criteria。

需要注意：

- LLM 没有完整输出原定五类 prompt：
  - `source_evidence_review`
  - `source_gold_alignment`
  - `material_transformation_hypothesis`
  - `material_quality_review`
  - `material_card_draft`
- 这不越权，但不满足理想 prompt asset contract。

## 7. material_quality_regression_draft 摘要

真实 LLM 输出保持：

- `status=draft_only`
- `formalized=false`
- `writeback_allowed=false`
- `requires_human_review=true`
- `requires_regression=true`

输出中包含：

- `source_presence_check`
- `family_fit_check`
- `question_support_check`
- `regression_consistency_check`

有效信息：

- 能识别当前 truth gold regression 是 `gold_only_baseline`；
- 能识别 truth gold split sample count；
- 明确 blocking conditions：
  - 未有 verified original source；
  - 未有 source/gold alignment；
  - 未有 material quality regression。

需要注意：

- LLM 没有按预期输出 `dimensions` 数组；
- 没有逐项给出 `method/confidence/limitation`；
- 这说明真实返回可读，但还需要 schema hardening，才能进入稳定 human review。

## 8. bridge_mapping_draft 摘要

真实 LLM 输出：

- `target_runtime=MaterialV2SearchRequest`
- `system_alignment_findings_ref=system_alignment_findings.json`
- checker 已通过 system alignment 引用要求。

有效信息：

- 没有修改 `question_runtime.yaml`；
- 没有调用 `/materials/v2/search`；
- 没有写 runtime mapping。

需要注意：

- 真实 LLM 输出没有完整列出 `confirmed_repository_fields_used`；
- 下一步可以要求 prompt 明确复制 `system_alignment_findings.recommended_minimal_compatible_mapping.confirmed_fields`。

## 9. hardcoded family 风险

检查结果：

- 当前 family context 是本次 artifact 的样例值；
- 真实返回没有把 `word_usage` 声称为通用规则；
- 输出中多次出现“not universal / observed sample only / hypothesis-only”。

判断：

- 未发现明显 hardcoded family 风险。

## 10. source seed 被误当 verified source 风险

检查结果：

- 未出现 `verified=true`；
- 未出现 `verified_original_source=true`；
- 未出现 `crawl_allowed=true`；
- 未声称 source body 已存在；
- 未声称 source/gold alignment 已完成。

判断：

- 未发现 source seed 被误当 verified source。

## 11. formalization 越权风险

检查结果：

- 未出现 `formalized=true`；
- 未出现 `writeback_allowed=true`；
- 未出现 `card_specs_write=true`；
- 未出现 `promotion_allowed=true`；
- 未写 material_card；
- 未写 card_specs；
- 未写 runtime mapping；
- 未写 prompt_assets；
- 未写 validator；
- 未改 question_card。

判断：

- 未发现 formalization 越权。

## 12. 当前真实返回的判断

这次真实 LLM 返回是有意义的：

- 它吃到了完整 evidence；
- 它保持了 draft 边界；
- 它没有把 source seed 当 verified；
- 它知道当前还缺 source body / source-gold alignment / material quality regression；
- 它能给出材料检索和材料筛选的草案方向。

但它还不能直接进入 material_protocol_draft human review 的正式节奏，因为结构契约还不稳定：

- `evidence_refs` 没有按固定字段输出；
- prompt assets 没按五类 prompt 输出；
- quality regression 没按 dimensions schema 输出；
- bridge mapping 没完整复述 confirmed fields。

## 13. 下一步建议

下一刀建议做非常小的 schema hardening：

1. prompt 里给出更具体的 output schema，不允许替换字段名；
2. checker 增加非空要求：
   - `material_card_draft.evidence_refs` 必须非空；
   - `material_line_prompt_assets_draft.prompts` 必须包含五类 prompt；
   - `material_quality_regression_draft.dimensions` 必须非空；
   - `material_bridge_mapping_draft.confirmed_repository_fields_used` 必须非空；
3. 再跑一次单次 LLM smoke。

如果下一次真实返回也通过这些更严格要求，就可以进入 material_protocol_draft human review。

## 14. 本轮明确未做事项

本轮只调用 LLM endpoint 获取真实材料协议草案返回。

本轮没有：

- 网页搜索；
- 正文抓取；
- source verification；
- source/gold alignment；
- passage_service ingest；
- material promotion；
- material_card 写回；
- card_specs 写回；
- runtime mapping 写回；
- prompt_assets 正式写回；
- validator 写回；
- question_card 修改；
- generation / validator / prompt / runtime 主链修改；
- API / UI 修改；
- 新增 promotion target。


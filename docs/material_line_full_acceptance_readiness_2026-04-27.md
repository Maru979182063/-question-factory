# Material Line Full Acceptance Readiness Report

## Status

Completed as a bounded material-line acceptance run.

This run used user-reviewed source seeds to produce source text evidence, ran LLM-assisted source/gold alignment, ran material quality regression, and attached the resulting evidence to the new-leaf formalization packet and readiness gate.

The result is intentionally **blocked** for material-card formalization. The chain ran, but the available source text does not yet provide strong enough source/gold alignment to support material-card review readiness.

## Modified Files

- `tools/leaf_pre_distill/material_evidence_alignment_regression.py`
- `tools/leaf_pre_distill/run.py`
- `tools/leaf_pre_distill/new_leaf_formalization_packet.py`
- `tools/leaf_pre_distill/formalization_readiness_gate.py`
- `docs/material_line_full_acceptance_readiness_2026-04-27.md`

## Output Directory

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1`

Generated artifacts:

- `source_text_evidence_approval.json`
- `manual_source_texts.jsonl`
- `source_text_evidence_manifest.json`
- `source_text_evidence_results.jsonl`
- `source_text_evidence_report.md`
- `source_gold_alignment_results.jsonl`
- `source_gold_alignment_summary.json`
- `source_gold_alignment_report.md`
- `source_gold_alignment_review.json`
- `material_quality_regression_results.json`
- `material_quality_regression_report.md`
- `material_quality_review.json`
- `agent_review_feedback_input.json`
- `agent_review_feedback_normalized.json`
- `agent_review_feedback_report.md`
- `new_leaf_formalization_packet.json`
- `new_leaf_formalization_packet_report.md`
- `runtime_activation_plan.json`
- `runtime_activation_plan_report.md`
- `formalization_readiness_checklist.json`
- `formalization_readiness_report.md`

## Inputs Used

Source seed evidence:

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_seed_registry.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/crawl_seed_manifest.json`

Gold and material evidence:

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_card_draft.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_quality_regression_draft.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_bridge_mapping_draft.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_regression_results.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_split_manifest.json`

## Source Text Evidence

Mode: `manual`

The run required `source_text_evidence_approval.json` before preparing text evidence. The approval scope was:

`prepare_source_text_evidence_only`

This approval did not confirm original source, did not allow material library write, and did not allow material-card write.

Approved seeds:

| seed_id | source_use | url | text_status | text_length |
| --- | --- | --- | --- | --- |
| `source_seed_8ba951e15ddc8257` | `similar_material` | `https://www.nju.edu.cn/info/3191/215671.htm` | `available` | 166 |
| `source_seed_a10a0cb29a5c0da5` | `original_source_candidate` | `https://digitalhumanities.nju.edu.cn/publication/5eddb5c68c265c25e6/` | `available` | 2600 |

Evidence summary:

- `approved_seed_count`: 2
- `available_count`: 2
- `manual_required_count`: 0
- `verified_count`: 0
- `verified_original_source_count`: 0
- `ready_for_source_gold_alignment`: true

Notes:

- The Nanjing University CO2 source used a local/manual excerpt derived from available source metadata because direct fetch was not reliable in this smoke.
- The digital humanities source had a longer locally prepared text excerpt.
- Both rows remain `requires_human_review=true`.
- Neither row is a verified original source.

## Source/Gold Alignment

Mode: `llm`

The LLM call was performed through an OpenAI-compatible endpoint using an environment-provided key. The key was not written to artifacts or reports.

Alignment summary:

- `alignment_count`: 2
- `status_counts`: `weak=1`, `needs_human_review=1`
- `relationship_counts`: `similar_material=1`, `topic_related=1`
- `verified_count`: 0
- `verified_original_source_count`: 0
- `ready_for_material_quality_regression`: true
- `ready_for_material_card_draft`: false

Sample-level result:

| seed_id | relationship | alignment_status | confidence | judgment |
| --- | --- | --- | --- | --- |
| `source_seed_8ba951e15ddc8257` | `similar_material` | `weak` | `low` | CO2 / plant-growth topic is related, but the available excerpt does not cover the reconstructed greenhouse-effect argument strongly enough. |
| `source_seed_a10a0cb29a5c0da5` | `topic_related` | `needs_human_review` | `low` | The source is about digital humanities, but the provided excerpt does not include a direct match to the reconstructed gold passage. It may require fuller text review. |

Boundary result:

- No alignment row set `verified=true`.
- No alignment row set `verified_original_source=true`.
- `original_source_candidate` remained unverified.
- `similar_material` was not treated as original source.

## Material Quality Regression

Result: `blocked`

Summary:

- `source_text_count`: 2
- `available_source_text_count`: 2
- `alignment_count`: 2
- `useful_alignment_count`: 0
- `verified_original_source_count`: 0
- `ready_for_material_card_formalization`: false

Blocking issues:

- `source_gold_alignment`
- `slicing_potential`

Important dimension outcomes:

- `question_bank_contamination`: pass
- `source_gold_alignment`: blocked
- `slicing_potential`: blocked
- `source_provenance_status`: warning
- `material_sufficiency`: warning
- `family_fit`: warning
- `bridge_compatibility`: warning
- `human_review_required`: pass

Interpretation:

The sources look cleaner than question-bank pages, but low contamination is not source verification. The available excerpts are not enough to prove original-source relation or produce reliable slicing rules. This correctly blocks material-card formalization.

## Formalization Packet Integration

`new_leaf_formalization_packet.json` now includes references to:

- `source_text_evidence_manifest`
- `source_text_evidence_results`
- `source_gold_alignment_summary`
- `source_gold_alignment_results`
- `material_quality_regression_results`

Packet material summary:

- `source_text_evidence_available`: true
- `source_text_evidence_count`: 2
- `source_gold_alignment_available`: true
- `source_gold_alignment_count`: 2
- `material_quality_regression_available`: true
- `material_quality_regression_status`: `blocked`
- `ready_for_material_card_review`: false
- `ready_for_material_card_formalization`: false
- `verified_original_source_count`: 0

The `material_card` formal target candidate remains `blocked` with these gaps:

- `material_card_formalization_not_allowed`
- `material_quality_regression_blocked`
- `verified_original_source_required_before_original_source_claim`

## Readiness Gate Integration

`formalization_readiness_checklist.json` result: `blocked`

Material line readiness:

```json
{
  "status": "blocked",
  "source_text_evidence_available": true,
  "source_gold_alignment_available": true,
  "material_quality_regression_status": "blocked",
  "material_card_formalization_allowed": false,
  "source_verified": false
}
```

Blocking checks:

- `material_quality_regression_not_blocked`
- `explicit_approval_available`
- `runtime_activation_blockers_clear`

Recommended next action:

`human_review`

## Can It Enter Material Card Draft Review?

Not as a ready material-card review package.

It can enter **human material evidence review**, focused on:

- whether the two candidate sources are meaningful enough to keep;
- whether the digital humanities source needs fuller body text;
- whether the CO2 source is only similar material rather than original source;
- whether more source text evidence should be collected before source/gold alignment is judged again.

It cannot enter material-card formalization, writeback planning, or material library ingest.

## What This Proves

This run proves the material acceptance chain now supports:

1. user-approved source text evidence preparation;
2. LLM-assisted source/gold semantic alignment;
3. material quality regression;
4. formalization packet attachment;
5. readiness gate material-line judgment.

The chain also correctly blocks when evidence is weak. That is the intended behavior.

## Boundaries Kept

This run did not:

- verify original source;
- fetch and ingest into `passage_service`;
- write a material library;
- write `material_card`;
- write `card_specs`;
- write runtime mapping;
- write prompt assets;
- write validator rules;
- change generation logic;
- add promotion targets;
- formalize source seeds.

## Next Recommended Step

Do a human material evidence review pass before any material-card review:

1. open the two candidate URLs manually;
2. decide whether either page contains the full relevant source body;
3. if yes, prepare fuller local source text evidence;
4. rerun source/gold alignment;
5. rerun material quality regression.

Only if alignment improves from `weak/needs_human_review` to `partial/aligned` should the system consider `ready_for_material_card_review`.

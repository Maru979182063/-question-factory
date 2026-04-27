# Material Quality Regression Real Evidence v1 Report

## Status

Completed with result: `blocked`.

This knife evaluated real source text evidence and source/gold alignment against the material-card draft. The regression is readiness evidence only. It is not material-card approval and cannot trigger writeback.

## Inputs

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_text_evidence_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_gold_alignment_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_gold_alignment_summary.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_card_draft.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_quality_regression_draft.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/agent_review_feedback_normalized.json`

## Output Artifacts

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/material_quality_regression_results.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/material_quality_regression_report.md`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/material_quality_review.json`

## Evidence Overview

- source_text_count: 2
- available_source_text_count: 2
- alignment_count: 2
- useful_alignment_count: 0
- verified_original_source_count: 0
- verified_count: 0
- ready_for_material_card_formalization: false

## Dimension Results

| dimension | status | method | confidence | blocking |
| --- | --- | --- | --- | --- |
| source_provenance_status | warning | heuristic | medium | true |
| question_bank_contamination | pass | heuristic | medium | false |
| source_gold_alignment | blocked | mixed | low | true |
| material_independence | warning | heuristic | low | true |
| material_sufficiency | warning | heuristic | low | true |
| context_dependency | warning | model | low | true |
| slicing_potential | blocked | heuristic | low | true |
| family_fit | warning | human | low | true |
| distractor_support | warning | unavailable | low | true |
| overfit_or_copy_risk | warning | heuristic | low | true |
| bridge_compatibility | warning | metadata | low | true |
| human_review_required | pass | human | high | true |

## Blocking Issues

- `source_gold_alignment`
- `slicing_potential`

## Interpretation

The source candidates are not obviously question-bank polluted, which is useful. But that is not enough. The current source/gold alignment is weak, and no reliable material span can be sliced yet.

Therefore:

- `ready_for_material_card_review`: false for this acceptance sample.
- `ready_for_material_card_formalization`: false.
- `recommended_next_action`: `human_material_review`.

## User Review Point

`material_quality_review.json` was generated as the next human decision point. It should allow a reviewer to accept/reject/defer the diagnosis, request more source text, request alignment revision, or later approve for material-card review.

It must not be used to:

- verify original source;
- approve formal writeback;
- write material_card;
- ingest into a material library.

## Boundary Checks

- High score cannot auto approve.
- Low contamination does not equal verified source.
- Original-source candidate does not equal verified original source.
- Material quality regression is not material-card approval.

## Not Done

This knife did not:

- verify source;
- ingest into `passage_service`;
- write material library entries;
- write `material_card`;
- write `card_specs`;
- modify runtime, prompt, validator, or generation logic.

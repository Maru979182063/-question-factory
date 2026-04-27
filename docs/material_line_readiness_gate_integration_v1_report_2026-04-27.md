# Material Line Readiness Gate Integration v1 Report

## Status

Completed.

This knife connected material-line evidence into the new-leaf formalization packet and formalization readiness gate. The gate correctly reports the current material line as `blocked`.

## Material Evidence Read

The integration used:

- `source_text_evidence_manifest.json`
- `source_text_evidence_results.jsonl`
- `source_gold_alignment_summary.json`
- `source_gold_alignment_results.jsonl`
- `material_quality_regression_results.json`
- `material_quality_regression_report.md`
- `source_gold_alignment_review.json`
- `material_quality_review.json`
- `material_card_draft.json`
- `material_bridge_mapping_draft.json`

## Packet Integration

`new_leaf_formalization_packet.json` now carries a dedicated `material_evidence_summary`.

Current summary:

- `source_text_evidence_status`: `completed`
- `source_text_evidence_count`: 2
- `source_text_available_count`: 2
- `source_text_manual_required_count`: 0
- `source_gold_alignment_status`: `completed`
- `source_gold_alignment_count`: 2
- `source_gold_alignment_needs_human_review_count`: 2
- `material_quality_regression_status`: `blocked`
- `verified_original_source_count`: 0
- `requires_source_review`: true
- `requires_alignment_review`: true
- `requires_material_quality_review`: true
- `ready_for_material_card_review`: false
- `ready_for_material_card_formalization`: false

Blocking issues carried by packet:

- `material_card_formalization_not_allowed`
- `material_quality_regression_blocked`
- `material_quality_review_required`
- `source_gold_alignment_review_required`
- `verified_original_source_required_before_original_source_claim`

## Readiness Gate Result

`formalization_readiness_checklist.json` final status: `blocked`

Material-line readiness:

- `status`: `blocked`
- `source_text_evidence_available`: true
- `source_gold_alignment_available`: true
- `material_quality_regression_status`: `blocked`
- `material_card_formalization_allowed`: false
- `source_verified`: false

Blocking checks:

- `material_quality_regression_not_blocked`
- `explicit_approval_available`
- `runtime_activation_blockers_clear`

Recommended next action:

`human_review`

## Can It Enter Material Card Review?

Not yet.

The system can enter human review of material evidence, but it should not mark the material card as review-ready. The source/gold alignment is still weak and the material quality regression is blocked.

## Formalization Boundary

The gate does not allow:

- material-card formalization;
- material-card writeback;
- card_specs writeback;
- source verification;
- passage_service ingest;
- runtime/prompt/validator/generation mutation.

## Overreach Check

No overreach field was detected:

- no source seed was treated as verified source;
- no `similar_material` was treated as original source;
- no material quality regression result was treated as material-card approval;
- no writeback permission was set.

## Next Step

The next useful step is human material evidence review:

1. inspect both candidate URLs;
2. decide whether fuller local source text should be prepared;
3. rerun source/gold alignment after fuller text is available;
4. rerun material quality regression;
5. only then reconsider material-card review readiness.

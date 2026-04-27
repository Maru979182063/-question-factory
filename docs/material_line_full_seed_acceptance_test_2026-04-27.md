# Material Line Full Seed Acceptance Test v1

## 1. Goal

Run the material-line acceptance chain over all currently human-reviewed accepted source seeds in the real `word_usage_content_word` artifact directory.

This is a full-seed run for the current artifact set. It is not a full-web search, crawler, source verification, passage-service ingest, material-card formalization, or writeback run.

## 2. Resolved Evidence Paths

Root:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425`

Inputs:

- `source_candidate_human_review_v1_fixture/source_candidate_review.json`
- `source_candidate_human_review_v1_fixture/source_seed_registry.jsonl`
- `source_candidate_human_review_v1_fixture/crawl_seed_manifest.json`
- `gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl`
- `material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_card_draft.json`
- `material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_quality_regression_draft.json`
- `material_protocol_draft_full_evidence_llm_smoke_prompt_hardened/material_bridge_mapping_draft.json`
- `truth_gold_regression_v1/truth_gold_regression_results.json`
- `truth_gold_regression_v1/truth_gold_split_manifest.json`

Output directory:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_seed_acceptance_v1`

## 3. Source Review / Seed Counts

From `source_candidate_review.json`:

- reviewed candidates: 5
- accepted: 2
- rejected: 2
- deferred: 1
- risky accepted seeds: 0
- verified original source count: 0

From `source_seed_registry.jsonl`:

- total accepted seed rows processed: 2
- seed ids:
  - `source_seed_8ba951e15ddc8257`
  - `source_seed_a10a0cb29a5c0da5`

Rejected and deferred candidates were not processed as source text evidence.

## 4. Source Text Evidence

Artifacts:

- `source_text_evidence_approval.json`
- `manual_source_texts.jsonl`
- `source_text_evidence_manifest.json`
- `source_text_evidence_results.jsonl`
- `source_text_evidence_report.md`

Run mode: `manual`

The run used local/manual text already prepared for the accepted seeds. It did not run a crawler and did not batch-fetch webpages.

Counts:

- approved_seed_count: 2
- result_count: 2
- available: 2
- manual_required: 0
- blocked: 0
- failed: 0
- verified_count: 0
- verified_original_source_count: 0

Every source text evidence row remains:

- `verified=false`
- `verified_original_source=false`
- `formalized=false`
- `requires_human_review=true`

## 5. Source/Gold Alignment

Artifacts:

- `source_gold_alignment_results.jsonl`
- `source_gold_alignment_summary.json`
- `source_gold_alignment_report.md`
- `source_gold_alignment_review.json`

Requested mode: `llm`

Actual result:

- the LLM path was attempted with an environment-provided key;
- the provider rejected the request with HTTP 401;
- no API key was written to artifacts or this report;
- the system did not fabricate semantic alignment;
- rows were downgraded to `needs_human_review` with warnings.

Alignment counts:

- total alignment rows: 2
- aligned: 0
- partial: 0
- weak: 0
- needs_human_review: 2
- blocked: 0
- irrelevant: 0

Relationship counts:

- original_source_candidate: 0
- similar_material: 0
- topic_related: 2
- question_bank_pollution: 0
- unknown: 0

Verification counts:

- verified_original_source_count: 0
- verified_count: 0

Human review required:

- both rows require human review.

Interpretation:

This is not a successful model-semantic alignment pass. It is a correct safe fallback: the system preserved the rows as review-needed evidence and did not pretend the model judged them.

## 6. Material Quality Regression

Artifacts:

- `material_quality_regression_results.json`
- `material_quality_regression_report.md`
- `material_quality_review.json`

Overall status:

`blocked`

Counts:

- source_text_count: 2
- available_source_text_count: 2
- alignment_count: 2
- useful_alignment_count: 0
- verified_original_source_count: 0
- verified_count: 0
- ready_for_material_card_formalization: false

Dimension results:

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

Blocking issues:

- `source_gold_alignment`
- `slicing_potential`

Readiness:

- ready_for_material_card_review: false
- ready_for_material_card_formalization: false

This blocked result is evidence-driven, not a system failure. The source text exists, but the source/gold alignment is not strong enough.

## 7. Packet / Runtime / Readiness Gate

Artifacts:

- `new_leaf_formalization_packet.json`
- `new_leaf_formalization_packet_report.md`
- `runtime_activation_plan.json`
- `runtime_activation_plan_report.md`
- `formalization_readiness_checklist.json`
- `formalization_readiness_report.md`

`new_leaf_formalization_packet.json` includes `material_evidence_summary`:

```json
{
  "source_text_evidence_status": "completed",
  "source_text_evidence_count": 2,
  "source_text_available_count": 2,
  "source_text_manual_required_count": 0,
  "source_gold_alignment_status": "completed",
  "source_gold_alignment_count": 2,
  "source_gold_alignment_needs_human_review_count": 2,
  "material_quality_regression_status": "blocked",
  "verified_original_source_count": 0,
  "requires_source_review": true,
  "requires_alignment_review": true,
  "requires_material_quality_review": true,
  "ready_for_material_card_review": false,
  "ready_for_material_card_formalization": false
}
```

Readiness gate final status:

`blocked`

Material-line readiness:

- status: `blocked`
- source_text_evidence_available: true
- source_gold_alignment_available: true
- material_quality_regression_status: `blocked`
- material_card_formalization_allowed: false
- source_verified: false

Gate blocking issues:

- `material_quality_regression_not_blocked`
- `explicit_approval_available`
- `runtime_activation_blockers_clear`

Recommended next action:

`human_review`

## 8. What Can Happen Next?

Can enter human material evidence review:

Yes.

The user can review:

- whether the two accepted seed URLs are worth keeping;
- whether fuller source text should be supplied;
- whether the current source/gold relationship should remain topic-related or be rejected;
- whether better sources are needed.

Can enter material_card_review:

No.

The current alignment is `needs_human_review/topic_related`, and material quality regression is blocked.

Can enter material_card_formalization:

No.

There is no verified original source, no useful alignment, no slicing potential, no formal approval, and no writeback plan.

## 9. Blocked Reason

This run is blocked because evidence is insufficient, not because packet/gate integration failed.

The system correctly:

- processed all accepted seeds;
- refused to process rejected/deferred candidates;
- kept source rows unverified;
- avoided fake LLM alignment after provider rejection;
- blocked material quality on weak alignment;
- carried material evidence into packet and readiness gate;
- prevented material-card review/formalization.

## 10. Boundaries Kept

This run did not:

- verify source;
- automatically confirm original source;
- batch crawl webpages;
- ingest into `passage_service`;
- write a material library;
- write `material_card`;
- write `card_specs`;
- write runtime mapping;
- write prompt assets;
- write validator rules;
- change generation main-chain logic;
- add a promotion target;
- treat source seed as verified source;
- treat similar material as original source;
- treat quality regression as material-card approval.

## 11. Test Results

Regression tests were run after the implementation:

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`

All passed.

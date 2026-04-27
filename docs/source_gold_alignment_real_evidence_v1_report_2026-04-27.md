# Source/Gold Alignment Real Evidence v1 Report

## Status

Completed.

This knife used real prepared `source_text_evidence` from the material-line acceptance run and aligned it against `gold_reconstruction_results.jsonl`. The alignment output is evidence only. It is not source verification, not material-card approval, and not a writeback path.

## Inputs

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_text_evidence_manifest.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_text_evidence_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/gold_reconstruction_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_seed_registry.jsonl`

## Source Text Evidence Counts

- total source text evidence rows: 2
- available: 2
- manual_required: 0
- blocked: 0
- failed: 0
- verified_original_source_count: 0
- verified_count: 0

## Alignment Mode

Mode: `llm`

The alignment artifacts used here were produced by the existing controlled LLM alignment path. The API key was read from environment configuration at runtime and was not written to the artifacts or reports.

If the provider or JSON parsing fails in future runs, the expected behavior is to mark the affected row as `needs_human_review` or `blocked`, not to fabricate an alignment.

## Output Artifacts

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_gold_alignment_results.jsonl`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_gold_alignment_summary.json`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_gold_alignment_report.md`
- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/material_line_full_acceptance_v1/source_gold_alignment_review.json`

## Alignment Status Distribution

- `weak`: 1
- `needs_human_review`: 1
- `blocked`: 0

## Relationship Distribution

- `similar_material`: 1
- `topic_related`: 1
- `original_source_candidate`: 0 in the final alignment relationship distribution
- `question_bank_pollution`: 0

Note: one seed had `source_use=original_source_candidate` before alignment, but alignment did not verify it and did not preserve it as a confirmed relationship.

## Sample Outcomes

| seed_id | source_use | alignment_status | relationship | confidence | review need |
| --- | --- | --- | --- | --- | --- |
| `source_seed_8ba951e15ddc8257` | `similar_material` | `weak` | `similar_material` | `low` | human review required |
| `source_seed_a10a0cb29a5c0da5` | `original_source_candidate` | `needs_human_review` | `topic_related` | `low` | human review required |

## Human Review Required

Both aligned rows require human review:

1. The CO2 / plant-growth source is topically meaningful, but the available excerpt is too weak to claim source/gold support.
2. The digital humanities source is topic-related, but the available excerpt does not show the specific reconstructed gold passage.

## Boundary Checks

- `verified_original_source_count`: 0
- `verified_count`: 0
- all rows keep `verified=false`
- all rows keep `verified_original_source=false`
- all rows keep `formalized=false`
- all rows require human review

## Risk Assessment

No pseudo-confirmation risk was observed in the final artifacts. The system did not treat similar material as original source, and did not treat an `original_source_candidate` seed as verified source.

## Not Done

This knife did not:

- verify original source;
- fetch or ingest into `passage_service`;
- write material library entries;
- write `material_card`;
- write `card_specs`;
- modify runtime, prompt, validator, or generation logic.

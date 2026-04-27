# Leaf Pre-Distill Real Pack Mock Frontend Smoke

Date: 2026-04-25

## Input

- Source file: `C:\Users\97918\AppData\Local\Temp\360zip$Temp\360$1\实词.docx`
- Mother family: `word_usage`
- Child family: `word_usage_content_word`
- Leaf label: `实词`

## Offline Artifacts

Output directory:

- `data/leaf_pre_distill/real_word_usage_shici_20260425`

Generated artifacts:

- `manifest.json`
- `samples.jsonl`
- `behavior_traces.jsonl`
- `field_candidates.json`
- `slot_projection_draft.yaml`
- `report.md`
- `llm_safe_digest.json`
- `llm_field_probe.json`

Summary:

- sample_count: `50`
- field_candidate_count: `0`
- high_confidence_count: `0`
- schema_gap_count: `0`
- LLM probe mode: dry-run only

Finding:

- The docx parser handled this pack and extracted 50 samples.
- Current marker rules do not include the `word_usage` family, so no field candidates were generated. This is a family coverage gap, not a review/patch/promotion chain failure.

## Mock Frontend Button Flow

Simulated flow:

1. create dataset
2. create session
3. run trial
4. submit review
5. submit patch
6. submit promote

Result:

- run status: `completed`
- review targets: `leaf_pre_distill_report`
- patch target: `leaf_pre_distill_report`
- promotion target: `leaf_pre_distill_report`
- promotion bundle generated successfully

Generated bundle:

- `data/leaf_pre_distill/real_word_usage_shici_20260425/distill_promotions/6acc2c95-d3d9-41ff-833e-2208734e51fb.json`

Mock flow log:

- `data/leaf_pre_distill/real_word_usage_shici_20260425/mock_frontend_button_flow_log_utf8.json`

Patch payload included:

- `artifact_path`
- `field_candidates_path`
- `slot_projection_draft_path`
- `llm_safe_digest_path`
- `llm_field_probe_path`

## Bugs / Notes

- Initial inline PowerShell-to-Python test script corrupted Chinese string literals into `??`. Re-running the flow with UTF-8 values loaded from generated artifacts preserved `实词` correctly. This appears to be a test harness encoding issue, not a workbench persistence issue.
- The next real functional gap is `word_usage` field marker coverage. The chain can archive the evidence, but the deterministic distiller has no rules yet for this mother family.

## Boundary Confirmation

- No real LLM request was made.
- No new promotion target was added.
- `slot_projection_draft` remained attachment-only.
- `llm_field_probe` remained evidence-only and did not act as a promotion judge.
- No automatic write-back to `card_specs`.
- No generation service or validator main logic was changed.

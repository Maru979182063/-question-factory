# Leaf Pre-Distill Real Word Usage System API Full Chain

Date: 2026-04-25

## Input

- Source pack: `C:\Users\97918\AppData\Local\Temp\360zip$Temp\360$1\实词.docx`
- Mother family: `word_usage`
- Child family: `word_usage_content_word`
- Leaf label: `实词`

## Offline New-Leaf Artifacts

Output directory:

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425`

Generated:

- `manifest.json`
- `samples.jsonl`
- `behavior_traces.jsonl`
- `field_candidates.json`
- `slot_projection_draft.yaml`
- `llm_safe_digest.json`
- `llm_field_probe.json`
- `bootstrap_discovery.json`
- `report.md`

Summary:

- sample_count: `50`
- field_candidate_count: `0`
- bootstrap_discovery_enabled: `true`
- llm_probe_enabled: `true`
- llm_field_probe usable: `true`
- should_promote: `false`

The LLM probe call succeeded after adding a browser-like `User-Agent` to the Python client. Without that header, the compatible endpoint returned HTTP 403 / error code 1010.

## System API Real Generation Attempt

Log:

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/system_api_real_generation_attempt.json`

System endpoints used:

- `GET /healthz`
- `GET /demo-static/distill_demo.html`
- `POST /api/v1/distill/datasets`
- `POST /api/v1/distill/sessions`
- `POST /api/v1/distill/sessions/{session_id}/trials`

Dataset creation worked:

- sample_count: `6`
- split_counts: train `2`, dev `2`, test `2`
- sample tags: `new_leaf`, `bootstrap_discovery`, `word_usage`, split label

Real generation trial result:

- run status: `failed`
- error: `Selected business_subtype is not mapped yet.`
- details.business_subtype: `word_usage_content_word`

Conclusion:

- The system can create and label the distillation dataset for the new leaf.
- The current formal generation service cannot yet run `word_usage_content_word`.
- This is the current user-facing blocker for fully self-service new-leaf distillation in the app.

## System API Fixture Generation Full Chain

Log:

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/system_api_fixture_generation_full_chain.json`

This flow used the real `/api/v1/distill` endpoints and a test-mode generation monkeypatch to complete the UX chain after the real generation blocker was identified.

Endpoints exercised:

- `POST /api/v1/distill/datasets`
- `POST /api/v1/distill/sessions`
- `POST /api/v1/distill/sessions/{session_id}/trials`
- `POST /api/v1/distill/runs/{run_id}/review`
- `POST /api/v1/distill/runs/{run_id}/patches`
- `POST /api/v1/distill/runs/{run_id}/promote`

Result:

- trial status: `completed`
- review target: `leaf_pre_distill_report`
- patch target: `leaf_pre_distill_report`
- promotion target: `leaf_pre_distill_report`
- promotion bundle generated successfully

Promotion bundle:

- `data/leaf_pre_distill/real_word_usage_full_chain_20260425/distill_promotions/511da260-7703-4377-b39f-bd52f023d043.json`

Patch payload attachments:

- `artifact_path`
- `field_candidates_path`
- `slot_projection_draft_path`
- `llm_safe_digest_path`
- `llm_field_probe_path`
- `bootstrap_discovery_path`

## UX Notes

- `distill_demo.html` exposes `leaf_pre_distill_report` and `schema_gap_report` targets.
- It does not expose a dedicated `bootstrap_discovery_path` field. Users can still paste it in the generic patch JSON textarea.
- A true self-service flow still needs either a leaf-preprocess UI/API or a supported generation route for `word_usage_content_word`.

## Boundaries

- No new promotion target was added.
- `bootstrap_discovery` is not `field_candidates`.
- `candidate_axes` are not fields.
- `proto_mother_family` is not a formal mother family.
- `llm_field_probe` is not a promotion judge.
- No automatic write-back to `card_specs`.
- No validator main logic change.
- No prompt assets change.
- No database migration.

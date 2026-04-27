# word_usage_content_word Manual Acceptance Report

Date: 2026-04-25

## Verdict

Accepted for the experimental/proto route.

The new leaf family `word_usage_content_word` can now enter the system through a
real distill workbench chain:

```text
offline leaf_pre_distill artifacts
-> distill dataset
-> distill session
-> generation trial
-> human review
-> evidence patches
-> promotion bundle
```

This acceptance does not approve `word_usage` as a formal stable mother family.

## Input Artifacts

Source artifact directory:

```text
E:\agent_repo_src\data\leaf_pre_distill\real_word_usage_full_chain_20260425
```

Checked artifacts:

- `manifest.json`
- `samples.jsonl`
- `behavior_traces.jsonl`
- `field_candidates.json`
- `slot_projection_draft.yaml`
- `report.md`
- `llm_safe_digest.json`
- `llm_field_probe.json`
- `bootstrap_discovery.json`

All were present.

## System Chain

The acceptance used real FastAPI routes through `TestClient`; no monkeypatch or
fixture generation runner was used.

Executed button-equivalent steps:

```text
GET  /healthz
GET  /demo-static/distill_demo.html
POST /api/v1/distill/datasets
POST /api/v1/distill/sessions
POST /api/v1/distill/sessions/{session_id}/trials
POST /api/v1/distill/runs/{run_id}/review
POST /api/v1/distill/runs/{run_id}/patches
POST /api/v1/distill/runs/{run_id}/patches
POST /api/v1/distill/runs/{run_id}/promote
```

All steps returned HTTP 200.

## Acceptance Output

Acceptance directory:

```text
E:\agent_repo_src\data\leaf_pre_distill\word_usage_proto_manual_acceptance_20260425
```

Step log:

```text
E:\agent_repo_src\data\leaf_pre_distill\word_usage_proto_manual_acceptance_20260425\manual_acceptance_full_chain.json
```

Acceptance DB:

```text
E:\agent_repo_src\data\leaf_pre_distill\word_usage_proto_manual_acceptance_20260425\manual_acceptance.db
```

Promotion bundle:

```text
E:\agent_repo_src\data\leaf_pre_distill\word_usage_proto_manual_acceptance_20260425\distill_promotions\dabadb14-5a34-4c50-868c-1aa94981a934.json
```

## Dataset Result

Dataset:

```text
cfca0c69-9cf2-4b54-b47e-5431bb458ec1
```

Samples:

```json
{
  "sample_count": 3,
  "split_counts": {
    "train": 1,
    "dev": 1,
    "test": 1
  }
}
```

## Trial Result

Run:

```text
df828399-56a4-4d78-b7d3-da757f23917d
```

Result:

```json
{
  "status": "completed",
  "sample_error": null,
  "item_question_type": "word_usage",
  "item_business_subtype": "word_usage_content_word"
}
```

Fit summary:

```json
{
  "truth_available": true,
  "question_type_match": true,
  "business_subtype_match": true,
  "answer_match": true,
  "stem_similarity": 0.9451,
  "analysis_similarity": 0.8904,
  "option_overlap": 0.9131,
  "material_similarity": 0.9386,
  "fit_band": "high",
  "notes": []
}
```

The high fit is expected because the proto route is intentionally conservative
and uses the source question as reviewable proto material. This proves route
availability, not production-quality generation.

## Proto Metadata

The generated item carried:

```json
{
  "experimental": true,
  "proto_family": "word_usage",
  "proto_child_family": "word_usage_content_word",
  "business_subtype": "word_usage_content_word",
  "question_card_id": "proto.word_usage.content_word.v0",
  "business_feature_card_id": "proto.word_usage.content_word.feature.v0",
  "material_strategy": "proto_text_context_window",
  "validator_contract": "proto_minimal_json_shape_only",
  "prompt_profile": "proto_word_usage_explanation",
  "source": "bootstrap_discovery",
  "formalized": false
}
```

Validation warnings:

```text
experimental_proto_route
proto_minimal_json_shape_only
not_formal_validator_contract
```

## Promotion Bundle

Promoted evidence targets:

```text
leaf_pre_distill_report
schema_gap_report
```

Patch payloads included:

- `leaf_pre_distill_report`
  - `artifact_path`
  - `manifest_path`
  - `samples_path`
  - `behavior_traces_path`
  - `field_candidates_path`
  - `slot_projection_draft_path`
  - `llm_safe_digest_path`
  - `llm_field_probe_path`
  - `bootstrap_discovery_path`
  - `manual_acceptance_db_path`

- `schema_gap_report`
  - `artifact_path`
  - `bootstrap_discovery_path`
  - `gap_summary`
  - `promotion_allowed: false`

## Boundary Checks

All boundary checks passed:

```json
{
  "experimental_true": true,
  "formalized_false": true,
  "no_new_promotion_target": true,
  "bootstrap_attachment_only": true,
  "slot_projection_attachment_only": true,
  "schema_gap_not_schema_change": true
}
```

## Regression Tests

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Result:

```text
Ran 4 tests in 0.606s
OK
```

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

Result:

```text
Ran 10 tests in 2.925s
OK
```

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

```text
Ran 12 tests in 0.161s
OK
```

## Explicit Non-Goals Preserved

- Did not formally promote `word_usage` mother family.
- Did not add a normalized `word_usage` question card.
- Did not convert `candidate_axes` into formal fields.
- Did not add a promotion target.
- Did not write back to `card_specs`.
- Did not modify validator main business logic.
- Did not change database schema or add migrations.
- Did not change frontend tabs.
- Did not call an external LLM during this acceptance.
- Did not affect existing `sentence_fill`, `sentence_order`, or
  `center_understanding` routes.

## Remaining Product Gap

This route is now system-callable, but the UI still requires the user to provide
the proto flag through JSON:

```json
{
  "extra_constraints": {
    "experimental_proto_route": true
  }
}
```

A future small UX slice can add a dedicated "experimental proto route" toggle or
artifact-driven patch template. That would improve usability without changing
the evidence boundaries.


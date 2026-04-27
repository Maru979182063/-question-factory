# Word Usage Axis Confirmation Small Loop Report

Date: 2026-04-25

## Verdict

Accepted.

The `word_usage_content_word` small loop now runs through:

```text
bootstrap_discovery.json
-> handwritten axis_decisions.json
-> axis_confirmation.json
-> formal_patch_draft.json
-> report.md sections
-> leaf_pre_distill_report evidence patch
-> schema_gap_report evidence patch
-> promotion bundle
```

This run did not write back to `card_specs`, did not add a promotion target, and
did not formalize `word_usage`.

## Source Note

The original temporary docx path no longer exists:

```text
C:\Users\97918\AppData\Local\Temp\360zip$Temp\360$1\实词.docx
```

This is expected for a temporary 360zip extraction directory.

The loop used the already saved real artifact directory from the previous
`实词` run:

```text
E:\agent_repo_src\data\leaf_pre_distill\real_word_usage_full_chain_20260425
```

## Output Directory

```text
E:\agent_repo_src\data\leaf_pre_distill\word_usage_axis_confirm_small_loop_20260425
```

Generated / checked files:

- `axis_decisions.json`
- `axis_confirmation.json`
- `formal_patch_draft.json`
- `report.md`
- `axis_confirmation_small_loop_log.json`

## Axis Confirmation

Result:

```json
{
  "status": "proto_confirmed",
  "formalized": false,
  "promotion_allowed": false,
  "confirmed_decision_count": 5
}
```

Confirmed/deferred decisions included:

- `explanation_target_type` -> `business_feature_card`
- `referent_resolution_mode` -> `prompt_assets`
- `contextual_meaning_mode` -> `business_feature_card`
- `concept_boundary_mode` -> `validator_contract`
- `context_detached` -> `signal_layer`
- `option_elimination_mode` -> deferred as reviewer note

## Formal Patch Draft

Result:

```json
{
  "status": "draft_only",
  "writeback_allowed": false,
  "formalized": false
}
```

Draft target groups:

- `business_feature_card`
- `prompt_assets`
- `signal_layer`
- `validator_contract`

These are draft payload groups only. No formal files were changed.

## Report Check

`report.md` contains:

- `## Axis Confirmation`
- `## Formal Patch Draft`

## Workbench Chain

Executed real FastAPI route calls through `TestClient`:

```text
GET  /healthz
POST /api/v1/distill/datasets
POST /api/v1/distill/sessions
POST /api/v1/distill/sessions/{session_id}/trials
POST /api/v1/distill/runs/{run_id}/review
POST /api/v1/distill/runs/{run_id}/patches
POST /api/v1/distill/runs/{run_id}/patches
POST /api/v1/distill/runs/{run_id}/promote
```

All returned HTTP 200.

Run result:

```json
{
  "run_status": "completed",
  "run_sample_error": null
}
```

IDs:

- dataset: `dc42df87-e148-4b25-9aff-f3de6167e62e`
- session: `29af1448-1ee3-4d22-a310-138415615979`
- run: `2c72254e-c068-45bb-be9a-53710ad354ac`

## Promotion Bundle

Promoted targets:

```text
leaf_pre_distill_report
schema_gap_report
```

Promotion bundle:

```text
E:\agent_repo_src\data\leaf_pre_distill\word_usage_axis_confirm_small_loop_20260425\distill_promotions\08b9891f-eb82-4a4d-a548-729ac2d55486.json
```

The `leaf_pre_distill_report` patch payload carried:

- `axis_confirmation_path`
- `formal_patch_draft_path`

The `schema_gap_report` patch kept:

```json
{
  "promotion_allowed": false
}
```

## Boundaries Preserved

- Did not do UI.
- Did not add API.
- Did not write back `card_specs`.
- Did not change validator main logic.
- Did not change prompt assets.
- Did not change generation main chain.
- Did not add promotion targets.
- Did not treat `axis_confirmation` as formal.
- Did not treat `formal_patch_draft` as writeback.


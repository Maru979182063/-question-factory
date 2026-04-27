# Axis Confirmation / Formal Patch Draft Execution Plan

Date: 2026-04-25

## Goal

Add the missing bridge that lets a user turn:

```text
bootstrap candidate axes
```

into:

```text
human-confirmed proto decisions
```

and then into:

```text
formal patch drafts for existing canonical targets
```

This is the step that moves the system from "new leaf experiment table" toward
"semi-automatic card factory".

## Non-Goals

Do not:

- add a promotion target;
- auto-write `card_specs`;
- auto-change validator main logic;
- auto-change prompt assets;
- auto-change runtime mappings;
- formally promote `word_usage`;
- treat `candidate_axes` as fields;
- treat `proto_mother_family` as a formal mother family;
- add database tables;
- add file upload or a large frontend tab;
- make LLM output a confirmation judge.

## Recommended First Implementation

Do this as an offline artifact layer first.

New files:

```text
tools/leaf_pre_distill/axis_confirmation.py
tools/leaf_pre_distill/formal_patch_draft.py
```

Modify only if needed:

```text
tools/leaf_pre_distill/run.py
tools/leaf_pre_distill/report_renderer.py
docs/leaf_pre_distill_artifact_contract.md
tests/test_leaf_pre_distill.py
```

Optional new report:

```text
docs/axis_confirmation_formal_patch_execution_report_2026-04-25.md
```

## CLI Shape

Add optional flags, default off:

```text
--enable-axis-confirmation
--axis-confirmation-decisions path/to/axis_decisions.json
--enable-formal-patch-draft
--formal-patch-targets business_feature_card,signal_layer,prompt_assets
```

Default behavior must remain unchanged.

If `--enable-axis-confirmation` is not passed:

- do not generate `axis_confirmation.json`;
- do not generate `formal_patch_draft.json`.

If `--enable-formal-patch-draft` is passed without confirmation decisions:

- fail with a clear message or emit `draft_status=blocked`;
- do not guess user decisions.

## Human Decision Input

Use a small JSON file first, rather than building UI immediately:

```json
{
  "decision_version": "v1",
  "reviewer": "operator",
  "proto_family_label": "word_usage",
  "decisions": [
    {
      "source_type": "candidate_axis",
      "source_id": "contextual_meaning_mode",
      "action": "promote_to_proto_field",
      "target_name": "contextual_meaning_mode",
      "target_layer": "business_feature_card",
      "rationale": "Most samples ask for meaning in context rather than dictionary meaning."
    },
    {
      "source_type": "candidate_axis",
      "source_id": "option_elimination_mode",
      "action": "downgrade_to_note",
      "rationale": "Too generic until tied to word-meaning distractors."
    }
  ]
}
```

This file is the user confirmation action.

## `axis_confirmation.json`

Suggested structure:

```json
{
  "confirmation_version": "v1",
  "enabled": true,
  "source": "human_axis_confirmation",
  "status": "proto_confirmed",
  "formalized": false,
  "promotion_allowed": false,
  "proto_mother_family": {
    "label": "word_usage",
    "status": "proto_confirmed",
    "formal": false
  },
  "axis_decisions": [
    {
      "source_axis": "contextual_meaning_mode",
      "decision": "promote_to_proto_field",
      "confirmed_name": "contextual_meaning_mode",
      "target_layer": "business_feature_card",
      "status": "proto_confirmed",
      "rationale": "..."
    }
  ],
  "rejected_or_deferred": [],
  "warnings": [],
  "limits": [
    "proto_confirmed is not formal.",
    "confirmed axes are not automatically written to card_specs.",
    "formal patch drafts require separate review."
  ]
}
```

Hard rules:

- top-level `promotion_allowed=false`;
- top-level `formalized=false`;
- every kept item must have `status=proto_confirmed`;
- every dropped item must be preserved in `rejected_or_deferred`;
- no `confirmed_fields` key;
- no direct `slot_projection_updates` key;
- no validator rule writeback.

## `formal_patch_draft.json`

Suggested structure:

```json
{
  "draft_version": "v1",
  "enabled": true,
  "source": "axis_confirmation",
  "status": "draft_only",
  "writeback_allowed": false,
  "formalized": false,
  "proto_family": "word_usage",
  "proto_child_family": "word_usage_content_word",
  "target_patches": [
    {
      "target": "business_feature_card",
      "scope_key": "proto.word_usage.content_word.feature.v0",
      "draft_status": "draft_only",
      "patch": {
        "experimental": true,
        "formalized": false,
        "proto_fields": {
          "contextual_meaning_mode": {
            "source_axis": "contextual_meaning_mode",
            "status": "proto_confirmed"
          }
        }
      }
    },
    {
      "target": "prompt_assets",
      "scope_key": "proto_word_usage_explanation",
      "draft_status": "draft_only",
      "patch": {
        "prompt_guards": [
          "Explain the target word by local context, not dictionary meaning alone."
        ],
        "experimental": true,
        "formalized": false
      }
    }
  ],
  "limits": [
    "This file is a patch draft, not a formal config change.",
    "Each target patch must still go through review/patch/promotion.",
    "No card_specs writeback has occurred."
  ]
}
```

Hard rules:

- only existing canonical targets are allowed;
- `writeback_allowed=false`;
- `formalized=false`;
- every target patch must include `experimental=true` when proto;
- no direct file writes to `card_specs`;
- no independent promotion target.

## Report Additions

Append two optional report sections:

```text
## Axis Confirmation
```

Show:

- enabled / disabled;
- proto family label;
- kept / dropped / renamed / merged / split counts;
- axis decisions table;
- warnings;
- boundary note: proto-confirmed is not formal.

```text
## Formal Patch Draft
```

Show:

- enabled / disabled;
- target patch groups;
- scope keys;
- draft-only flags;
- writeback status;
- boundary note: formal patch draft is not card_specs writeback.

## Artifact Contract Update

Update `docs/leaf_pre_distill_artifact_contract.md` with:

- `axis_confirmation.json`
- `formal_patch_draft.json`

Both should say:

- Promotion evidence: yes, only as attachment to `leaf_pre_distill_report`.
- Direct formal config: no.
- Independent promotion target: no.
- Human review focus: whether decisions are grounded, whether axes are too broad,
  whether target mapping is appropriate, and whether the draft accidentally
  formalizes proto material.

Patch payload example should allow:

```json
{
  "artifact_type": "leaf_pre_distill_report",
  "artifact_path": ".../report.md",
  "bootstrap_discovery_path": ".../bootstrap_discovery.json",
  "axis_confirmation_path": ".../axis_confirmation.json",
  "formal_patch_draft_path": ".../formal_patch_draft.json"
}
```

## Workbench Usage

First version should keep the workbench unchanged.

The user can promote evidence targets:

```text
leaf_pre_distill_report
schema_gap_report
```

and include:

```text
axis_confirmation_path
formal_patch_draft_path
```

as attachment paths.

When the user is ready to promote real patch groups, they can add explicit patches
for existing canonical targets such as:

```text
business_feature_card
signal_layer
prompt_assets
validator_contract
runtime_mapping
material_mapping
```

That second step should remain human-approved.

## Tests

Add tests in `tests/test_leaf_pre_distill.py`:

1. Default run does not generate `axis_confirmation.json`.
2. Enabling axis confirmation with a decision file generates
   `axis_confirmation.json`.
3. `axis_confirmation.json` has `promotion_allowed=false` and
   `formalized=false`.
4. Kept axes become `proto_confirmed`, not formal fields.
5. Dropped/deferred axes are preserved.
6. Unknown source axes produce warnings and do not enter confirmed decisions.
7. Enabling formal patch draft without confirmed decisions is blocked or produces
   `draft_status=blocked`.
8. Formal patch draft emits only canonical targets.
9. Formal patch draft has `writeback_allowed=false` and `formalized=false`.
10. Report includes Axis Confirmation and Formal Patch Draft sections.
11. `bootstrap_discovery`, `llm_field_probe`, `axis_confirmation`, and
    `formal_patch_draft` can coexist as attachment paths without adding
    promotion targets.

If a workbench test is added later:

1. Patch payload can store `axis_confirmation_path`.
2. Patch payload can store `formal_patch_draft_path`.
3. Promotion target list remains unchanged.
4. Missing canonical target patch guard still works.

## Acceptance Commands

Minimum after implementation:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

If workbench payload examples or tests are touched:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

Recommended regression:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

## Later UI Slice

After the offline artifact layer works, add a small UI:

- show candidate axes from `bootstrap_discovery.json`;
- allow keep/drop/rename/merge/split;
- choose target layer;
- export decision JSON;
- preview formal patch draft.

Do not build this UI before the artifact contract is stable.

## Success Standard

For a new leaf such as `word_usage_content_word`, the system should be able to
produce this chain:

```text
bootstrap_discovery.json
-> user axis decisions
-> axis_confirmation.json
-> formal_patch_draft.json
-> evidence promotion bundle
```

without:

- automatically writing formal cards;
- pretending proto axes are final fields;
- adding new promotion targets;
- changing existing stable question families.


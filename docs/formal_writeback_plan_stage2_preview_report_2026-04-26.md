# Formal Writeback Plan Stage 2 Preview Report

Date: 2026-04-26

## Scope

This stage adds a preview-only writeback planning layer after `formal_patch_draft`.

Pipeline:

```text
formal_patch_draft.json
-> formal_writeback_plan.json
-> formal_writeback_diff.md
```

The layer does not write formal files. It only explains what would be changed if a later explicit writeback is approved.

## New Artifacts

### `formal_writeback_plan.json`

Purpose:
- records target files for each draft target;
- records proposed additions from proto-confirmed decisions;
- records prompt guards for `prompt_assets`;
- records validator candidates for `validator_contract`;
- records legacy-family impact and regression requirements;
- records rollback guidance.

Hard boundaries:
- `status = preview_only`
- `writeback_allowed = false`
- `requires_explicit_approval = true`

### `formal_writeback_diff.md`

Purpose:
- human-readable diff preview derived from `formal_writeback_plan.json`;
- lists target files, additions, prompt guards, validator candidates, old-family impact, rollback, and regression requirements.

Hard boundary:
- preview only; no files are changed.

## Frontend Preview

The distill demo now exposes `5B. Writeback Plan Preview`.

User flow:

```text
formal_patch_draft.json preview / editable
-> Generate writeback plan + diff preview
-> Copy attachment paths into leaf patch JSON
```

The copy button fills the normal `leaf_pre_distill_report` patch payload with:

```json
{
  "formal_patch_draft_path": ".../formal_patch_draft.json",
  "formal_writeback_plan_path": ".../formal_writeback_plan.json",
  "formal_writeback_diff_path": ".../formal_writeback_diff.md",
  "writeback_allowed": false,
  "requires_explicit_approval": true
}
```

It does not submit automatically and does not write formal files.

## Smoke Result

Input:

```text
data/leaf_pre_distill/word_usage_axis_confirm_small_loop_20260425/formal_patch_draft.json
```

Output:

```text
data/leaf_pre_distill/word_usage_writeback_plan_preview_20260426/formal_writeback_plan.json
data/leaf_pre_distill/word_usage_writeback_plan_preview_20260426/formal_writeback_diff.md
```

Targets in the smoke preview:
- `business_feature_card`
- `prompt_assets`
- `signal_layer`
- `validator_contract`

Planned files in the smoke preview:
- `card_specs/business_feature_slots/examples/word_usage_word_usage_content_word.proto.yaml`
- `prompt_skeleton_service/configs/prompt_templates.yaml`
- `card_specs/normalized/signal_layers/word_usage_signal_layer.proto.yaml`
- `card_specs/validator_contracts/proto/word_usage_word_usage_content_word.validator.yaml`

## Tests

Commands run:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Result:
- all passed.

## Explicit Non-Changes

- No formal writeback was performed.
- No `card_specs` formal config was modified.
- No prompt assets formal config was modified.
- No validator main logic was modified.
- No generation service was modified.
- No database schema or migration was added.
- No API was added.
- No promotion target was added.
- `word_usage` was not formally promoted to a stable mother family.

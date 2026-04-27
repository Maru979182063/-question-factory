# Axis Confirmation Stage 1 Productization Report

Date: 2026-04-26

## Verdict

Accepted for Stage 1.

The distill demo now supports a frontend-only confirmation and preview workflow:

```text
bootstrap_discovery.candidate_axes
-> keep / drop / rename / split / merge
-> choose target_layer
-> generate axis_confirmation.json preview
-> generate / edit formal_patch_draft.json preview
-> create canonical target patches through the existing workbench patch API
```

This stage does not write `card_specs`, prompt assets, validator rules, runtime
mapping files, or any formal config files.

## UI Entry

Page:

```text
/demo/distill
```

New section:

```text
5A. Axis Confirmation
```

Main controls:

- `bootstrapDiscoveryJson`
- `axisDecisionList`
- `axisConfirmationJson`
- `formalPatchDraftJson`
- `createCanonicalPatchesBtn`

## Supported Canonical Patch Targets

The frontend can create workbench patches for:

- `business_feature_card`
- `prompt_assets`
- `signal_layer`
- `validator_contract`
- `material_mapping`
- `runtime_mapping`

These patches remain workbench patches only.

## Boundaries

- No UI upload API was added.
- No new backend API was added.
- No promotion target was added.
- No formal writeback was added.
- No `card_specs` file was changed.
- No validator main logic was changed.
- No prompt/generation main chain was changed.

## Acceptance

Test commands:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

Result:

```text
Ran 8 tests
OK
```

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

Result:

```text
Ran 10 tests
OK
```

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

```text
Ran 15 tests
OK
```

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Result:

```text
Ran 4 tests
OK
```

Button-equivalent canonical patch smoke:

```json
{
  "run_status": "completed",
  "patch_count": 6,
  "targets": [
    "business_feature_card",
    "material_mapping",
    "prompt_assets",
    "runtime_mapping",
    "signal_layer",
    "validator_contract"
  ],
  "all_patches_draft_only": true
}
```

## Known Local Limitation

Direct `node --check` syntax validation could not run because this local Windows
environment returned `Access is denied` for `node.exe`. The FastAPI demo smoke
tests loaded the page and script assets successfully.


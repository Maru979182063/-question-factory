# Formal Writeback Executor Execution Report

Date: 2026-04-26

## Scope

Implemented Executor v1 as an offline guarded writer for approved `formal_writeback_plan.json` artifacts.

New module:

```text
tools/leaf_pre_distill/formal_writeback_executor.py
```

Executor v1 is intentionally narrow:

- requires a separate human approval object;
- rejects incomplete approval;
- rejects shared config targets;
- writes only allowlisted proto files;
- generates forward and rollback patches before writing target files;
- generates manifest and regression report after writing;
- does not modify prompt, generation, validator main-chain files, API, DB, or UI.

## Writable Targets

Allowed:

- `business_feature_card`
- `signal_layer`
- `validator_contract`

Rejected / draft-only:

- `prompt_assets`
- `material_mapping`
- `runtime_mapping`
- `material_card`
- `question_card`
- `leaf_pre_distill_report`
- `schema_gap_report`

## Approval Gate

The executor requires approval fields including:

- `approval_version = v1`
- `approval_type = formal_writeback`
- `approved = true`
- non-empty human `approved_by`
- matching `proto_family` and `proto_child_family`
- exact `allowed_targets`
- exact `allowed_files`
- source artifact paths
- human review assertions:
  - `candidate_axes_are_proto_confirmed`
  - `draft_reviewed`
  - `diff_reviewed`
  - `rollback_reviewed`
  - `no_shared_config_write_in_v1`

The plan still keeps:

```json
{
  "writeback_allowed": false,
  "requires_explicit_approval": true
}
```

The plan is not the approval. The approval object is the write gate.

## Smoke Test

Smoke output:

```text
data/leaf_pre_distill/formal_writeback_executor_smoke_20260426_140931
```

The smoke used a temporary repo root under the smoke directory, not the real repository root.

Written proto files in the smoke repo:

- `card_specs/business_feature_slots/examples/word_usage_word_usage_content_word.proto.yaml`
- `card_specs/normalized/signal_layers/word_usage_signal_layer.proto.yaml`
- `card_specs/validator_contracts/proto/word_usage_word_usage_content_word.validator.yaml`

Generated artifacts:

- `out/formal_writeback_forward.patch`
- `out/formal_writeback_rollback.patch`
- `out/formal_writeback_manifest.json`
- `out/formal_writeback_regression_report.json`

Smoke regression:

```text
passed = true
command_count = 1
```

## Tests Run

Passed:

```powershell
python -m py_compile tools/leaf_pre_distill/formal_writeback_executor.py tests/test_leaf_pre_distill.py
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_sentence_fill_protocol
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_sentence_order_protocol
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_card_binding
```

Additional broad tests attempted but not clean in the current local environment:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_prompt_builder
```

Result: failed because the local Round 1 few-shot pack file does not exist.

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_generation
```

Result: one failure from a hard-coded old local path:

```text
C:\Users\Maru\Documents\agent\prompt_skeleton_service\app\services\question_generation.py
```

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_validator
```

Result: existing validator expectation failures unrelated to this executor module.

## Acceptance Mapping

1. No approval must reject: covered by unit test.
2. Incomplete approval must reject: covered by unit test.
3. Shared config target must reject: covered by unit test.
4. Only allowlist proto files are written: covered by unit test and smoke.
5. Forward and rollback patch generated before write: implemented in executor sequence and verified by smoke artifacts.
6. Manifest and regression report generated after write: covered by unit test and smoke.
7. Regression passes: executor regression passed in smoke; core distill/workbench/word_usage/sentence tests passed.
8. Prompt/generation/validator main chain and old families are not modified by this executor. Old sentence-fill and sentence-order protocol tests passed; broad prompt/generation/validator suites have pre-existing local issues recorded above.

## Explicit Non-Changes

- No API added.
- No UI added.
- No DB migration.
- No promotion target added.
- No prompt templates written.
- No runtime mappings written.
- No material mapping written.
- No question card written.
- No generation service file modified by this executor.
- No validator main logic modified by this executor.
- No formal stable promotion of `word_usage`.

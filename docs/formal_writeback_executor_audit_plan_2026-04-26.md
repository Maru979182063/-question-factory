# Formal Writeback Executor Audit And Execution Plan

Date: 2026-04-26

## Executive Decision

Do not start formal writeback yet.

The next implementation should first create a guarded `Formal Writeback Executor` that can turn an approved `formal_writeback_plan.json` into:

- a forward writeback patch;
- a rollback patch;
- a writeback manifest;
- post-writeback regression results.

Executor v1 should only write isolated proto files. Shared runtime or prompt configuration should stay draft-only until the executor has stronger pollution guards and regression coverage.

## Current State

Existing preview chain:

```text
bootstrap_discovery.json
-> axis_confirmation.json
-> formal_patch_draft.json
-> formal_writeback_plan.json
-> formal_writeback_diff.md
```

Current plan targets are generated from `tools/leaf_pre_distill/formal_writeback_plan.py`.

Current planned file map:

| target | current planned file |
|---|---|
| `business_feature_card` | `card_specs/business_feature_slots/examples/{proto_family}_{proto_child_family}.proto.yaml` |
| `signal_layer` | `card_specs/normalized/signal_layers/{proto_family}_signal_layer.proto.yaml` |
| `material_mapping` | `card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml` |
| `runtime_mapping` | `card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml` |
| `prompt_assets` | `prompt_skeleton_service/configs/prompt_templates.yaml` |
| `validator_contract` | `card_specs/validator_contracts/proto/{proto_family}_{proto_child_family}.validator.yaml` |
| `material_card` | `card_specs/normalized/material_cards/{proto_family}_material_cards.proto.yaml` |
| `question_card` | `card_specs/normalized/question_cards/{proto_family}_standard_question_card.proto.yaml` |

## 1. Files Allowed To Be Written

Executor v1 allowlist should be strict and path-based.

Allowed in Executor v1:

| path pattern | reason | guard |
|---|---|---|
| `card_specs/business_feature_slots/examples/*.proto.yaml` | isolated proto business-feature cards | filename must include `proto_family` and `proto_child_family`; no overwrite unless previous file has executor manifest id |
| `card_specs/normalized/signal_layers/*_signal_layer.proto.yaml` | isolated proto signal layer | new file only; must include `experimental: true` and `formalized: false` |
| `card_specs/validator_contracts/proto/*.validator.yaml` | non-enforced validator candidate contract | new file only; cannot be imported by validator main logic |
| `data/leaf_pre_distill/**/formal_writeback_manifest.json` | audit manifest | append/create only in artifact output dir |
| `data/leaf_pre_distill/**/formal_writeback_forward.patch` | forward patch artifact | generated before/after diff |
| `data/leaf_pre_distill/**/formal_writeback_rollback.patch` | rollback artifact | reverse diff |
| `data/leaf_pre_distill/**/formal_writeback_regression_report.json` | regression report | result artifact only |

Executor v1 must not write:

- `prompt_skeleton_service/configs/prompt_templates.yaml`
- `prompt_skeleton_service/configs/question_generation_prompt_assets.yaml`
- `card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml`
- `card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml`
- `card_specs/normalized/question_cards/*.normalized.yaml`
- existing stable `*.normalized.yaml` material cards
- generation service files
- validator service files
- API/router files
- database or migration files

Executor must reject any target file that:

- resolves outside the repo root;
- is not in the allowlist;
- is a shared config in v1;
- would overwrite an existing file without a matching previous writeback manifest;
- lacks `proto` / `experimental` markers for a new-family writeback.

## 2. Target Write Policy

### Executor v1: allowed to write

| target | status | reason |
|---|---|---|
| `business_feature_card` | write allowed | isolated proto file; lowest blast radius; best first formalization step |
| `signal_layer` | write allowed | isolated proto signal file if not wired into runtime automatically |
| `validator_contract` | write allowed as candidate file only | allowed only under `card_specs/validator_contracts/proto/`; not imported by validator main logic |

### Executor v1: must remain draft-only

| target | status | reason |
|---|---|---|
| `prompt_assets` | draft-only | `prompt_templates.yaml` is shared; one bad append can affect old generation |
| `material_mapping` | draft-only | writes shared executable runtime mapping |
| `runtime_mapping` | draft-only | writes shared family hierarchy used by routing |
| `material_card` | draft-only | current plan lacks enough material-card schema guarantees |
| `question_card` | draft-only | highest semantic commitment; would make `word_usage` look close to a formal family |
| `leaf_pre_distill_report` | evidence-only | never a formal writeback target |
| `schema_gap_report` | evidence-only | gap statement, not schema change |

Recommended staged expansion:

1. Executor v1: `business_feature_card`, `signal_layer`, proto-only `validator_contract`.
2. Executor v1.1: `material_card` after schema template and material-card tests exist.
3. Executor v1.2: `material_mapping` with scoped insertion and old-family regression.
4. Executor v1.3: `prompt_assets` with isolated template id and prompt-builder regression.
5. Executor v2: `runtime_mapping` and `question_card`, only after full approval and old-family plus new-family generation regressions pass.

## 3. Shared Prompt Configuration Pollution Guard

`prompt_templates.yaml` is high risk because it is shared executable configuration.

Do not let Executor v1 write it.

When prompt writeback is eventually allowed, it must use these guards:

1. New template only, never edit an existing template in place.
2. Template id must be unique and proto-scoped, for example:

   ```text
   tpl-proto-word-usage-content-word-generate-v0
   ```

3. Template must contain:

   ```yaml
   experimental: true
   formalized: false
   source: formal_writeback_executor
   proto_family: word_usage
   proto_child_family: word_usage_content_word
   ```

4. Must set exact routing fields:

   ```yaml
   question_type: word_usage
   business_subtype: word_usage_content_word
   action_type: generate
   ```

5. Existing templates must remain byte-identical except for the append block.
6. The executor must generate a before/after hash for the full file.
7. The executor must run prompt-builder and generation regressions before marking writeback success.
8. If more than one existing template changes, fail the writeback.
9. If the appended template id collides with an existing id, fail the writeback.
10. If any old subtype resolves to the new proto template unexpectedly, fail the writeback.

Minimum prompt-specific regression later:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_prompt_builder
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_generation
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

## 4. Required Approval Fields Before Writeback

Executor must reject writeback unless all fields are present and internally consistent.

Required approval object, stored beside the plan or embedded in an execution request:

```json
{
  "approval_version": "v1",
  "approval_type": "formal_writeback",
  "approved": true,
  "approved_at": "2026-04-26T00:00:00+08:00",
  "approved_by": "human_reviewer",
  "approval_scope": {
    "proto_family": "word_usage",
    "proto_child_family": "word_usage_content_word",
    "allowed_targets": ["business_feature_card", "signal_layer"],
    "allowed_files": [
      "card_specs/business_feature_slots/examples/word_usage_word_usage_content_word.proto.yaml",
      "card_specs/normalized/signal_layers/word_usage_signal_layer.proto.yaml"
    ]
  },
  "source_artifacts": {
    "axis_confirmation_path": ".../axis_confirmation.json",
    "formal_patch_draft_path": ".../formal_patch_draft.json",
    "formal_writeback_plan_path": ".../formal_writeback_plan.json",
    "formal_writeback_diff_path": ".../formal_writeback_diff.md"
  },
  "human_review_assertions": {
    "candidate_axes_are_proto_confirmed": true,
    "draft_reviewed": true,
    "diff_reviewed": true,
    "rollback_reviewed": true,
    "no_shared_config_write_in_v1": true
  }
}
```

Executor validation rules:

- `approved` must be `true`.
- `approval_type` must be `formal_writeback`.
- `approved_by` must be non-empty and cannot be `llm`, `model`, `auto`, or `system`.
- `allowed_targets` must be a subset of Executor v1 allowed targets.
- `allowed_files` must exactly match the target files being written.
- `formal_writeback_plan.status` must be `preview_only`.
- `formal_writeback_plan.writeback_allowed` must be `false`; approval is the separate release gate.
- every writeback item must still have `requires_explicit_approval=true`.
- every source `axis_decision.status` must be `proto_confirmed`, not `hypothesis`.
- no item may contain `formalized=true` before writeback.
- no shared config target may be present in Executor v1.

Important distinction:

`formal_writeback_plan.writeback_allowed=false` remains correct. The plan itself never authorizes writing. The separate human approval object authorizes the executor to apply a narrow subset.

## 5. Required Regressions After Writeback

Executor v1 post-writeback regressions:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

If any shared config target is eventually enabled, add:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_card_binding
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_prompt_builder
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_generation
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_validator
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_sentence_fill_protocol
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_sentence_order_protocol
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_generation_gate
```

If `runtime_mapping` or `question_card` is enabled later, add a real generation smoke:

- existing `sentence_fill` sample;
- existing `sentence_order` sample;
- existing `center_understanding` sample;
- `word_usage_content_word` proto sample.

Regression report must record:

- command;
- exit code;
- duration;
- pass/fail;
- stdout/stderr path;
- git diff summary after writeback.

If any required regression fails, executor must leave the files in place for inspection but mark:

```json
{
  "writeback_status": "failed_regression",
  "rollback_recommended": true
}
```

It should not auto-rollback unless the user explicitly approves rollback.

## 6. Rollback Patch Generation

Executor must generate rollback before it reports success.

Recommended implementation:

1. Resolve all target paths.
2. Read current bytes for each target file.
3. Store before snapshots in memory and write hashes into manifest:

   ```json
   {
     "path": "card_specs/...",
     "before_sha256": "...",
     "after_sha256": "..."
   }
   ```

4. Apply proposed writes in memory first.
5. Generate forward patch:

   ```text
   before -> after
   ```

6. Generate rollback patch:

   ```text
   after -> before
   ```

7. Write artifacts:

   ```text
   formal_writeback_forward.patch
   formal_writeback_rollback.patch
   formal_writeback_manifest.json
   ```

8. Only then write files.
9. After writing, re-read files and verify `after_sha256`.
10. If hash verification fails, mark writeback failed and do not continue to regression.

Patch format should be standard unified diff so rollback can be reviewed and applied with normal tools.

Rollback patch rules:

- include new-file deletion when the executor created a new file;
- include exact reverse hunks for modified files;
- include original file mode if available;
- include manifest id in patch header comments;
- include only files touched by this executor run.

Rollback command should be documented but not run automatically:

```powershell
git apply data/leaf_pre_distill/<job>/formal_writeback_rollback.patch
```

## Proposed Executor Design

New module:

```text
tools/leaf_pre_distill/formal_writeback_executor.py
```

Proposed CLI additions:

```text
--execute-formal-writeback
--formal-writeback-plan PATH
--formal-writeback-approval PATH
--formal-writeback-output-dir PATH
--formal-writeback-dry-run
```

Default must be dry-run / no execution unless `--execute-formal-writeback` and an approval file are both present.

Main functions:

```python
load_writeback_plan(path)
load_writeback_approval(path)
validate_writeback_approval(plan, approval)
resolve_allowed_writeback_items(plan, approval)
render_writeback_files(items)
generate_forward_and_rollback_patches(before, after)
apply_writeback(items)
run_writeback_regressions()
write_writeback_manifest()
```

Executor v1 tests:

1. Rejects missing approval.
2. Rejects `approved=false`.
3. Rejects shared config targets.
4. Rejects target path outside allowlist.
5. Writes only approved proto files.
6. Generates forward patch.
7. Generates rollback patch.
8. Hashes before/after.
9. Runs or records regression commands.
10. Does not modify prompt templates, runtime mappings, question cards, generation service, validator main logic, or API.

## Final Recommendation

Implement Executor v1 as a narrow file writer for:

- `business_feature_card`
- `signal_layer`
- proto-only `validator_contract`

Keep these draft-only for now:

- `prompt_assets`
- `material_mapping`
- `runtime_mapping`
- `material_card`
- `question_card`

This preserves the product path toward a half-automatic card factory while keeping the first real writeback from contaminating existing generation routes.

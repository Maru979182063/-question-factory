# distill_workbench_formalization_gate_ui_v1 Report

Date: 2026-04-28

## Modified Files

- `prompt_skeleton_service/app/demo_static/distill_demo.html`
- `prompt_skeleton_service/app/demo_static/distill_demo.js`
- `prompt_skeleton_service/tests/test_demo_shell.py`

## New Frontend Section

Added a lightweight section:

- `5E. Formalization Gate Preview / 正式化送审与 Readiness Gate 预览`

The section lets a user paste existing artifacts and generate conservative frontend-only previews for:

- `new_leaf_formalization_packet_preview.json`
- `runtime_activation_plan_preview.json`
- `formalization_readiness_checklist_preview.json`
- human-readable gate summary

This is a preview-only UI. It does not call a backend executor and does not write any formal configuration.

## Supported Inputs

The UI accepts pasted JSON for:

- `formal_patch_draft.json`
- `material_card_draft.json`
- `material_evidence_summary` or material-line artifact summary
- `agent_review_feedback_normalized.json`
- `source_candidate_review.json` or source seed summary
- `truth_gold_regression_results.json`
- `runtime_activation_plan.json`
- `new_leaf_formalization_packet.json`
- `formalization_readiness_checklist.json`

## Output Preview Contract

Every generated preview keeps these safety fields:

```json
{
  "preview_version": "v1",
  "formalized": false,
  "writeback_allowed": false,
  "executor_allowed": false,
  "requires_human_review": true,
  "requires_regression": true
}
```

The preview status is one of:

- `blocked`
- `review_needed`
- `material_card_review_ready`
- `proto_ready`
- `writeback_plan_ready`

The frontend does not generate `executor_ready`.

## Gate Preview Logic

The preview defaults to `blocked`.

It remains `blocked` when:

- `formal_patch_draft` is missing
- normalized user feedback is missing
- `runtime_activation_plan` is missing
- material evidence is missing while material card evidence is needed
- `material_quality_regression_status=blocked`
- source/gold alignment still requires review
- `verified_original_source_count>0` appears without source verification approval
- `writeback_allowed=true` appears in any pasted draft
- `formalized=true` appears in any pasted draft
- `material_card_draft` attempts formalization/writeback
- high-severity unresolved feedback exists

If evidence is present but still needs human checks, the preview returns `review_needed`.

If material evidence is sufficient for review only, it may return `material_card_review_ready`; the UI explicitly states this is not material-card formalization.

If proto trial is available while formal generation is still blocked, the preview may return `proto_ready`.

## Unsafe Field Interception

The JS recursively scans pasted JSON for unsafe true-valued fields:

- `formalized`
- `writeback_allowed`
- `executor_allowed`
- `verified`
- `verified_original_source`
- `material_card_write`
- `card_specs_write`
- `passage_service_ingest`
- `promotion_target_added`

Any unsafe field with value `true` forces `status=blocked` and appears in the warning list.

## Browser Smoke

Ran a real browser smoke test against:

- `http://127.0.0.1:8017/demo-static/distill_demo.html`

Actions:

1. Opened the distill workbench.
2. Clicked `fillBlockedFormalGateExampleBtn`.
3. Generated Gate Preview.
4. Verified output status is `blocked`.
5. Verified output fields:
   - `formalized=false`
   - `writeback_allowed=false`
   - `executor_allowed=false`

Screenshot:

- `docs/distill_workbench_formalization_gate_ui_2026-04-28.png`

## Tests

Passed:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
# Ran 88 tests - OK

$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
# Ran 12 tests - OK

$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
# Ran 10 tests - OK

$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
# Ran 4 tests - OK
```

## Explicit Non-Actions

This change did not:

- perform formal writeback
- call executor
- write `card_specs`
- write `material_card`
- verify sources
- ingest into passage_service
- modify runtime/prompt/validator/generation main chain
- add a promotion target
- call external LLM or network APIs

## Acceptance Conclusion

The frontend workbench now extends the user flow to:

`proto trial -> review -> axis confirmation -> formal_patch_draft -> promotion bundle -> source review -> agent feedback -> formalization packet/runtime/readiness gate preview`

It still does not formalize, write back, verify sources, ingest materials, or execute guarded writeback.

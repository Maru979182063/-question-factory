# Leaf Pre-Distill LLM Field Probe Execution Report

Date: 2026-04-25

## Scope

This slice adds an optional LLM-safe digest and field-probe layer to the offline `leaf_pre_distill` toolchain.

The layer is evidence-only. It does not change formal card specs, validators, prompt assets, runtime mappings, database schema, API surface, or promotion targets.

## Added Artifacts

- `llm_safe_digest.json`
- `llm_field_probe.json`

Both artifacts are attachments to `leaf_pre_distill_report`. Neither artifact is an independent promotion target.

## Behavior

Default behavior remains closed:

- no `--enable-llm-probe`: no model request
- no `--enable-llm-probe`: no LLM artifacts are generated
- `--llm-dry-run`: writes digest and a disabled probe without calling a model

When enabled, the tool:

1. Builds a short digest from existing samples, behavior traces, field candidates, and slot projection.
2. Excludes raw docx text, full stems, full analyses, and raw sample text.
3. Calls an OpenAI-compatible chat endpoint only through environment-provided credentials.
4. Writes normalized `llm_field_probe.json`.
5. Appends an `LLM Field Probe` section to `report.md`.

## Probe Constraints

- `should_promote` is always forced to `false`.
- `confirmed_fields` can only include existing field candidates or existing slot projection fields.
- Unknown model suggestions are moved to `rejected_suggestions`.
- Invalid JSON or request errors produce `usable=false` and do not interrupt the main flow.

## Validation

Commands run:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
python -m py_compile tools/leaf_pre_distill/llm_safe_digest.py tools/leaf_pre_distill/llm_field_probe.py tools/leaf_pre_distill/run.py tools/leaf_pre_distill/report_renderer.py
```

Result:

- `test_leaf_pre_distill.py`: 9 tests OK
- `test_distill_workbench.py`: 10 tests OK
- `py_compile`: OK

## Boundary Confirmation

- No new promotion target was added.
- `slot_projection_draft` remains attachment-only.
- `llm_field_probe` is not a promotion judge.
- No automatic write-back to `card_specs`.
- No generation service changes.
- No validator main-logic changes.
- No raw docx or raw sample text is sent to the model by this layer.

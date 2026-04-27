# Truth Gold Regression Loop V1 Execution Report

Date: 2026-04-26

## Scope

Implemented offline `truth_gold_regression_loop v1`.

This is a quality-regression loop for truth-gold question packs. It does not write formal configuration and does not modify the generation, validator, prompt, card, API, database, or frontend main chains.

## New Module

```text
tools/leaf_pre_distill/truth_gold_regression.py
```

Supported flows:

1. Run as part of `run_leaf_pre_distill` when explicitly enabled.
2. Run directly from an existing artifact directory:

```powershell
python -m tools.leaf_pre_distill.truth_gold_regression --artifact-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425 --output-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1
```

## New Artifacts

```text
truth_gold_split_manifest.json
truth_gold_regression_results.json
truth_gold_regression_report.md
```

These are evidence attachments for `leaf_pre_distill_report`.

They are not independent promotion targets and are not formal writeback approval.

## Capabilities

### Gold Split

The loop creates deterministic splits:

- `train_observation`
- `dev_tuning`
- `eval`
- `insurance_holdout`

The insurance holdout is explicitly recorded and must not be used for axis discovery or prompt tuning.

### Gold-Only Baseline

If no generated items are available, the loop still produces:

- split manifest;
- regression results with `mode = gold_only_baseline`;
- report with generated comparison marked unavailable.

This is intentional. Missing generated items should not block dataset quality preparation.

### Generated Comparison

If `generated_items.jsonl` or a provided generated-items path exists, the loop compares original gold samples to generated items by `sample_id`.

First-pass dimensions:

- `material_alignment`
- `stem_intent_alignment`
- `answer_mechanism_alignment`
- `distractor_mechanism_alignment`
- `explanation_path_alignment`
- `difficulty_signal_alignment`
- `overfit_risk`

Each dimension records:

- `method`
- `confidence`
- `limitation`

The scoring is deterministic heuristic/lexical/metadata based. It is not a human quality judgment.

## Smoke Test

Input:

```text
data/leaf_pre_distill/real_word_usage_full_chain_20260425
```

Output:

```text
data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_split_manifest.json
data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_regression_results.json
data/leaf_pre_distill/real_word_usage_full_chain_20260425/truth_gold_regression_v1/truth_gold_regression_report.md
```

Smoke result:

- gold sample count: 50
- train/dev/eval/insurance: 20 / 10 / 10 / 10
- mode: `gold_only_baseline`
- generated comparison: unavailable
- no failure

## Tests

Passed:

```powershell
python -m py_compile tools/leaf_pre_distill/truth_gold_regression.py tools/leaf_pre_distill/run.py tools/leaf_pre_distill/report_renderer.py tests/test_leaf_pre_distill.py
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Coverage added:

- default disabled state creates no truth-gold artifacts;
- enabled gold-only run creates split/results/report;
- split count sums to sample count;
- insurance holdout is non-empty;
- generated comparison creates sample results;
- high lexical similarity is flagged as high overfit risk;
- report section is appended to `report.md`;
- artifact contract documents new artifacts;
- existing axis confirmation, patch draft, writeback plan, and executor tests still pass.

## Explicit Non-Changes

- No generation service change.
- No validator change.
- No input decoder change.
- No question card binding change.
- No prompt templates change.
- No card specs writeback.
- No runtime mapping or material mapping change.
- No API change.
- No frontend UI change.
- No promotion target added.

## Important Limitation

High fit is not proof of true-question quality.

In v1, high similarity can indicate:

- good replay resemblance;
- source wording reuse;
- overfit risk.

The report therefore labels scoring method and limitation for each dimension and keeps `ready_for_formalization=false`.

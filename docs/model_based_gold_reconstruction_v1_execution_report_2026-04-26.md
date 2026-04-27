# Model-Based Gold Reconstruction V1 Execution Report

Date: 2026-04-26

## Scope

Implemented offline `model_based_gold_reconstruction v1`.

This layer converts raw true-question samples into a unified gold reconstruction schema. It does not discover protocol fields, does not generate formal cards, and does not write any formal config.

## New Files

```text
tools/leaf_pre_distill/gold_reconstruction.py
tools/leaf_pre_distill/gold_reconstruction_prompt.py
```

Modified integration points:

```text
tools/leaf_pre_distill/run.py
tools/leaf_pre_distill/report_renderer.py
tools/leaf_pre_distill/truth_gold_regression.py
docs/leaf_pre_distill_artifact_contract.md
tests/test_leaf_pre_distill.py
```

## New Artifacts

```text
model_safe_gold_reconstruction_input.jsonl
gold_reconstruction_results.jsonl
gold_reconstruction_report.md
```

These artifacts are evidence attachments for `leaf_pre_distill_report`.

They are not independent promotion targets and are not formal writeback approval.

## Modes

### Dry-run

Creates only:

```text
model_safe_gold_reconstruction_input.jsonl
```

No model call. No reconstruction results.

### Mock

Creates deterministic mock reconstruction results without external calls. Used for tests and pipeline smoke.

### LLM

Calls an OpenAI-compatible chat endpoint using an environment variable key. The key is not hard-coded. Invalid JSON or request failure marks the sample as `needs_human_review=true` and does not interrupt the whole run.

## Responsibility Split

Model layer:

- reads the true question package;
- decides what must be reconstructed for a reliable gold reference;
- reconstructs gold material/question/mechanism into the unified schema;
- marks evidence, uncertainty, confidence, warnings, and human-review needs.

Mechanical layer:

- builds model-safe inputs;
- records sample id, source metadata, hash, and truncation;
- checks JSON/required fields;
- checks confidence/warnings/review flags exist;
- checks answer/options basic consistency;
- summarizes warnings and low-confidence samples.

Mechanical layer does not judge semantic correctness.

## Truth-Gold Regression Integration

`truth_gold_regression.py` now prefers:

```text
gold_reconstruction_results.jsonl
```

when available.

It records:

```json
"gold_source": "gold_reconstruction_results"
```

If reconstruction is unavailable, it falls back to raw samples and records:

```json
"gold_source": "raw_samples"
```

## Smoke Test

Input:

```text
data/leaf_pre_distill/real_word_usage_full_chain_20260425
```

Output:

```text
data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_v1_mock
```

Smoke result:

- `model_safe_gold_reconstruction_input.jsonl`: created
- `gold_reconstruction_results.jsonl`: created
- `gold_reconstruction_report.md`: created
- `truth_gold_regression_results.json`: records `gold_source=gold_reconstruction_results`
- sample count: 50
- mock mode marked samples for human review when low-level structure was insufficient

## Tests

Passed:

```powershell
python -m py_compile tools/leaf_pre_distill/gold_reconstruction.py tools/leaf_pre_distill/gold_reconstruction_prompt.py tools/leaf_pre_distill/truth_gold_regression.py tools/leaf_pre_distill/run.py tools/leaf_pre_distill/report_renderer.py tests/test_leaf_pre_distill.py
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Coverage added:

- default disabled state creates no gold reconstruction artifacts;
- dry-run creates model-safe input only;
- mock mode creates unified schema results and report;
- results contain confidence, warnings, and needs-human-review;
- forbidden names such as `confirmed_fields`, validator rules, prompt guards, and card specs are absent;
- invalid model JSON marks the sample for human review without interrupting the run;
- mechanical checks remain structural;
- truth-gold regression prefers reconstructed gold when available;
- raw sample fallback still records `gold_source=raw_samples`;
- artifact contract documents new artifacts.

## Explicit Non-Changes

- No generation service change.
- No validator change.
- No input decoder change.
- No question card binding change.
- No prompt template change.
- No card specs writeback.
- No runtime mapping or material mapping change.
- No API change.
- No frontend UI change.
- No promotion target added.
- No formal writeback executor change.

## Boundary

This layer is gold schema reconstruction.

It is not:

- protocol field discovery;
- formal question card generation;
- prompt guard generation;
- validator rule generation;
- semantic correctness certification.

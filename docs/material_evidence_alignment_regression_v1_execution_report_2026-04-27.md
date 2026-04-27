# Material Evidence Alignment Regression v1 Execution Report

## Status

Completed.

This round adds three offline, reviewable material-line evidence gates:

1. `source_text_evidence`
2. `source_gold_alignment`
3. `material_quality_regression`

They remain evidence artifacts only. They do not verify original source, ingest into `passage_service`, write `material_card`, write `card_specs`, or change runtime/prompt/validator/generation main-chain logic.

## Modified Files

- `tools/leaf_pre_distill/material_evidence_alignment_regression.py`
- `tools/leaf_pre_distill/run.py`
- `tools/leaf_pre_distill/report_renderer.py`
- `tests/test_leaf_pre_distill.py`
- `docs/leaf_pre_distill_artifact_contract.md`
- `docs/material_evidence_alignment_regression_v1_execution_report_2026-04-27.md`

## New Artifacts

Source text evidence:

- `source_text_evidence_approval.json`
- `source_text_evidence_manifest.json`
- `source_text_evidence_results.jsonl`
- `source_text_evidence_report.md`

Source/gold alignment:

- `source_gold_alignment_results.jsonl`
- `source_gold_alignment_summary.json`
- `source_gold_alignment_report.md`
- `source_gold_alignment_review.json`

Material quality regression:

- `material_quality_regression_results.json`
- `material_quality_regression_report.md`
- `material_quality_review.json`

## Source Text Evidence

Implemented as an offline gate in `tools/leaf_pre_distill/material_evidence_alignment_regression.py`.

Inputs:

- `source_seed_registry.jsonl`
- `crawl_seed_manifest.json`
- `source_text_evidence_approval.json`
- optional manual source text JSONL

Supported modes:

- `mock`: produces reviewable source text evidence from seed metadata for tests and smoke.
- `manual`: requires user-provided text; otherwise rows are marked `manual_required`.

Boundary guarantees:

- only approved seed IDs are processed;
- `verified=false`;
- `verified_original_source=false`;
- `formalized=false`;
- no material library write;
- no material card write;
- unavailable text is recorded as `manual_required` or blocked, not fabricated.

## Source/Gold Alignment

Implemented as an offline heuristic alignment gate.

Inputs:

- `source_text_evidence_results.jsonl`
- `gold_reconstruction_results.jsonl`
- source seed metadata carried through source text evidence

Supported modes:

- `dry-run`: checks inputs and marks rows for review.
- `mock`: deterministic lexical overlap and risk classification.

Boundary guarantees:

- alignment is not source verification;
- `original_source_candidate` remains unverified;
- similar material is not original source;
- no material card or material library write.

## Material Quality Regression

Implemented as readiness evidence.

Inputs:

- `gold_reconstruction_results.jsonl`
- `source_text_evidence_results.jsonl`
- `source_gold_alignment_results.jsonl`
- optional `material_card_draft.json`
- optional `material_quality_regression_draft.json`
- optional `agent_review_feedback_normalized.json`

Dimensions covered:

- `source_provenance_status`
- `question_bank_contamination`
- `source_gold_alignment`
- `material_independence`
- `material_sufficiency`
- `context_dependency`
- `slicing_potential`
- `family_fit`
- `distractor_support`
- `overfit_or_copy_risk`
- `bridge_compatibility`
- `human_review_required`

Boundary guarantees:

- high score cannot auto-approve formalization;
- low contamination does not equal verified source;
- material quality regression is readiness evidence, not material-card approval.

## User Confirmation Points

Implemented:

- `source_text_evidence_approval.json`: user approval to prepare source text evidence from selected seed-only source candidates.

Prepared as review schemas:

- `source_gold_alignment_review.json`: user review point for alignment relationship and uncertainty.
- `material_quality_review.json`: user review point for material quality diagnosis.

## Report Renderer

`report.md` now appends these sections when matching artifacts/summaries are present:

- `Source Text Evidence`
- `Source/Gold Alignment`
- `Material Quality Regression`

Each section records status, counts, blocked count, human review requirement, verified-original-source count, readiness conclusion, and next action.

## Artifact Contract

`docs/leaf_pre_distill_artifact_contract.md` now documents all new artifacts.

All are:

- promotion evidence only as attachments to `leaf_pre_distill_report`;
- not direct formal config;
- not independent promotion targets.

## Model / Web Usage

- Model used: no.
- Real external web access: no.
- Body fetch/crawler execution: no.

This v1 uses manual/mock source text evidence and deterministic alignment/regression checks.

## Material Card Formalization

Current result: not ready for material card formalization.

Reason:

- source text evidence remains unverified;
- source/gold alignment still requires human review;
- material quality regression is readiness evidence only;
- no source verification, source body confirmation, or writeback approval has occurred.

## Tests

Executed:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

- OK, 86 tests.

Executed:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

Result:

- OK, 11 tests.

Executed:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

Result:

- OK, 10 tests.

Executed:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Result:

- OK, 4 tests.

## Explicit Non-Changes

This round did not:

- verify original source;
- fetch external source bodies;
- ingest into `passage_service`;
- write `material_card`;
- write `card_specs`;
- write runtime mapping;
- write prompt assets;
- write validator logic or validator contracts;
- change generation main-chain logic;
- perform material promotion;
- add promotion targets.


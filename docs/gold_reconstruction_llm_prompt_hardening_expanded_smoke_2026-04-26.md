# Gold Reconstruction LLM Prompt Hardening Expanded Smoke

Date: 2026-04-26

## Scope

This run validates prompt hardening for `gold_material.restored_text` and the new question-wrapper leakage check.

It only covers the material-line smoke:

- no web search
- no source confirmation
- no material_card writeback
- no card_specs writeback
- no prompt/generation/validator/runtime/API/UI changes
- no effect on the card/protocol line

## Code Changes

- `tools/leaf_pre_distill/gold_reconstruction_prompt.py`
  - Added source-like material rules.
  - Explicitly forbids question stem wording, option labels, answer/explanation boilerplate, exam meta language, and common question-wrapper terms in `gold_material.restored_text`.
  - Added `gold_quality_flags.question_wrapper_leakage_risk`.

- `tools/leaf_pre_distill/gold_reconstruction.py`
  - Added `QUESTION_WRAPPER_TERMS`.
  - Added mechanical leakage check for `gold_material.restored_text`.
  - When leakage is detected, sets `question_wrapper_leakage_risk=high`, marks `needs_human_review=true`, and appends `restored_text_contains_question_wrapper_terms`.

- `tools/leaf_pre_distill/source_discovery_preparation.py`
  - Raises contamination risk when reconstruction leakage is high.
  - Lowers query confidence when leaked text still produces candidate queries.

- `tools/leaf_pre_distill/gold_reconstruction_llm_smoke.py`
  - Added smoke report engineering parameters: max input chars, max output tokens, max retry per sample.
  - Added parse success, failed sample ids, leakage distribution, and query quality distribution.
  - Added optional `--report-name`.

- `tests/test_leaf_pre_distill.py`
  - Added prompt hardening, leakage check, source contamination escalation, and expanded smoke report tests.

## Expanded Real LLM Smoke

Command shape:

```powershell
python -m tools.leaf_pre_distill.gold_reconstruction_llm_smoke `
  --artifact-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425 `
  --output-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b `
  --sample-size 8 `
  --seed 7 `
  --gold-reconstruction-model chat `
  --gold-reconstruction-base-url https://new.fastaicode.top `
  --gold-reconstruction-api-key-env LEAF_PRE_DISTILL_LLM_API_KEY `
  --gold-reconstruction-max-input-chars 2500 `
  --gold-reconstruction-max-output-tokens 1000 `
  --gold-reconstruction-timeout-seconds 45 `
  --report-name gold_reconstruction_llm_prompt_hardening_smoke_report.md `
  --run-llm
```

The API key was provided through environment variable only and was not written to code or docs.

## Sample IDs

- `实词_2637844`
- `实词_2727570`
- `实词_5407266`
- `实词_2461791`
- `实词_5626725`
- `实词_2830937`
- `实词_5598288`
- `实词_5498124`

## Results

- request_count: 8
- parse_success_count: 8
- failed_count: 0
- reconstruction_success_rate: 100%
- confidence distribution:
  - high: 6
  - medium: 2
- reconstruction needs_human_review_count: 2
- question_wrapper_leakage_risk distribution:
  - low: 8

## Source Discovery Preparation

- query_rows: 8
- seed_rows: 8
- natural_material_quality: high
- query_de_question_bank_score: high
- source_discovery_readiness: ready
- contamination risk distribution:
  - low: 8
- query quality distribution:
  - high: 27
  - medium: 9

Compared with the previous mock baseline where 50/50 rows were high risk, this expanded real LLM smoke produced no high contamination rows in the 8-sample subset.

## Judgment

`ready_for_source_candidate_search`: ready for a small pilot.

Recommendation:

- Proceed to `source_candidate_search v1` only as a bounded pilot.
- Start from low-risk rows in this smoke output.
- Keep source confirmation human-reviewed.
- Do not treat reconstructed material as verified source text yet.

## Tests

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

- Ran 47 tests
- OK

## Boundaries

- No web search was executed.
- No original source was confirmed.
- No material_card was written.
- No card_specs files were written.
- No promotion target was added.
- No generation, validator, prompt, runtime, API, or UI code was changed.
- The card/protocol line was not affected by this material-line smoke.

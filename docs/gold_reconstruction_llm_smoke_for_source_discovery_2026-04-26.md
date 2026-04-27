# Gold Reconstruction LLM Smoke for Source Discovery v1

## Scope

This smoke validates whether a small LLM gold reconstruction pass can produce natural material clues for `source_discovery_preparation`.

It does not run web search, does not confirm original sources, does not write `material_card` or `card_specs`, and does not affect the card/protocol line.

## Implementation

Added:

- `tools/leaf_pre_distill/gold_reconstruction_llm_smoke.py`

The module:

1. reads `manifest.json` and `samples.jsonl`;
2. selects a fixed-seed small sample;
3. writes `llm_smoke_sample_manifest.json`;
4. runs `gold_reconstruction` in dry-run or explicit `--run-llm` mode;
5. when LLM results exist, runs `source_discovery_preparation` without raw fallback;
6. writes `gold_reconstruction_llm_smoke_report.md`.

## CLI

Dry run:

```powershell
python -m tools.leaf_pre_distill.gold_reconstruction_llm_smoke `
  --artifact-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425 `
  --output-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_smoke_v1_dry_run `
  --sample-size 8 `
  --seed 7 `
  --gold-reconstruction-model chat `
  --dry-run
```

LLM run:

```powershell
python -m tools.leaf_pre_distill.gold_reconstruction_llm_smoke `
  --artifact-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425 `
  --output-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_smoke_v1 `
  --sample-size 3 `
  --seed 7 `
  --gold-reconstruction-model chat `
  --gold-reconstruction-base-url https://new.fastaicode.top `
  --gold-reconstruction-api-key-env OPENAI_API_KEY `
  --run-llm
```

The key is read from the environment. No key is hard-coded into source, docs, or artifacts.

## Dry Run Result

Output:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_smoke_v1_dry_run`

Artifacts:

- `llm_smoke_sample_manifest.json`
- `model_safe_gold_reconstruction_input.jsonl`
- `gold_reconstruction_llm_smoke_report.md`

No LLM request was made and no source discovery artifacts were generated in dry-run mode.

## Real LLM Smoke Result

Output:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_smoke_v1`

Sample size: 3

Sample ids:

- `瀹炶瘝_2637844`
- `瀹炶瘝_2727570`
- `瀹炶瘝_5407266`

Observed:

- LLM requests attempted: 3
- Parsed reconstruction success: 0
- Failed / needs human review: 3
- `source_discovery_queries.jsonl` rows: 3
- `initial_material_seed_pack.jsonl` rows: 3
- contamination risk distribution: `high=3`
- source discovery readiness: `blocked`

Because every LLM output failed JSON parsing, `source_discovery_preparation` now refuses to use the question stem as a substitute material source. The affected rows are high risk, query-less, and require human review.

## Mock Comparison

The previous mock gold source discovery profile was:

- mock contamination risk: `high=50`

The real LLM smoke did not improve readiness in this run because no valid reconstructed gold was produced. This is still a useful negative result: the chain now blocks rather than producing fake source queries from failed reconstructions.

## Decision

Not ready for `source_candidate_search v1` yet.

Before source search, the LLM reconstruction call needs one of:

- a compatible model/endpoint response that returns JSON-only content;
- a stronger repair/extraction layer for model outputs;
- a smaller input or stricter prompt if the endpoint is returning empty or non-JSON content.

## Tests

Executed:

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`

Result:

- 38 tests passed.

## Boundaries

- No web search was executed.
- No original source was confirmed.
- No `material_card` was written.
- No `card_specs` files were written.
- No promotion target was added.
- No generation, validator, prompt, runtime, API, UI, or formal writeback logic was changed.
- The card/protocol line was not affected.

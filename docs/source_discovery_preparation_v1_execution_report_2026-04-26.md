# Source Discovery Preparation v1 Execution Report

## Scope

Implemented the first material-line offline preparation layer:

`gold_reconstruction_results.jsonl` -> source discovery query candidates -> material source profile -> initial material seed pack.

This layer prepares material clues for later source discovery and passage tooling. It does not run web search, does not write a material library, and does not modify card/prompt/validator/runtime configuration.

## Added Artifacts

- `source_discovery_queries.jsonl`
- `material_source_profile.json`
- `initial_material_seed_pack.jsonl`
- `source_discovery_preparation_report.md`

All four artifacts are evidence attachments under `leaf_pre_distill_report`. None is an independent promotion target.

## Implementation Notes

- The prep layer prefers `gold_reconstruction_results.jsonl`.
- If reconstructed gold is missing and raw fallback is not enabled, it writes a blocked profile/report without crashing.
- Raw fallback is opt-in and marks `using_raw_sample_material=true`, high contamination risk, and human-review requirements.
- Query generation removes or avoids obvious question-bank terms such as stem/answer/explanation markers, answer-analysis wording, and exam metadata.
- `initial_material_seed_pack.jsonl` is always seed-only: `status=seed_only`, `formalized=false`.

## CLI

`tools/leaf_pre_distill/run.py` now supports:

- `--enable-source-discovery-prep`
- `--source-discovery-output-dir`
- `--source-discovery-max-queries-per-sample`
- `--source-discovery-min-query-chars`
- `--source-discovery-use-raw-fallback`

The standalone module also supports:

- `python -m tools.leaf_pre_distill.source_discovery_preparation --artifact-dir ...`
- optional `--gold-reconstruction-results ...`
- optional `--output-dir ...`

## Smoke Result

Ran the material prep over:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425`

using reconstructed gold from:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_v1_mock/gold_reconstruction_results.jsonl`

Output directory:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_discovery_prep_v1`

Observed:

- 50 query rows generated.
- 50 material seeds generated.
- `gold_source=gold_reconstruction_results`.
- No web search was executed.
- The profile marks all rows high contamination risk because the mock reconstructed gold still contains question-bank/source-pack metadata, so it is not ready for material-card drafting.

## Tests

Executed:

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`

Result:

- 35 tests passed.

## Boundaries

- No `material_card` was written.
- No `card_specs` files were written.
- No promotion target was added.
- No generation, validator, prompt, runtime, API, UI, database, or formal writeback executor logic was changed.
- The material line does not automatically affect the card/protocol line.

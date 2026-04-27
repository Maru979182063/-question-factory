# Source Candidate Search v1 Web Smoke Report

Date: 2026-04-26

## Scope

This is a real search-provider smoke for `source_candidate_search v1`.

It only tests whether the provider can return candidate URL/title/snippet/domain metadata for human review. It does not open candidate pages, fetch article bodies, confirm original sources, write a material library, generate a material card, or affect the card/protocol line.

## Provider

- provider: `web`
- implementation: DuckDuckGo HTML search with Bing HTML fallback
- API key: none hardcoded; no search API key was used
- real network search: yes
- candidate page body fetch: no

## Input

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/source_discovery_queries.jsonl`

## Output

`E:/agent_repo_src/data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_web_smoke`

Artifacts:

- `search_request_manifest.json`
- `source_candidate_results.jsonl`
- `source_candidate_summary.json`
- `source_candidate_alignment_report.md`

## Limits

- max_samples: 3
- max_queries_per_sample: 2
- max_results_per_query: 5
- allowed_risk: `low`
- run_search: true

Selected samples:

- `实词_2637844`
- `实词_2727570`
- `实词_5407266`

## Results

- provider_status: `ok`
- sample_count: 3
- query_count: 6
- candidate_count: 30
- verified values: `false` only
- verification_status: `unverified` only

Candidate status counts:

- `blocked`: 23
- `question_bank_like`: 2
- `weak_candidate`: 5

Source risk counts:

- `unknown`: 23
- `question_bank_like`: 2
- `low`: 5
- `exam_training_like`: 0

Readiness:

- ready_for_human_source_review: true
- ready_for_material_card_draft: false
- blocked: false

## Interpretation

The real provider can return reviewable candidate metadata. The system did not auto-confirm any source and did not hide risky results.

The result is suitable for a human source-review step because at least some low-risk candidates exist for the selected samples. It is not suitable for material-card drafting yet:

- most candidates remain `unknown` and `blocked`;
- low-risk candidates are still only weak candidates;
- no article body was fetched;
- no source was verified against the restored material.

## Boundaries

- No original source was confirmed.
- No webpage body was fetched.
- No material library write occurred.
- No material_card was written.
- No card_specs files were written.
- No promotion target was added.
- No generation, validator, prompt, runtime, API, or UI code was changed.
- The card/protocol line was not affected.

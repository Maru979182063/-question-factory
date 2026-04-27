# Source Candidate Search v1 Execution Report

Date: 2026-04-26

## Scope

This is a bounded material-line pilot for source candidate search.

It produces unverified candidate sources only. It does not confirm original sources, fetch full article bodies, write a material library, generate a material card, or affect the card/protocol line.

## Modified Files

- `tools/leaf_pre_distill/source_candidate_search.py`
- `tools/leaf_pre_distill/run.py`
- `tools/leaf_pre_distill/report_renderer.py`
- `docs/leaf_pre_distill_artifact_contract.md`
- `tests/test_leaf_pre_distill.py`

## New Artifacts

- `search_request_manifest.json`
- `source_candidate_results.jsonl`
- `source_candidate_summary.json`
- `source_candidate_alignment_report.md`

All artifacts are evidence attachments for `leaf_pre_distill_report`; none is a formal config artifact or independent promotion target.

## Provider Strategy

Implemented providers:

- `manual`: dry/manual request manifest provider, no network.
- `mock`: deterministic test/pilot provider, no network.
- `web`: explicit unavailable stub for v1.

No real web search provider is configured in this v1 implementation.

## Pilot Run

Input:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/source_discovery_queries.jsonl`

Command shape:

```powershell
python -m tools.leaf_pre_distill.source_candidate_search `
  --source-discovery-queries data/leaf_pre_distill/real_word_usage_full_chain_20260425/gold_reconstruction_llm_prompt_hardening_smoke_v1_sample8b/source_discovery_queries.jsonl `
  --output-dir data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_mock_pilot `
  --max-samples 3 `
  --max-queries-per-sample 2 `
  --max-results-per-query 2 `
  --allowed-risk low `
  --search-provider mock `
  --run-search
```

Output directory:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_mock_pilot`

Selected samples:

- `实词_2637844`
- `实词_2727570`
- `实词_5407266`

Results:

- provider: `mock`
- real network search: `false`
- selected_sample_count: 3
- query_count: 6
- candidate_count: 12
- candidate_status_counts:
  - candidate: 6
  - question_bank_like: 6
- source_risk_counts:
  - low: 6
  - exam_training_like: 6
- verified values:
  - false only
- ready_for_human_source_review: true
- ready_for_material_card_draft: false

## Interpretation

The pilot proves the evidence chain and filtering behavior:

- low-risk source discovery rows can be selected;
- search requests are bounded by sample/query/result limits;
- positive-looking source candidates and exam-training-like candidates are both retained for audit;
- exam-training/question-bank results are downgraded rather than silently deleted;
- no candidate is marked verified.

Because the provider was mock and no real web search was executed, this does not prove actual source findability.

## Tests

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

- Ran 53 tests
- OK

Additional regressions:

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Results:

- `test_distill_workbench`: Ran 10 tests, OK
- `test_word_usage_proto_mapping`: Ran 4 tests, OK

## Boundaries

- No original source was confirmed.
- No real web search was executed.
- No material_card was written.
- No passage-service or material-library write occurred.
- No card_specs files were written.
- No promotion target was added.
- No generation, validator, prompt, runtime, API, or UI code was changed.
- The card/protocol line was not affected.

## Next Step

If the user wants real source discovery, the next safe step is adding a real search provider behind the same bounded interface, then running:

- max_samples <= 3
- max_queries_per_sample <= 2
- max_results_per_query <= 5
- low-risk rows only
- no article-body fetch
- no source confirmation without human review

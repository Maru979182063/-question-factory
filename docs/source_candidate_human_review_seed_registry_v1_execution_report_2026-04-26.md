# Source Candidate Human Review + Seed Registry v1 Execution Report

Date: 2026-04-26

## Scope

Implemented the offline human-review layer for source candidates.

This layer turns reviewed source candidates into seed-only source assets. It does not confirm original sources, fetch web page bodies, run crawlers, write a material library, generate a material card, or affect the card/protocol line.

## Modified Files

- `tools/leaf_pre_distill/source_candidate_review.py`
- `tools/leaf_pre_distill/run.py`
- `tools/leaf_pre_distill/report_renderer.py`
- `docs/leaf_pre_distill_artifact_contract.md`
- `tests/test_leaf_pre_distill.py`

## New Artifacts

- `source_candidate_review_decisions.json`
- `source_candidate_review.json`
- `source_seed_registry.jsonl`
- `crawl_seed_manifest.json`
- `source_candidate_human_review_report.md`

All are evidence attachments for `leaf_pre_distill_report`. None is an independent promotion target or formal config artifact.

## Fixture Decision

Input candidates came from:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_search_v1_web_smoke/source_candidate_results.jsonl`

Fixture decision file:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture/source_candidate_review_decisions.json`

Decision overview:

- 1 `keep_as_similar_material_seed`
  - `https://www.nju.edu.cn/info/3191/215671.htm`
  - source_use: `similar_material`
- 1 `keep_as_original_source_candidate`
  - `https://digitalhumanities.nju.edu.cn/publication/5eddb5c68c265c25e6/`
  - source_use: `original_source_candidate`
- 1 `reject_question_bank`
  - `https://www.zhihu.com/tardis/bd/ans/3436290976`
- 1 `reject_irrelevant`
  - Baidu Baike concept page for carbon dioxide fertilization effect
- 1 `defer`
  - `https://news.gmw.cn/2021-07/05/content_34969912.htm`

## Fixture Output

Output directory:

`data/leaf_pre_distill/real_word_usage_full_chain_20260425/source_candidate_human_review_v1_fixture`

Observed:

- accepted_count: 2
- rejected_count: 2
- deferred_count: 1
- seed_count: 2
- risky_accepted_seed_count: 0
- verified_original_source_count: 0
- crawl_allowed: false
- recommended_limits.fetch_body: false
- ready_for_crawl_review: true
- ready_for_material_card_draft: false

Generated seeds:

1. Similar material seed
   - domain: `www.nju.edu.cn`
   - title: `二氧化碳浓度越高，植物生长越快？ - 南京大学`
   - source_use: `similar_material`
   - crawl_priority: `high`
   - verified: false
   - verified_original_source: false
   - status: `seed_only`

2. Original-source candidate seed
   - domain: `digitalhumanities.nju.edu.cn`
   - title: `零壹Lab | 数字人文：概念、历史、现状及其在文学研究中的应用（上）`
   - source_use: `original_source_candidate`
   - crawl_priority: `medium`
   - verified: false
   - verified_original_source: false
   - status: `seed_only`

## Boundary Checks

- `keep_as_original_source_candidate` still produces `verified_original_source=false`.
- `human_opened_url=false` cannot produce verified source.
- `reject_question_bank` creates no seed.
- `reject_irrelevant` creates no seed.
- `defer` creates no seed.
- Risky candidates require explicit allowance to become seeds.
- `crawl_seed_manifest.crawl_allowed=false`.
- `crawl_seed_manifest.ready_for_material_card_draft=false`.

## Tests

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

- Ran 62 tests
- OK

## Explicit Non-Changes

- No original source was confirmed.
- No webpage body was fetched.
- No crawler was executed.
- No material library was written.
- No material_card was generated.
- No card_specs files were written.
- No promotion target was added.
- No generation, validator, prompt, runtime, API, or UI code was changed.
- The card/protocol line was not affected.

## Next Step

The next safe material-line step is not `material_card` yet.

The next step should be either:

- crawl approval over the seed registry; or
- a manual source-review UI/flow that lets users mark more candidates as similar material, original-source candidates, domain seeds, rejects, or deferred items.

Only after approved seeds produce source bodies should the system attempt source/gold alignment and material cleaning recipes.

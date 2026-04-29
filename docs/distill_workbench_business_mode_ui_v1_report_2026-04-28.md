# Distill Workbench Business Mode UI v1 Report

## Scope

This round adds a business-facing layer to the distill workbench. It does not replace the engineering control plane. It gives non-technical reviewers a shorter path:

1. choose or paste a question pack,
2. see what family the system thinks it found,
3. see candidate core traits,
4. record whether the user accepts the interpretation,
5. review trial and feedback signals,
6. read the readiness gate in plain language,
7. get a card-family draft report.

## Modified Files

- `prompt_skeleton_service/app/demo_static/distill_demo.html`
- `prompt_skeleton_service/app/demo_static/distill_demo.js`
- `prompt_skeleton_service/tests/test_demo_shell.py`

## Business Mode Behavior

The workbench now defaults to the `business_mode` layer. The original engineering layers remain available:

- data/trial
- protocol/patch
- material/feedback
- formalization gate
- status/history

The business layer hides technical JSON by default and keeps it under "technical details".

## Plain-Language Gate Translation

The business layer translates technical gate statuses such as `blocked`, `review_needed`, `material_quality_regression_blocked`, and `source_gold_alignment_review_required` into user-facing conclusions:

- whether the leaf can be formalized now,
- why it cannot be formalized,
- what evidence is missing,
- what the next user action should be.

The underlying JSON remains available but is no longer the primary business surface.

## Card-Family Draft Report

The UI can generate a readable `business_card_family_draft_report.md` preview containing:

- inferred mother/child/leaf family context,
- core traits,
- user feedback dimensions,
- material-line status,
- current readiness conclusion,
- next steps.

This is a business draft report only. It is not a formal question card, material card, prompt asset, validator contract, runtime mapping, or writeback plan.

## Question Pack Format Support

Current frontend direct preview support:

- `.json`
- `.jsonl`
- `.csv`
- `.txt`

Current offline tool support already present:

- `.docx` through `tools/leaf_pre_distill/docx_reader.py` / `tools/leaf_pre_distill/run.py`

Not yet native in frontend:

- `.docx`
- `.xlsx`
- `.pdf`

If a user selects DOCX/XLSX/PDF in the browser, business mode records an explicit "not supported for browser preview" diagnosis instead of pretending upload worked. A real product upload route should later connect DOCX parsing to the existing offline `leaf_pre_distill` parser or a backend upload endpoint.

## Browser Smoke

Smoke target:

- `http://127.0.0.1:8017/demo-static/distill_demo.html`

Verified:

- default visible form is only `businessModeForm`,
- "fill business example" generates a plain-language conclusion,
- generated preview JSON keeps `status=blocked`,
- card-family draft report is generated,
- no page JavaScript errors.

Screenshot:

- `docs/distill_workbench_business_mode_smoke_2026-04-28.png`

## Tests

Passed:

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`

## Boundaries

This round did not:

- add formal writeback,
- call the executor,
- write `card_specs`,
- write a formal `material_card`,
- verify source articles,
- ingest into `passage_service`,
- modify runtime/prompt/validator/generation main-chain code.


# Distill Workbench Question Pack Multi-Format Support

## Scope

This round opens the business-mode question pack entrance to common user-provided file formats:

- PDF
- CSV
- DOC
- DOCX
- JSON
- JSONL
- Markdown (`.md`, `.markdown`)
- TXT
- XLSX

The goal is preview and evidence intake, not formal card writeback.

## Modified Files

- `prompt_skeleton_service/app/services/question_pack_preview.py`
- `prompt_skeleton_service/app/routers/distill.py`
- `prompt_skeleton_service/app/demo_static/distill_demo.html`
- `prompt_skeleton_service/app/demo_static/distill_demo.js`
- `prompt_skeleton_service/tests/test_demo_shell.py`

## New API

`POST /api/v1/distill/question-pack/preview`

Input:

- multipart `files`

Output:

- per-file preview status,
- parser name,
- text excerpt,
- structured preview when available,
- warnings,
- combined text excerpt,
- supported format list.

## Parser Behavior

High-confidence structured/text formats:

- JSON
- JSONL
- CSV
- Markdown
- TXT
- DOCX
- XLSX

Best-effort formats that always require human review:

- PDF
- legacy DOC

The system does not pretend PDF/DOC extraction is perfect. These rows are marked `degraded` or `manual_required` with warnings.

## Frontend Behavior

Business mode now supports multi-file selection and posts files to the preview API. If the API is unavailable, the browser falls back only for text-like formats:

- JSON
- JSONL
- CSV
- TXT
- Markdown

Binary formats do not get fake browser parsing if the API is unavailable.

## Tests

Passed:

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`

Additional smoke:

- Service preview handled 9 sample files: JSON, JSONL, CSV, MD, TXT, DOCX, XLSX, PDF, DOC.
- PDF and DOC returned degraded best-effort extraction with warnings.

## Boundaries

This round did not:

- create a dataset automatically,
- write question cards,
- write material cards,
- write `card_specs`,
- modify runtime/prompt/validator/generation main-chain code,
- call the formal writeback executor.


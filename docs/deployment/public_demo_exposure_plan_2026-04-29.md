# Public Demo Exposure Plan - 2026-04-29

## A. Recommended Exposure

Expose only the prompt workbench service:

```yaml
ingress:
  - hostname: workbench.example.com
    service: http://127.0.0.1:8011
  - service: http_status:404
```

Do not expose `passage.example.com -> http://127.0.0.1:8001` in the first public demo. The prompt service calls `passage_service` over localhost, so external users can still experience material-backed generation without reaching the material backend directly.

## B. Cloudflare Access Policy

`workbench.example.com/*` must be protected by Cloudflare Access before using the `public_demo` profile.

Access policy requirements:

- Allow only specified email addresses or approved team email domains.
- Do not expose the profile without Access.
- Do not commit Cloudflare tunnel credentials, Access tokens, `.env.public-demo`, or the real distill key.
- Keep `PROMPT_SERVICE_SECURITY_ENABLED=false` for this profile only because browser APIs are protected by Cloudflare Access instead of in-app Bearer auth.

## C. Normal Tester Paths

Normal trusted testers can use:

- `/demo`
- `/demo/user-material`
- `/api/v1/questions/generate`
- `/api/v1/questions/generate-async`
- `/api/v1/questions/generate-async/tasks/{task_id}`
- `/api/v1/questions/{item_id}`
- `/api/v1/questions/{item_id}/review-actions`
- `/api/v1/questions/{item_id}/confirm`
- `/api/v1/questions/{item_id}/download`
- `/api/v1/review/items`
- `/api/v1/review/batches`
- `/api/v1/review/batches/{batch_id}`
- `/api/v1/review/items/{item_id}/history`
- `/api/v1/review/items/{item_id}/diff`
- `/api/v1/review/batches/{batch_id}/delivery`
- `/api/v1/review/batches/{batch_id}/delivery/export`

In `public_demo`, these routes use `PROMPT_QUESTION_DB_PATH=data/public_demo/question_workbench.demo.db`, so generated questions, edits, confirmations, downloads, async task state, runtime events, and usage events stay in the demo question DB.

## D. Deep Trusted Tester Paths

Deep trusted testers can use these only after both Cloudflare Access and a separately shared distill key:

- `/demo/distill`
- `/api/v1/distill/datasets`
- `/api/v1/distill/sessions`
- `/api/v1/distill/sessions/{session_id}/trials`
- `/api/v1/distill/runs/{run_id}/review`
- `/api/v1/distill/runs/{run_id}/patches`
- `/api/v1/distill/runs/{run_id}/promote`
- `/api/v1/distill/behavior/packets`

The distill key comes from `DISTILL_ACCESS_KEY`; `admin` and `change-me-distill-key` are not valid public demo defaults. Distill datasets, sessions, runs, reviews, patches, promotion rows, and behavior packets write to the demo question DB. Promotion evidence JSON is written under the demo DB parent directory, for example `data/public_demo/distill_promotions/`. This path does not run the formal writeback executor and does not write back to formal cards, prompt templates, or validator configs.

## E. Paths Not Recommended For External Direct Access

Do not directly expose `passage_service` or any independent passage hostname. In particular, do not expose:

- `/articles/ingest`
- `/articles/{article_id}/process`
- `/articles/{article_id}/review-export`
- `/materials/promote`
- `/materials/reprocess`
- `/materials/v2/precompute`
- `/materials/export/dify-pack`
- `/crawl/run`
- `/api/v1/diagnostics/runtime`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/api/v1/admin/reload-config`

For the prompt service, `PROMPT_DISABLE_FASTAPI_DOCS=true` disables `/docs`, `/redoc`, and `/openapi.json` in public demo. `PROMPT_PUBLIC_DEMO_MODE=true` blocks `/api/v1/admin/*` and `/api/v1/diagnostics/*`.

For passage service, `PASSAGE_DISABLE_FASTAPI_DOCS=true` disables FastAPI docs in public demo, but passage should still remain localhost-only and not receive a Cloudflare public hostname.

## F. User Experience Acceptance Chain

1. Visit `https://workbench.example.com`.
2. Pass Cloudflare Access.
3. Open `/demo`.
4. Generate questions.
5. Modify a generated question.
6. Confirm the question.
7. Download or export the question.
8. Open `/demo/user-material`.
9. Paste user material and generate a question.
10. For trusted users, open `/demo/distill`.
11. Enter the distill key.
12. Create a demo dataset or session.
13. Run a trial.
14. Review the run.
15. Add a patch.
16. Promote and inspect promotion evidence.

## G. Explicit Non-Goals

This public demo profile does not add:

- Full user accounts.
- Registration or login.
- JWT, app sessions, or a user database.
- Frontend `apiFetch` Bearer-token auth.
- A public `passage_service` hostname.
- Access to real development or production DBs.
- Formal writeback executor calls.
- Automatic writeback to formal question cards, prompts, validators, or runtime configuration.

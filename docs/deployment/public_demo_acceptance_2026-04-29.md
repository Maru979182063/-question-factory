# Public Demo Acceptance Report - 2026-04-29

## Summary

Result: passed for the public demo acceptance path.

The public demo profile was started from `.env.public-demo` on local loopback ports only:

- `passage_service`: `http://127.0.0.1:8001`
- `prompt_skeleton_service`: `http://127.0.0.1:8011`

The acceptance run used the OpenAI-compatible chat endpoint supplied locally in `.env.public-demo`. Secrets are intentionally redacted in this report.

## Startup Commands

Passage service:

```powershell
cd E:\agent_repo_src\passage_service
# Load .env.public-demo into the process environment first.
C:\Users\97918\AppData\Local\Programs\Python\Python313\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Prompt service:

```powershell
cd E:\agent_repo_src\prompt_skeleton_service
# Load .env.public-demo into the process environment first.
C:\Users\97918\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

## Environment Summary

- `GENERATION_LLM_BASE_URL=https://new.fastaicode.top/v1`
- `GENERATION_LLM_API_KEY=<redacted>`
- `MATERIAL_LLM_BASE_URL=https://new.fastaicode.top/v1`
- `MATERIAL_LLM_API_KEY=<redacted>`
- `PASSAGE_OPENAI_BASE_URL=https://new.fastaicode.top/v1`
- `PASSAGE_OPENAI_API_KEY=<redacted>`
- `PROMPT_RUNTIME_CONFIG_PATH=configs/question_runtime.public_demo.yaml`
- `PROMPT_QUESTION_DB_PATH=E:\agent_repo_src\data\public_demo\question_workbench.demo.db`
- `PROMPT_DATA_DIR=E:\agent_repo_src\data\public_demo`
- `PROMPT_PUBLIC_DEMO_MODE=true`
- `PROMPT_SERVICE_SECURITY_ENABLED=false`
- `PROMPT_DISABLE_FASTAPI_DOCS=true`
- `DISTILL_ACCESS_KEY=<redacted>`
- `DISTILL_COOKIE_SECURE=false` for local HTTP acceptance; set `true` behind HTTPS/Cloudflare.
- `PASSAGE_DATABASE_URL=sqlite:///./passage_service.demo.db`
- `PASSAGE_DISABLE_FASTAPI_DOCS=true`
- `PASSAGE_DISABLE_SCHEDULER=true`
- `PASSAGE_ALLOW_NON_PRIMARY_DATABASE=true`

## Runtime Paths

- Demo question DB: `E:\agent_repo_src\data\public_demo\question_workbench.demo.db`
- Demo distill promotion evidence: `E:\agent_repo_src\data\public_demo\distill_promotions`
- Passage demo DB: `E:\agent_repo_src\passage_service\passage_service.demo.db`
- Real question DB checked for no write: `E:\agent_repo_src\data\question_workbench.db`

## Acceptance Results

| Step | Result |
| --- | --- |
| Open `/demo` | 200 OK |
| Open `/demo/user-material` | 200 OK |
| Confirm `/docs` disabled | 404 OK |
| Generate one standard question through `/api/v1/questions/generate` | 200 OK; item `e85d6b22-950e-4131-a9b9-292625a38beb` |
| Modify generated item through `/review-actions` | 200 OK |
| Confirm generated item | 200 OK |
| Download generated item | 200 OK |
| Generate from user material through equivalent API | 200 OK |
| Access `/api/v1/distill/datasets` before distill key | 401 OK |
| Verify distill key | 200 OK |
| Access `/api/v1/distill/datasets` after key | 200 OK |
| Create distill session | 200 OK; session `5cbf12a0-6caf-4d84-addb-ed05230702e1` |
| Run distill trial | 200 OK; run `8d80617a-b5e6-4efb-b174-c7fdea35a909` |
| Review distill run | 200 OK |
| Add distill patch | 200 OK |
| Promote distill run | 200 OK |
| Confirm promotion evidence | Wrote `data\public_demo\distill_promotions\b297f384-e5d6-42db-b414-2d039e916216.json` |

Demo DB counters after the run:

- `question_items`: 3
- `question_review_actions`: 2
- `question_usage_events`: 1
- `distill_sessions`: 1
- `distill_runs`: 1
- `distill_run_reviews`: 1
- `distill_run_patches`: 1
- `distill_promotions`: 1

## Data Isolation Checks

The real question DB was checked immediately before and after the end-to-end run:

- Before: `mtime_ns=1777445150818045100`, `size=405504`
- After: `mtime_ns=1777445150818045100`, `size=405504`

Result: the public demo run did not write `E:\agent_repo_src\data\question_workbench.db`.

The prompt service wrote only the configured demo DB and demo distill promotion directory. The passage service used the local demo DB at `passage_service.demo.db`.

## Passage Exposure Check

The acceptance run used only local loopback service calls:

- `127.0.0.1:8011` for the public workbench entry.
- `127.0.0.1:8001` for internal passage service calls.

No passage public hostname is required. The recommended Cloudflare Tunnel exposure remains:

```yaml
ingress:
  - hostname: workbench.example.com
    service: http://127.0.0.1:8011
  - service: http_status:404
```

Do not expose `passage.example.com` for the first public demo.

## Not Tested

- Cloudflare Tunnel and Cloudflare Access were not started from this workstation. The local acceptance verifies the service behavior that Cloudflare should protect, but not Cloudflare policy enforcement itself.
- `DISTILL_COOKIE_SECURE=true` was not used in the local HTTP run because Secure cookies are not sent over plain HTTP. The profile supports it and should use `true` under HTTPS/Cloudflare.
- Full pytest suite was not run in this acceptance pass because the local Python environments previously reported `No module named pytest`. The replacement was a real service-level end-to-end acceptance run against both FastAPI apps.

## Public Exposure Decision

Current status: ready to connect to Cloudflare Tunnel + Cloudflare Access for controlled public trial, provided that:

- Cloudflare Access protects `workbench.example.com/*`.
- Only `workbench.example.com -> http://127.0.0.1:8011` is exposed.
- `.env.public-demo` remains local and uncommitted.
- Real secrets, tunnel credentials, and DB files are never committed.
- `DISTILL_COOKIE_SECURE=true` is used for the HTTPS public deployment.

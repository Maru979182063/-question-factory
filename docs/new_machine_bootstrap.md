# New Machine Bootstrap

## Goal

Bring up both local services on a new machine with the repo contents that already live on `codex/dev-local`.

## Branch

```powershell
git clone https://github.com/Maru979182063/-.git
cd agent
git checkout codex/dev-local
```

## One-Time Bootstrap

Run the dependency bootstrap from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-demo.ps1
```

Or with the wrapper:

```cmd
scripts\bootstrap-demo.cmd
```

What it does:

- creates the repo-root `.venv` for `prompt_skeleton_service`
- creates `passage_service\.venv`
- upgrades `pip`, `setuptools`, and `wheel`
- installs both services in editable mode

Optional:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-demo.ps1 -CopyPassageEnvExample
```

That also creates `passage_service\.env` from `passage_service\.env.example` when missing.

## Required Env Vars

Set these in your shell, user profile, or CI secret store before generation/material workflows:

```powershell
$env:GENERATION_LLM_API_KEY="your_key"
$env:MATERIAL_LLM_API_KEY="your_key"
```

Optional overrides:

```powershell
$env:GENERATION_LLM_BASE_URL="https://api.openai.com/v1"
$env:MATERIAL_LLM_BASE_URL="https://api.openai.com/v1"
$env:PASSAGE_OPENAI_API_KEY="your_key"
```

## Start Both Services

The existing launcher already starts both services:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload
```

Common wrappers:

```cmd
scripts\start-demo-dev.cmd
scripts\start-demo-mvp.cmd
scripts\start-demo-uat.cmd
```

## Local URLs

- Prompt/demo UI: `http://127.0.0.1:8111/demo` for `dev`
- User-material UI: `http://127.0.0.1:8111/demo/user-material` for `dev`
- Passage/material docs: `http://127.0.0.1:8101/docs` for `dev`

Other profile defaults are defined in `scripts/start-demo.ps1`.

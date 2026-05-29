# APGL Agent Handoff Guide

This file is the first-stop guide for any AI agent or developer continuing APGL.
Read it before making changes.

## Required Reading Order

Before editing code, read these files in order:

1. `README.md`
2. `docs/product.md`
3. `docs/architecture.md`
4. `docs/progress.md`
5. `docs/todo.md`
6. `docs/development.md`

Use `docs/development.md` as the full development standard.

## Hard Rules

- Use the project-local Python environment only: `.\.venv\Scripts\python`.
- Do not install Python packages globally.
- Do not commit `.env`, `.venv/`, SQLite databases, `node_modules/`, `frontend/dist/`, caches, or real API keys.
- Do not run tests against `backend/data/app.db`; tests must use an isolated test database.
- Do not call an LLM directly from frontend pages or API routers. Use `backend/app/services/ai.py`.
- Do not silently fall back to mock AI when `APGL_MOCK_AI=false`; surface visible errors.
- Do not make unrelated visual rewrites or landing pages. This is a learning workspace.
- Do not commit or push unless the user explicitly asks.

## Standard Workflow

1. Check current state with `git status --short`.
2. Read the relevant code and docs before changing behavior.
3. Keep backend concerns in routers, services, models, schemas, and config as described in `docs/development.md`.
4. Keep frontend API types in `frontend/src/api/types.ts` and API calls in `frontend/src/api/client.ts`.
5. Update `docs/progress.md` and `docs/todo.md` before finishing meaningful behavior, architecture, configuration, test, or user-visible changes. Pure formatting or typo-only edits do not need progress/todo churn.
6. Run verification unless there is a clear blocker:
   - `.\.venv\Scripts\python -m pytest backend`
   - `cd frontend && npm run build`
7. In the final handoff, report changed areas, verification results, and anything not completed.

## Local Commands

Backend setup and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir backend
```

Environment setup:

Create `.env` from `.env.example` only if `.env` does not already exist. Never
overwrite a user's local `.env`.

Use local `.env` for real LLM credentials. For offline development, set
`APGL_MOCK_AI=true`; for provider testing, configure `LLM_API_KEY`,
`LLM_BASE_URL`, `LLM_MODEL_FAST`, and `LLM_MODEL_SMART`.

Frontend setup and run:

```powershell
cd frontend
npm install
npm run dev
```

Verification:

```powershell
.\.venv\Scripts\python -m pytest backend
cd frontend
npm run build
```

## Security Notes

- Real LLM credentials belong only in local `.env`.
- Example files must use placeholders.
- If a secret appears in a tracked file, remove it immediately and tell the user.
- If a test, script, or tool may delete data, confirm it targets a test database before running it.

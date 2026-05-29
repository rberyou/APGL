# Development Standard

This document defines how APGL should be developed and maintained by AI agents
and human developers.

## Project Intent

APGL is an AI guided learning workspace. It turns a skill goal or uploaded
material into lessons, quizzes, mistakes, and reviews. Keep the product focused
on learning workflows, not marketing pages or decorative demos.

## Required Context Before Work

Before modifying code, read:

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/progress.md`
- `docs/todo.md`
- This file

Then inspect the relevant implementation files. Do not guess where behavior
lives when the repository can answer it.

## Environment Rules

- Python dependencies must be installed only into the repository-local `.venv`.
- Use `.\.venv\Scripts\python -m pip ...`, not global `pip`.
- Do not commit `.env`, `.venv/`, `node_modules/`, SQLite databases, caches, or build output.
- The main local app database is `backend/data/app.db`; tests must not delete or rewrite it.
- Use `.env.example` only for placeholders and safe defaults.

## Backend Standards

Backend code lives under `backend/app`.

- API routes belong in `backend/app/routers/`.
- Business logic belongs in `backend/app/services/`.
- Database models belong in `backend/app/models.py`.
- Request and response schemas belong in `backend/app/schemas.py`.
- Runtime configuration belongs in `backend/app/config.py`.
- Database setup and sessions belong in `backend/app/database.py`.

Rules:

- Keep routers thin. They should validate ownership, call services, and return schemas.
- Keep LLM, material parsing, and job processing out of routers.
- Use SQLModel for database tables and queries.
- Always enforce user ownership before returning or mutating user-owned data.
- Background generation failures must be recorded on `Job.error` and visible to users.
- Do not introduce migrations or PostgreSQL unless the task explicitly calls for it.

## Frontend Standards

Frontend code lives under `frontend/src`.

- API types belong in `frontend/src/api/types.ts`.
- API calls belong in `frontend/src/api/client.ts`.
- Pages belong in `frontend/src/pages/`.
- Shared layout and reusable components belong in `frontend/src/components/`.
- Global styling belongs in `frontend/src/styles.css`.

Rules:

- Use React Router for page navigation.
- Use TanStack Query for server state, polling, and cache invalidation.
- Keep the UI task-focused and workspace-like.
- Do not add landing pages, marketing hero sections, or unrelated visual rewrites.
- Show visible error states for failed jobs, failed API calls, and validation errors.
- Keep runtime-configurable frontend values synchronized through the existing `GET /api/config` endpoint when possible. Add new public config fields only for values that must be controlled by backend configuration.

## LLM Standards

All LLM access must go through `backend/app/services/ai.py`.

Supported modes:

- `APGL_MOCK_AI=true`: deterministic local mock behavior.
- `APGL_MOCK_AI=false`: real OpenAI-compatible Chat Completions through `LLM_*`.

Required configuration for third-party providers:

```env
LLM_API_KEY=your_provider_api_key
LLM_BASE_URL=https://provider.example.com/v1
LLM_MODEL_FAST=provider-fast-model
LLM_MODEL_SMART=provider-smart-model
LLM_API_MODE=chat_completions
APGL_MOCK_AI=false
```

Rules:

- Do not put real keys in tracked files.
- Do not call LLM providers from frontend code.
- Do not silently use mock output when real LLM mode is configured.
- LLM output parsing must tolerate common provider quirks such as markdown fences,
  `<think>` blocks, and explanatory text before JSON.
- If LLM output is unusable, fail the job with a clear, user-visible error.
LLM-related tests must cover:

- `APGL_MOCK_AI=true` deterministic local mock behavior.
- `APGL_MOCK_AI=false` with missing key/base URL fails with a clear error.
- A mocked Chat Completions response can be parsed into lessons, quizzes, and feedback.

## Testing Standards

Default verification:

```powershell
.\.venv\Scripts\python -m pytest backend
cd frontend
npm run build
```

Rules:

- Backend tests must use an isolated test database, never `backend/data/app.db`.
- Existing pytest coverage sets `DATABASE_URL` to a test database before importing the app. New tests or scripts must explicitly point `DATABASE_URL` at a test or temporary database before importing `backend/app/database.py`, `backend/app/main.py`, or modules that create sessions.
- Add or update tests for behavior changes, especially auth, jobs, LLM parsing, lessons, quizzes, mistakes, and reviews.
- Frontend changes must at least pass `npm run build`.
- If verification cannot be run, document the reason in the final handoff and in `docs/progress.md` if relevant.

## Documentation Standards

Update docs as part of every meaningful behavior, architecture, configuration,
test, or user-visible change. Pure formatting or typo-only edits do not need
progress/todo churn unless they change instructions or project state.

- Product behavior changes: update `docs/product.md` when the user-facing concept changes.
- Architecture or data flow changes: update `docs/architecture.md`.
- Technical or product decisions: update `docs/decisions.md`.
- Completed work and verification: update `docs/progress.md`.
- Remaining work, risks, and follow-ups: update `docs/todo.md`.
- Development process changes: update this file and `AGENTS.md` if needed.

`docs/progress.md` must say what changed, what was verified, and the current state.
`docs/todo.md` must preserve actionable next steps by priority.

## Git Standards

- Start by checking `git status --short`.
- Never revert user changes unless explicitly asked.
- Keep commits focused when the user asks for a commit.
- Do not commit or push unless the user explicitly asks.
- Preserve remote history; do not force push.
- Before a requested commit, run verification or document why it was not run.

## Recovery After Interruption

When resuming work:

1. Read `AGENTS.md`.
2. Read `docs/progress.md` and `docs/todo.md`.
3. Check `git status --short`.
4. Inspect files related to the active task.
5. Run tests or targeted checks before continuing if the current state is unclear.
6. Continue from the documented next step instead of restarting from scratch.

## Definition of Done

A change is done only when:

- The requested behavior is implemented or the blocker is clearly documented.
- Relevant backend and frontend checks pass, or skipped checks are explained.
- `docs/progress.md` and `docs/todo.md` are updated when the change is meaningful behavior, architecture, configuration, test, or user-visible work. Pure formatting or typo-only edits do not require progress/todo updates.
- No secrets or local artifacts are staged.
- The final handoff names what changed, what was verified, and what remains.

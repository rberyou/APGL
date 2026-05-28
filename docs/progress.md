# Progress

Last updated: 2026-05-29

## Completed

- Cloned remote repository and preserved existing `main` history.
- Added backend FastAPI app with auth, projects, materials, jobs, lessons, quiz, reviews, and mistakes APIs.
- Added SQLModel data model for users, sessions, learning projects, source materials, chunks, knowledge points, lessons, quizzes, answers, mistakes, reviews, and jobs.
- Added OpenAI service wrapper with deterministic mock fallback.
- Added Vite React frontend with Dashboard, Create Project, Job Status, Project Detail, Lesson, Review, and Mistake Book pages.
- Added project documentation and setup instructions.
- Added backend pytest coverage for the core learning loop.
- Created local `.venv` and installed backend dependencies without using global Python packages.
- Installed frontend dependencies under `frontend/node_modules`.
- Verified backend tests: `12 passed`.
- Verified frontend production build with `npm run build`.
- Started local backend and frontend dev servers.
- Completed HTTP smoke test for register, skill project generation, lesson retrieval, quiz answer, mistake creation, and review queue.
- Clarified project lesson cards as AI-generated learning path units and made mock fallback lesson titles more project-specific.
- Added explicit 8 MB material upload limit copy, frontend file-size validation, and backend 413 error detail.
- Implemented OpenAI-compatible Chat Completions through `LLM_*` environment variables, with explicit mock mode and visible LLM configuration errors.
- Added public `/api/config` so the frontend displays the backend-configured upload limit.
- Verified MiniMax-compatible `.env` configuration and improved JSON extraction for providers that emit `<think>` blocks before JSON.
- Added recovery path for projects with no generated lessons and isolated backend tests from the local development database.
- Added latest generation job error display on project pages and made plan storage tolerant of provider responses that use string items.

## Current State

Implementation is verified locally, including third-party OpenAI-compatible Chat Completions support.

## Next Step

Configure `LLM_API_KEY`, `LLM_BASE_URL`, and provider model names in `.env`, then create a new learning project to verify the chosen provider.

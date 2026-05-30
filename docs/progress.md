# Progress

Last updated: 2026-05-30

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
- Added `AGENTS.md` as the first-stop AI handoff guide for future agents and developers.
- Added `docs/development.md` as the complete development standard for backend, frontend, LLM, testing, docs, Git, and recovery workflows.
- Re-verified after the development-standard update: backend tests `12 passed`; frontend `npm run build` passed.
- Refined the development standard after review: clarified when progress/todo updates are required, added `.env` setup guidance, made test database isolation explicit, and converted LLM test expectations into an actionable checklist.
- Refined the handoff standard again to warn agents not to overwrite existing `.env`, to use the existing `GET /api/config` endpoint for runtime-configurable frontend values, and to align Definition of Done with the progress/todo update exception.
- Implemented the first APGL V2 tutor-platform slice: tutor profiles, project trackers, learning gaps, knowledge edges, lesson steps, study sessions, tutor messages, source citations, learning events, and material diagnostics.
- Added SQLite FTS indexing for source chunks and tutor retrieval so material projects can search across all parsed chunks instead of only using the first few excerpts.
- Added V2 APIs for project tracker, knowledge map, material status, lesson steps, tutor sessions, tutor messages, and session ending.
- Upgraded the frontend Dashboard, Project Detail, Lesson, Review, and Weak Point views toward a multi-learning-space tutor workspace.
- Expanded backend tests to cover material diagnostics, FTS-backed tutor sessions, knowledge map/tracker APIs, unreadable PDF errors, and existing learning flows.
- Improved third-party LLM robustness after repeated generation failures: invalid JSON responses now get one automatic JSON repair attempt, nested provider payloads are unwrapped, and backend coverage includes the repair path.
- Fixed a MiniMax-specific JSON parsing failure where an outer ```json fence was truncated by inner Markdown code fences inside JSON string content. The parser now scans the full response for a complete JSON object before trying fenced snippets, and plan storage accepts provider-shaped `title`/`description` knowledge points and single-object quiz payloads.
- Captured the next V2 learning-flow optimization plan in `docs/v2-learning-flow-optimization-plan.md`, covering staged generation, job timeline UX, retry/resume, explicit lesson-to-knowledge mapping, dynamic tutor assessment, and removal of manual lesson completion from the primary flow.

## Current State

Implementation is verified locally, including third-party OpenAI-compatible Chat Completions support and the first V2 tutor-platform slice. The repository includes explicit AI handoff and development rules for interrupted or future AI-assisted work. The next optimization direction is planned but not implemented yet.

## Next Step

Implement `docs/v2-learning-flow-optimization-plan.md`: staged project generation, persisted job stages/artifacts, retry/resume, explicit knowledge-point lesson mapping, and dynamic tutor assessment that updates mastery without manual lesson completion.

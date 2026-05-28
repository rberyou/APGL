# Progress

Last updated: 2026-05-28

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
- Verified backend tests: `3 passed`.
- Verified frontend production build with `npm run build`.
- Started local backend and frontend dev servers.
- Completed HTTP smoke test for register, skill project generation, lesson retrieval, quiz answer, mistake creation, and review queue.
- Clarified project lesson cards as AI-generated learning path units and made mock fallback lesson titles more project-specific.

## Current State

Implementation is verified locally and ready for commit and push. Backend is available at `http://127.0.0.1:8000`; frontend is available at `http://127.0.0.1:5173`.

## Next Step

Commit the MVP implementation and push to `origin main`.

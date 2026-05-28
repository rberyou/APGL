# Architecture

## Overview

The app is a monorepo with a FastAPI backend and Vite React frontend.

```mermaid
flowchart LR
  Browser["React Web App"] --> API["FastAPI /api"]
  API --> DB["SQLite"]
  API --> Jobs["FastAPI BackgroundTasks + Job table"]
  Jobs --> Materials["PDF/Markdown/Text parser"]
  Jobs --> AI["OpenAI-compatible Chat Completions or explicit mock AI"]
  AI --> DB
```

## Backend

- `app.main` creates the FastAPI app, CORS, startup database initialization, and routers.
- `app.models` contains SQLModel tables.
- `app.services.materials` extracts and chunks uploaded material.
- `app.services.ai` wraps OpenAI-compatible Chat Completions and deterministic explicit mock output.
- `app.services.jobs` processes skill and material generation jobs.
- Auth uses email/password, Argon2 password hashing, and httpOnly Cookie sessions.

## Frontend

- React Router owns page navigation.
- TanStack Query owns server state and polling.
- Vite proxies `/api` requests to `http://127.0.0.1:8000`.
- Pages are task-oriented: Dashboard, Create Project, Job Status, Project Detail, Lesson, Review, Mistake Book.

## Data Flow

- Skill project: `POST /api/projects` creates a project and background job; job generates lessons and quiz items.
- Material project: create project, upload file, parse text, chunk text, generate lessons and quiz items.
- Quiz answer: backend grades the answer, records it, and creates mistake/review records when incorrect.

## AI Strategy

- Prefer `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_FAST`, and `LLM_MODEL_SMART` for third-party compatible providers.
- `LLM_API_MODE=chat_completions` is the supported mode.
- `OPENAI_API_KEY`, `OPENAI_MODEL_FAST`, and `OPENAI_MODEL_SMART` remain legacy fallback settings.
- `APGL_MOCK_AI=true` enables deterministic local fallback content. If mock is false and LLM config/calls fail, jobs fail with visible errors.

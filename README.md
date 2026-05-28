# APGL - AI Powered Guided Learning

APGL is a local-first MVP for AI guided learning. It turns a skill goal or uploaded material into a small learning project with lessons, quiz checks, mistakes, and review tasks.

## Stack

- Backend: Python 3.12, FastAPI, SQLModel, SQLite
- Frontend: Vite, React, TypeScript, Tailwind CSS
- AI: OpenAI-compatible Chat Completions with explicit mock mode

## Local Setup

Create the local Python virtual environment from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Create local environment values:

```powershell
Copy-Item .env.example .env
```

Set `LLM_*` values in `.env` for real AI calls, or set `APGL_MOCK_AI=true` for deterministic local mock output.

## LLM Configuration

For third-party providers that expose an OpenAI-compatible Chat Completions API, configure:

```env
LLM_API_KEY=your_provider_api_key
LLM_BASE_URL=https://your-provider.example.com/v1
LLM_MODEL_FAST=your-fast-model
LLM_MODEL_SMART=your-smart-model
LLM_API_MODE=chat_completions
APGL_MOCK_AI=false
```

Notes:

- `LLM_BASE_URL` should usually include `/v1`; follow your provider's docs if they specify a different base path.
- Model names must be the names from your provider, not OpenAI model names unless you are using OpenAI.
- ChatGPT Plus does not include API access or an API key.
- `OPENAI_API_KEY`, `OPENAI_MODEL_FAST`, and `OPENAI_MODEL_SMART` remain supported as legacy official OpenAI fallback settings.
- If `APGL_MOCK_AI=false` and the LLM config is missing or invalid, generation jobs fail with a visible error instead of silently using mock content.

## Run

Backend:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir backend
```

Frontend:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`.

## Test

Backend:

```powershell
.\.venv\Scripts\python -m pytest backend
```

Frontend:

```powershell
cd frontend
npm run build
```

## Development Notes

- Do not install Python packages globally. Always use `.\.venv\Scripts\python -m pip`.
- Local database files live under `backend/data/` and are ignored by Git.
- Update `docs/progress.md` and `docs/todo.md` before pausing work.
- Material uploads accept PDF, Markdown, and plain text files up to the configured `MAX_UPLOAD_BYTES` limit.

# APGL - AI Powered Guided Learning

APGL is a local-first MVP for AI guided learning. It turns a skill goal or uploaded material into a small learning project with lessons, quiz checks, mistakes, and review tasks.

## Stack

- Backend: Python 3.12, FastAPI, SQLModel, SQLite
- Frontend: Vite, React, TypeScript, Tailwind CSS
- AI: OpenAI Responses API with mock fallback when no API key is configured

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

Set `OPENAI_API_KEY` in `.env` for real AI calls. Leave it empty for deterministic mock AI.

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


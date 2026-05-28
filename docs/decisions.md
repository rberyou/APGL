# Decisions

## 2026-05-28

- Use `FastAPI + React` for the MVP because it cleanly separates API work from a rich learning workspace UI.
- Use SQLite first to keep local setup simple and avoid extra services.
- Use project-local `.venv` for Python dependencies; never install backend dependencies globally.
- Use email/password and httpOnly Cookie sessions for local account support.
- Use an internal `Job` table and FastAPI background tasks instead of Redis for MVP simplicity.
- Support only PDF, Markdown, and text material ingestion in v1.
- Keep deterministic mock AI fallback so development and tests work without an API key.
- Preserve remote Git history from `git@github.com:rberyou/APGL.git`; no force push.


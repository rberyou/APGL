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

## 2026-05-29

- Upgrade APGL toward a multi-learning-space AI tutor platform rather than a static lesson generator.
- Use SQLite FTS for V2 source retrieval so large PDF/text material can be searched without adding embeddings or a vector database yet.
- Keep video, web links, OCR, and vector retrieval out of V2 to focus on reliable PDF/Markdown/text learning.
- Store tutor sessions, messages, citations, trackers, and learning gaps in the database instead of requiring users to manage Markdown session files.

## 2026-05-30

- Split project generation into persisted stages instead of one large LLM call so each stage is smaller, visible, retryable, and resumable.
- Use knowledge-point mastery as the canonical progress signal. Lessons are learning containers, not manually completed tasks.
- Replace fixed pre-generated lesson check questions with dynamic tutor assessment that asks questions at learning time and updates mastery, weak points, and review tasks.
- Require explicit lesson-to-knowledge-point mapping so every knowledge point has a visible learning action.
- For V2 material projects, require the learning file during project creation rather than keeping create and upload as separate primary user actions.
- Continue lesson assessment until the lesson mastery threshold is reached, while preserving unfinished assessments so learners can leave and resume later.
- Send low-score assessment answers to review, not only answers marked strictly incorrect.
- Automatically mark projects as `passed` when mastery and open-gap criteria are satisfied.
- Use one learner-facing generation recovery action, `Continue generation`, with explanatory copy instead of separate retry/resume buttons.
- Keep FastAPI BackgroundTasks for this local-first slice, but persist every
  generation stage and artifact so a later retry/resume can continue after local
  service interruption.
- Store uploaded source files in `backend/data/uploads/` and keep parsed text in
  `SourceMaterial` so material jobs can be resumed without requiring another
  browser upload.
- Keep the legacy lesson-complete and static quiz endpoints temporarily for
  compatibility, while the primary lesson UX uses dynamic assessment.

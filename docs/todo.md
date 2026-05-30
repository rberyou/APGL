# Todo

## P0

- Implement the staged generation pipeline described in `docs/v2-learning-flow-optimization-plan.md`.
- Add persisted job stages and generation artifacts so generation progress is visible, retryable, and resumable.
- Replace the simple job loading UI with a stage timeline that shows current work, material diagnostics, skipped stages, and stage-specific errors.
- Add explicit lesson-to-knowledge-point mapping so every knowledge point has a learning action.
- Replace the lesson page's fixed `Check understanding` block and primary manual `Mark complete` flow with dynamic tutor assessment that updates mastery and weak points.

## P1

- Keep `AGENTS.md` and `docs/development.md` synchronized with future workflow, verification, and security rule changes.
- Re-run a real provider smoke test whenever `LLM_*` settings change.
- Manually verify the V2 tutor workflow with a real provider and a large PDF such as the Vulkan specification after staged generation is implemented.
- Improve tutor prompt quality so generated explanations are deeper, source-grounded, and less generic.
- Add API pagination for projects and mistake records.
- Improve material chunk source references for PDF page ranges and Markdown headings.
- Add explicit project pass criteria UI based on lesson completion, mastery, and assessment results.
- Add rate limits or basic abuse protection around auth and AI generation.
- Add frontend LLM settings page, provider presets, and a provider connectivity test button.
- Add richer session controls such as resume last session, learn weak points, and quiz me modes.

## P2

- Add migrations with Alembic before production use.
- Add PostgreSQL configuration for hosted deployments.
- Add streaming tutor chat inside lessons.
- Add OCR support for scanned PDFs.
- Add web page ingestion.
- Add video transcript ingestion.
- Add spaced repetition scheduling beyond same-day and next-day review.

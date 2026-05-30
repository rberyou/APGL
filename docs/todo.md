# Todo

## P0

- Harden retry/resume idempotency around partially written stages with more
  targeted tests for interrupted material parsing, stale jobs, and provider JSON
  failures.

## P1

- Keep `AGENTS.md` and `docs/development.md` synchronized with future workflow, verification, and security rule changes.
- Re-run a real provider smoke test whenever `LLM_*` settings change.
- Manually verify the V2 tutor workflow with a real provider and a large PDF such as the Vulkan specification.
- Improve tutor prompt quality so generated explanations are deeper, source-grounded, and less generic.
- Add API pagination for projects and mistake records.
- Improve material chunk source references for PDF page ranges and Markdown headings.
- Add richer project pass criteria UI based on mastery, open gaps, and assessment results.
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

# Product Design

## Goal

APGL helps individual self-learners manage multiple learning spaces with an AI
tutor. A learning space can start from a skill goal or learning material, then
grow into a source library, knowledge map, tutor sessions, progress tracker,
mistake history, and review plan.

## Audience

The current product targets personal self-learners using the product locally or
in a single-user hosted setup. It does not include cohorts, teachers, enterprise
reporting, community features, or mobile apps.

## Core Flow

1. User registers or logs in.
2. User creates a learning space from either a skill goal or uploaded material.
3. Backend creates a generation job.
4. AI generates knowledge points, lessons, quiz items, and a tracker baseline.
5. For material projects, APGL parses all readable text into source chunks and
   indexes them for retrieval.
6. User studies inside a tutor workspace: structured lesson steps, AI tutor chat,
   checks, citations, and review prompts.
7. Each tutor session can be ended with a session note that updates the project
   tracker, mastered topics, learning gaps, and next plan.
8. Incorrect answers become mistake records and review tasks.
9. Dashboard shows learning spaces, due reviews, weak points, and next tutor moves.

## Supported Inputs

- Skill goal: title, goal, current level, session time.
- Material: PDF, Markdown, or plain text.

## Current Exclusions

- Video subtitles
- Web page ingestion
- OCR for scanned PDFs
- Third-party login
- Multi-user teams or classrooms
- Mobile app or WeChat mini program
- Payments, pricing, or admin console

## V2 Experience

- Project detail shows tracker, source diagnostics, knowledge map, sessions, and
  the tutor learning path.
- Lesson pages are tutor workspaces, not static content pages.
- Tutor replies use project goals, session history, tracker state, weak points,
  and retrieved source chunks.
- Material projects surface page/text/chunk diagnostics so large PDFs are
  inspectable and empty/scanned PDFs fail clearly.

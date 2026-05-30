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
   Material projects require the file in the same creation action.
3. Backend creates a staged generation job with a visible timeline.
4. AI generates a project brief, knowledge map, lesson plan, and first lesson
   content in separate persisted stages.
5. For material projects, APGL persists the uploaded file, parses readable text
   into source chunks, and
   indexes them for retrieval.
6. User studies inside a tutor workspace: structured lesson steps, AI tutor chat,
   dynamic assessment, citations, and review prompts.
7. Each tutor session can be ended with a session note that updates the project
   tracker, mastered topics, learning gaps, and next plan.
8. Dynamic assessment asks one tutor question at a time, evaluates answers,
   updates knowledge-point mastery, and sends incorrect or low-score answers to
   mistake/review workflows.
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
- Progress is derived from knowledge-point mastery, not manual lesson-complete
  clicks.
- Fixed pre-generated lesson questions are no longer the primary flow. Learners
  use a resumable dynamic tutor assessment to reach lesson mastery.
- Tutor replies use project goals, session history, tracker state, weak points,
  and retrieved source chunks.
- Material projects surface page/text/chunk diagnostics so large PDFs are
  inspectable and empty/scanned PDFs fail clearly.

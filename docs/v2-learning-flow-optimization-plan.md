# APGL V2 Learning Flow Optimization Plan

This document is an implementation-ready handoff plan. A new AI agent should be
able to start from this file without needing the previous conversation.

## Implementation Prompt

Implement the APGL V2 learning-flow optimization on branch
`feature/v2-ai-tutor-platform`.

Before editing, read:

1. `AGENTS.md`
2. `README.md`
3. `docs/product.md`
4. `docs/architecture.md`
5. `docs/development.md`
6. `docs/progress.md`
7. `docs/todo.md`
8. This file

Do not commit or push unless the user explicitly asks. Use the project-local
Python environment only: `.\.venv\Scripts\python`.

## Summary

APGL should move from a static lesson generator to a multi-topic AI tutor
platform. Project creation has two entry modes, but they must share the same
core generation pipeline:

- Skill goal: user provides a goal and optional current level. There is no
  uploaded source material. The first version should use the configured LLM's
  model knowledge. Official/authoritative web search is a future enhancement,
  not part of this implementation.
- Learning material: user provides a goal plus PDF/Markdown/text material. The
  system parses the material, chunks it, indexes it with SQLite FTS, and uses
  retrieved chunks as source context.

Both modes must generate a project brief, knowledge map, and lesson plan in
separate stages. Lesson content and quizzes should be generated or conducted
closer to the learning moment, not all in one large initial LLM request.

The lesson page should keep `Tutor explanation` and `AI Tutor`, but remove
pre-generated fixed check questions and remove the manual `Mark complete`
workflow. The learner should use a quiz/tutor assessment entry point where the
AI asks questions about the lesson's knowledge points, evaluates answers,
updates mastery, records weak points, and updates project progress.

## Core Product Decisions

- A learning project is a learning space. It owns a source library, knowledge
  map, lesson plan, tutor sessions, mastery tracker, weak points, and review
  tasks.
- Knowledge points are the source of truth for progress.
- Lessons are guided learning containers that cover one or more knowledge
  points.
- Project progress is derived from knowledge-point mastery, not from a user
  clicking a lesson-complete button.
- Quiz questions should be dynamic tutor interactions, not static questions
  generated during project creation.
- Static `QuizItem` records may remain for compatibility and review history, but
  the main lesson experience should use dynamic assessment.
- Generation must be staged, persisted, retryable, and resumable after a local
  service interruption.

## Non-Goals For This Slice

- Do not add video ingestion.
- Do not add web page ingestion.
- Do not add OCR for scanned PDFs.
- Do not add vector databases or embeddings.
- Do not add frontend LLM key management.
- Do not redesign the app into a marketing or landing page.
- Do not copy CFP-Study's file-based workflow. APGL remains a web app with
  database-backed learning spaces.

## Current Pain Points To Fix

- Initial generation asks the LLM to do too much in one request, which causes
  shallow lessons, incomplete mappings, and invalid JSON failures.
- The current `Job` model only exposes coarse status and error text. Users
  cannot see which stage failed.
- The job page uses a simple loading state, which feels stalled for large PDFs
  or slow providers.
- Knowledge points and lessons are not explicitly linked, so some knowledge
  points have no obvious learning path.
- Lesson pages still contain fixed `Check understanding` prompts and manual
  `Mark complete`, which does not match the AI tutor goal.

## Target Generation Pipeline

### Stage 0: Create Learning Space

Input:

- `title`
- `goal`
- `source_type`
- `current_level`
- `time_budget_minutes`
- optional uploaded material

Output:

- `LearningProject`
- `TutorProfile`
- `ProjectTracker`
- `Job`
- stage timeline initialized

### Stage 1: Material Intake

Run only for `source_type=material`.

Tasks:

- Parse PDF/Markdown/txt.
- Store `SourceMaterial` diagnostics:
  - filename
  - content type
  - page count when available
  - text page count when available
  - character count
  - chunk count
  - status
- Chunk readable text into `SourceChunk`.
- Index chunks in SQLite FTS.
- If no readable text exists, fail this stage with a clear OCR message.

For `source_type=skill`, mark this stage as skipped with a visible message:

`No source material was uploaded. APGL will start from the learning goal and the configured LLM's model knowledge.`

### Stage 2: Project Brief

Make a small LLM call that only produces the project brief.

Expected JSON:

```json
{
  "learning_goal": "string",
  "assumed_current_level": "beginner|intermediate|advanced|unknown",
  "scope": ["string"],
  "out_of_scope": ["string"],
  "recommended_strategy": "string",
  "success_criteria": ["string"]
}
```

Persist as a generation artifact and use it as input for later stages.

### Stage 3: Knowledge Map

Make a separate LLM call that only produces knowledge points and relationships.

Expected JSON:

```json
{
  "knowledge_points": [
    {
      "client_key": "stable-human-readable-key",
      "name": "string",
      "explanation": "string",
      "difficulty": "intro|core|advanced",
      "estimated_weight": 0.1,
      "source_locator": "optional page/chunk label"
    }
  ],
  "edges": [
    {
      "source_client_key": "prerequisite-key",
      "target_client_key": "dependent-key",
      "relation_type": "prerequisite|related_to"
    }
  ]
}
```

Rules:

- Do not generate lesson content in this stage.
- Material projects should use retrieved source chunks as context.
- Skill projects should use the goal and project brief.
- Persist all knowledge points before lesson planning.

### Stage 4: Lesson Plan

Make a separate LLM call that receives the saved knowledge points and returns
lesson containers.

Expected JSON:

```json
{
  "lessons": [
    {
      "title": "string",
      "summary": "string",
      "order_index": 1,
      "covered_knowledge_client_keys": ["key-1", "key-2"],
      "learning_objectives": ["string"],
      "suggested_activity": "string"
    }
  ]
}
```

Rules:

- Every knowledge point must be covered by at least one lesson.
- A lesson can cover multiple knowledge points.
- If the LLM leaves a knowledge point uncovered, the backend must either:
  - assign it to the nearest lesson using a deterministic fallback, or
  - fail the lesson-plan stage with a clear error and allow retry.
- Store explicit lesson-to-knowledge-point mappings.

### Stage 5: First Lesson Preparation

Generate detailed lesson content only for the first lesson, or for the first
unstarted lesson.

Expected JSON:

```json
{
  "tutor_explanation": "short structured explanation",
  "examples": ["string"],
  "practice_suggestions": ["string"],
  "source_citations": [
    {
      "source_chunk_id": 123,
      "label": "Page 12",
      "excerpt": "short excerpt"
    }
  ]
}
```

Rules:

- Do not generate fixed quiz questions here.
- Keep the explanation useful but not too long.
- Material projects should cite source chunks when possible.
- Other lesson content can be generated lazily when the learner opens the
  lesson.

### Stage 6: Complete Generation

Mark the job completed only after:

- project brief exists
- knowledge map exists
- lesson plan exists
- every knowledge point is mapped to at least one lesson
- first lesson has tutor explanation content
- project tracker has a next action

## Job Timeline UX

Replace the plain loading state with a visible staged timeline.

Recommended labels:

1. Understand learning goal
2. Parse learning material
3. Build source index
4. Create project brief
5. Build knowledge map
6. Plan tutor learning path
7. Prepare first lesson
8. Ready

For skill projects, show material stages as skipped rather than hiding them if
that is clearer in the UI.

Each stage should show:

- status: pending, running, completed, skipped, failed
- short message
- optional details
- retryability when failed

Examples:

```text
[done] Understand learning goal
[skipped] Parse learning material: no material uploaded
[done] Create project brief: beginner Git workflow, collaboration, internals
[running] Build knowledge map: identified 12 knowledge points
[pending] Plan tutor learning path
[pending] Prepare first lesson
```

For material projects:

```text
[done] Parse learning material: VulkanSpec.pdf, 243 pages, 238 text pages
[done] Build source index: 912 chunks indexed
[running] Build knowledge map: extracting concepts from source chunks
```

## Retry And Resume Requirements

Generation must not be an all-or-nothing black box.

### Persisted Stages

Add persistent stage records so the frontend can render real progress and the
backend can resume from the last completed stage.

Suggested model:

```python
class JobStage(SQLModel, table=True):
    id: int | None
    job_id: int
    project_id: int
    stage_key: str
    label: str
    status: str  # pending, running, completed, skipped, failed
    order_index: int
    message: str
    details_json: str
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
```

Add a lightweight current-state mirror to `Job` for list/detail responses:

- `stage_key`
- `stage_label`
- `progress_percent`
- `message`
- `error_stage`
- `retry_of_job_id`

### Persisted Artifacts

Persist outputs of each successful generation stage.

Suggested model:

```python
class GenerationArtifact(SQLModel, table=True):
    id: int | None
    project_id: int
    job_id: int
    material_id: int | None
    artifact_type: str  # project_brief, knowledge_map, lesson_plan, lesson_content
    input_hash: str
    content_json: str
    status: str  # active, superseded, failed
    created_at: datetime
    updated_at: datetime
```

Use artifacts to:

- avoid redoing completed stages after a retry
- debug what was generated
- resume from the last valid stage after interruption
- make prompt/schema changes easier to test

### Retry Behavior

Add:

- `POST /api/jobs/{id}/retry`

Behavior:

- Only failed or interrupted jobs can be retried.
- Retry creates a new job with `retry_of_job_id` pointing to the previous job.
- Completed artifacts from previous stages are reused when their `input_hash`
  still matches.
- The failed stage and later dependent stages are rerun.
- The UI should show which stage is being retried.

### Resume Behavior

FastAPI `BackgroundTasks` do not survive process restarts. Handle this
explicitly rather than pretending background work always continues.

Add:

- `POST /api/jobs/{id}/resume`

Behavior:

- If a job is `processing` but has no recent stage update, the frontend can show
  `Generation may have been interrupted` and offer Resume.
- Resume creates a new job or reuses the existing job only if safe. Prefer a new
  job for clearer history.
- Resume starts from the first incomplete stage using persisted artifacts.
- Do not delete existing project data unless the stage explicitly regenerates
  that data.

### Stage Failure Rules

- Material parse failure is not LLM retryable. Show a clear message:
  `No readable text was extracted. Scanned PDFs require OCR, which is not supported yet.`
- LLM JSON failure is retryable. Keep one automatic repair attempt, then fail
  the stage with a clear provider/model message.
- Lesson-plan coverage failure is retryable.
- First lesson content failure is retryable and should not delete the knowledge
  map or lesson plan.
- A failed stage must set both `Job.error` and the relevant `JobStage.error`.

## Knowledge Point To Lesson Mapping

Add an explicit mapping table.

Suggested model:

```python
class LessonKnowledgePoint(SQLModel, table=True):
    id: int | None
    lesson_id: int
    knowledge_point_id: int
    project_id: int
    coverage_role: str  # primary, supporting
    order_index: int
```

Rules:

- Every saved `KnowledgePoint` must have at least one mapping.
- Project detail should show the mapped lesson action for every knowledge point.
- Lesson detail should show the knowledge points covered by that lesson.
- Project progress should be computed from knowledge-point mastery.

## Lesson Page Target UX

Remove from the main lesson flow:

- fixed `Check understanding` question block
- manual `Mark complete` primary action

Keep:

- lesson title/summary
- covered knowledge points
- `Tutor explanation`
- source citations
- `AI Tutor` chat

Add:

- `Start quiz` or `Quiz me` button
- current lesson mastery summary
- weak points discovered in this lesson
- next suggested action

The learner should not have to decide whether a lesson is complete. APGL should
infer progress from tutor assessment and knowledge-point mastery.

## Dynamic Tutor Assessment

Implement quiz as a tutor-driven assessment loop.

Suggested API:

- `POST /api/lessons/{lesson_id}/assessment/start`
- `GET /api/assessments/{assessment_id}`
- `POST /api/assessments/{assessment_id}/answer`
- `POST /api/assessments/{assessment_id}/end`

Suggested models:

```python
class AssessmentSession(SQLModel, table=True):
    id: int | None
    project_id: int
    lesson_id: int
    user_id: int
    status: str  # active, completed
    mode: str  # quiz, weak_point_review
    summary: str | None
    started_at: datetime
    ended_at: datetime | None

class AssessmentTurn(SQLModel, table=True):
    id: int | None
    assessment_id: int
    project_id: int
    lesson_id: int
    knowledge_point_id: int | None
    question: str
    user_answer: str | None
    feedback: str | None
    score: float | None
    mastery_delta: float | None
    citations_json: str
    created_at: datetime
```

Assessment flow:

1. Start assessment for a lesson.
2. Pick the lowest-mastery covered knowledge point, or rotate through uncovered
   points.
3. Generate one question through `backend/app/services/ai.py`.
4. User answers.
5. AI evaluates the answer with a small JSON response:

```json
{
  "is_correct": true,
  "score": 0.82,
  "feedback": "string",
  "missing_concepts": ["string"],
  "mastery_delta": 0.08,
  "next_action": "ask_follow_up|explain_again|move_on"
}
```

6. Update:
   - `KnowledgePoint.mastery`
   - `LearningGap`
   - `MistakeRecord` and `ReviewTask` when weak or incorrect
   - `LearningEvent`
   - `ProjectTracker.mastery`
7. Ask a follow-up question or finish with a summary.

## Mastery And Progress Rules

Use knowledge point mastery as the canonical progress signal.

Initial suggested thresholds:

- `0.0 - 0.29`: not started / weak
- `0.30 - 0.59`: learning
- `0.60 - 0.79`: usable
- `0.80 - 1.00`: mastered

Lesson mastery:

- average mastery of mapped knowledge points
- show as guidance, not a manually toggled status

Project mastery:

- weighted average of all knowledge points
- use `estimated_weight` when available
- fallback to equal weights

Pass criteria:

- A project can be considered passed when project mastery is at least `0.80`
  and no high-severity learning gaps remain open.
- This pass UI can be simple in this slice; do not build a full certificate or
  exam mode.

## Backend Implementation Scope

Update or add:

- `backend/app/models.py`
  - `JobStage`
  - `GenerationArtifact`
  - `LessonKnowledgePoint`
  - `AssessmentSession`
  - `AssessmentTurn`
  - additive `Job` fields for current stage/progress
- `backend/app/database.py`
  - additive SQLite schema updates
  - no destructive migration against local data
- `backend/app/schemas.py`
  - job timeline responses
  - generation artifact diagnostics if needed
  - lesson knowledge mapping reads
  - assessment request/response types
- `backend/app/services/jobs.py`
  - staged pipeline orchestration
  - persisted stage updates
  - retry/resume entry points
  - no all-at-once generation
- `backend/app/services/ai.py`
  - `generate_project_brief`
  - `generate_knowledge_map`
  - `generate_lesson_plan`
  - `generate_lesson_content`
  - `generate_assessment_question`
  - `evaluate_assessment_answer`
  - keep all LLM calls centralized here
- `backend/app/services/learning.py`
  - knowledge-to-lesson mapping helpers
  - mastery calculation
  - tracker updates
  - learning gap updates
- `backend/app/routers/jobs.py`
  - job detail includes stages
  - retry endpoint
  - resume endpoint
- `backend/app/routers/lessons.py`
  - lesson detail includes covered knowledge points and mastery
  - avoid relying on manual completion
- new or existing router for assessments

## Frontend Implementation Scope

Update or add:

- `frontend/src/api/types.ts`
  - stage timeline types
  - assessment types
  - lesson knowledge point mapping types
- `frontend/src/api/client.ts`
  - job retry/resume
  - assessment APIs
- `frontend/src/pages/JobStatusPage.tsx`
  - replace simple loading panel with job timeline
  - show material diagnostics
  - show retry/resume actions
  - show stage-specific errors
- `frontend/src/pages/ProjectDetailPage.tsx`
  - knowledge map items show mapped lesson action
  - highlight unmapped items only as an error/retry state
  - show generation retry when latest job failed
- `frontend/src/pages/LessonPage.tsx`
  - remove fixed check question block
  - remove primary manual completion action
  - show covered knowledge points and mastery
  - add dynamic assessment entry point
  - preserve AI Tutor chat
- review/mistake pages
  - keep compatibility with existing mistakes/reviews
  - show weak points grouped by project and knowledge point where possible

## Test Plan

Backend tests:

- Skill project generation runs through staged pipeline with mock AI.
- Material project generation runs through material parse, chunking, FTS, brief,
  knowledge map, lesson plan, and first lesson preparation.
- Empty/scanned PDF fails at material parse with a clear OCR message.
- Job detail returns ordered stages and current progress.
- Failed LLM JSON at knowledge map stage marks only that stage failed.
- `POST /api/jobs/{id}/retry` reuses completed artifacts and reruns failed and
  dependent stages.
- Interrupted/stale processing job can be resumed from the last completed stage.
- Every knowledge point is mapped to at least one lesson.
- Lesson detail returns covered knowledge points and lesson mastery.
- Starting assessment chooses a mapped knowledge point.
- Answer evaluation updates mastery, learning gaps, review/mistake records, and
  tracker progress.
- `APGL_MOCK_AI=true` path works.
- Mocked OpenAI-compatible Chat Completions path works.

Frontend verification:

- `npm run build` passes.
- Job status page shows timeline for skill project.
- Job status page shows timeline and material diagnostics for material project.
- Job failure shows stage-specific error and retry action.
- Resume action appears for stale interrupted processing jobs.
- Lesson page has no fixed `Check understanding` block.
- Lesson page does not depend on manual `Mark complete`.
- Dynamic assessment can be started, answered, and reflected in mastery UI.

Manual smoke test:

1. Start backend and frontend.
2. Register or log in.
3. Create a skill project for Git.
4. Watch job timeline complete.
5. Verify project knowledge map has lesson actions for every point.
6. Open lesson 1.
7. Start assessment and answer at least one tutor question.
8. Confirm mastery/weak points/tracker update.
9. Create a material project with a Markdown or small PDF file.
10. Confirm material diagnostics and source-grounded lesson generation.
11. Force an LLM failure or invalid model config and confirm stage-specific
    failure plus retry UX.

Verification commands:

```powershell
.\.venv\Scripts\python -m pytest backend
cd frontend
npm run build
```

## Documentation Updates Required During Implementation

Update these before finishing the implementation:

- `docs/product.md`
  - state that progress is knowledge-point mastery, not manual lesson complete
  - describe dynamic tutor assessment
- `docs/architecture.md`
  - add staged generation, job stages, artifacts, retry/resume, assessment loop
- `docs/progress.md`
  - record completed implementation and verification results
- `docs/todo.md`
  - remove completed P0 items and add remaining follow-ups
- `docs/decisions.md`
  - record staged generation and dynamic assessment decisions

## Definition Of Done

This slice is done when:

- Project generation is staged and persisted.
- Users can see a meaningful job timeline.
- Failed generation tells users which stage failed.
- Failed/restarted generation can retry or resume without starting from zero.
- Every knowledge point has a mapped lesson action.
- Lesson pages no longer show fixed pre-generated questions as the primary flow.
- Lesson pages no longer require manual completion.
- Dynamic tutor assessment updates mastery and weak points.
- Backend tests pass.
- Frontend build passes.
- Required docs are updated.

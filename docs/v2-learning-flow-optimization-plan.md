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
- Learning material: user provides a goal plus PDF/Markdown/text material in
  the same project creation flow. The system parses the material, chunks it,
  indexes it with SQLite FTS, and uses retrieved chunks as source context.

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
- Material projects require a file at creation time. The old two-step
  create-then-upload flow should not remain the primary UX.
- Dynamic assessments continue until the lesson mastery threshold is reached,
  while allowing the learner to leave and resume later.
- Incorrect answers and low-score answers both enter review, because low
  understanding means the knowledge point is not reliably mastered.
- Projects are automatically marked `passed` when pass criteria are satisfied.
- The learner-facing generation recovery action is named `Continue generation`;
  UI copy explains whether APGL is continuing after an interruption or retrying
  a failed stage.

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

## Architect Review Updates

This section captures design fixes found during a senior architecture review.
These are implementation requirements, not optional ideas.

- Material uploads must be resumable. The upload API should persist the
  original uploaded file under an ignored local data path such as
  `backend/data/uploads/`, create a `SourceMaterial` row with diagnostics still
  pending, and then start a generation job. Do not rely on in-memory upload
  bytes or synchronous router parsing for the staged pipeline, because retry and
  resume cannot reconstruct the input after a process restart.
- Routers must stay thin. Material parsing, chunking, FTS indexing, LLM calls,
  stage transitions, and retry/resume decisions belong in services, primarily
  `backend/app/services/jobs.py`, `materials.py`, `retrieval.py`, `ai.py`, and
  `learning.py`.
- New LLM calls need schema-specific parsing. Do not extend the current generic
  JSON parser only by adding more accepted top-level keys. Instead, make the AI
  helper accept expected keys or a validation callback per call, so project
  brief, knowledge map, lesson plan, lesson content, tutor reply, and answer
  evaluation can each validate their own schema.
- Retry and resume must be idempotent. A stage that reruns must either reuse an
  active artifact with a matching input hash or replace only the records owned
  by that stage and its dependent stages. It must never duplicate lessons,
  mappings, chunks, citations, or stages.
- Keep only one active generation job per project. A new retry/resume job may be
  created only after the previous active job is failed or explicitly marked
  interrupted.
- For this slice, retry/resume applies only to projects whose initial
  generation did not complete. Do not support regenerating a completed project
  after the learner has assessment turns, tutor sessions, answers, mistakes, or
  review tasks; that is a later versioned-regeneration feature.
- `QuizItem` can stay for existing quiz/review compatibility, but dynamic
  assessment must be the primary lesson flow. If a dynamic assessment answer
  needs a `MistakeRecord` or `ReviewTask`, create a compatibility `QuizItem`
  snapshot for that assessment turn so existing non-null quiz foreign keys do
  not require destructive SQLite migrations in this slice.
- Remove manual completion from the primary frontend flow, but keep the existing
  lesson-complete API temporarily for backward compatibility until old tests and
  data paths are retired.

## Resolved Product Decisions

These decisions are locked for this implementation slice.

1. Material project creation is a combined flow: the learner provides the goal
   and file before APGL creates the material learning space and generation job.
2. Lesson assessment continues until the lesson mastery threshold is reached.
   If the learner leaves midway, the unfinished assessment remains resumable and
   the next visit continues from the latest unanswered or next needed question.
3. Low-score answers enter review in addition to clearly incorrect answers.
   The default low-score threshold for this slice is `score < 0.70`; scores
   from `0.70` to below mastery can still create or update learning gaps.
4. When project mastery is at least `0.80` and no high-severity learning gaps
   remain open, APGL automatically marks the project as `passed`.
5. The UI uses one learner-facing action, `Continue generation`, for retry and
   resume. Supporting text explains the reason, such as `Generation was
   interrupted while building the knowledge map` or `The provider returned
   invalid JSON while preparing the first lesson`.

## Target Generation Pipeline

### Stage 0: Create Learning Space

Input:

- `title`
- `goal`
- `source_type`
- `current_level`
- `time_budget_minutes`
- uploaded material when `source_type=material`

Output:

- `LearningProject`
- `TutorProfile`
- `ProjectTracker`
- `SourceMaterial` for material projects
- `Job`
- stage timeline initialized

For material projects, the uploaded file must be persisted before the job
starts. The persisted path should be stored on `SourceMaterial` and must point
inside an ignored local data directory. Store a checksum for input hashing.
Do not create a material project without a file in the primary create flow.
The existing upload endpoint may remain for compatibility or future material
replacement, but the V2 creation UX should not depend on it.

### Stage 1: Material Intake

Run only for `source_type=material`.

Tasks:

- Parse PDF/Markdown/txt.
- Store `SourceMaterial` diagnostics:
  - filename
  - content type
  - storage path
  - file checksum
  - page count when available
  - text page count when available
  - character count
  - chunk count
  - status
  - clear error message when parsing fails
- Chunk readable text into `SourceChunk`.
- Index chunks in SQLite FTS.
- If no readable text exists, fail this stage with a clear OCR message.

Implementation notes:

- The upload router should not parse the file synchronously except for basic
  validation such as size and supported extension/content type. Parsing belongs
  to this stage so the timeline can show progress and resume can rerun it.
- If this stage reruns, delete and rebuild only chunks, FTS entries, and
  citations owned by the current material/project before reinserting them.
- Split the user-visible timeline into `Parse learning material` and
  `Build source index`, even if both are implemented inside the same stage
  function initially. This keeps the UI honest for large files.

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
- Persist stable fields on `KnowledgePoint`: `client_key`, `difficulty`,
  `estimated_weight`, and optional `source_locator`. These fields are required
  for deterministic lesson mapping, weighted progress, and artifact reuse.
- If `estimated_weight` is missing or invalid, assign equal normalized weights
  during persistence.
- If a returned edge references an unknown `client_key`, skip that edge and add
  a stage warning in `JobStage.details_json`; do not fail the whole stage unless
  most edges are invalid.

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
- If the LLM leaves a knowledge point uncovered, assign it to the nearest lesson
  using a deterministic fallback first. A simple fallback is to attach uncovered
  points to the lesson whose title/summary/objectives has the highest token
  overlap with the point name/explanation, falling back to the final lesson.
  Record this in `JobStage.details_json`. Fail the stage only if no lessons were
  returned or no mappings can be formed.
- Store explicit lesson-to-knowledge-point mappings.
- If this stage reruns, replace lesson units, lesson steps, source citations,
  static quiz compatibility rows created by generation, and
  `LessonKnowledgePoint` rows created by prior incomplete generation attempts.
  Do not touch learner-owned answers, sessions, assessments, mistakes, or
  reviews because retry/regeneration is not allowed after learning begins in
  this slice.

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
- Other lesson content can be generated lazily through an explicit
  `POST /api/lessons/{lesson_id}/prepare` endpoint. Do not make `GET` lesson
  endpoints mutate state or block on LLM calls. The endpoint creates or returns
  a `lesson_content_generation` job for that lesson. The lesson page should show
  a `Prepare lesson` action and then use the same job timeline pattern while the
  later lesson's tutor explanation is generated.

### Stage 6: Complete Generation

Mark the job completed only after:

- project brief exists
- knowledge map exists
- lesson plan exists
- every knowledge point is mapped to at least one lesson
- first lesson has tutor explanation content
- project tracker has a next action
- `LearningProject.progress_percent` mirrors knowledge-point mastery rather
  than lesson completion state

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
- last update time when the job is still running

Generation recovery UX:

- Show one primary action: `Continue generation`.
- If the latest job is stale/interrupted, explain that APGL will continue from
  the last saved stage.
- If the latest job failed, explain which stage failed and that APGL will reuse
  valid prior artifacts where possible.
- Do not show separate learner-facing Retry and Resume buttons in this slice.

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
    is_retryable: bool
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
- `resumed_from_job_id`

Allowed job statuses:

- `pending`
- `processing`
- `completed`
- `failed`
- `interrupted`

Use `interrupted` when the backend has determined that an old processing job no
longer has a live background task and a new resume job has taken over.

### Persisted Artifacts

Persist outputs of each successful generation stage.

Suggested model:

```python
class GenerationArtifact(SQLModel, table=True):
    id: int | None
    project_id: int
    job_id: int
    material_id: int | None
    stage_key: str
    artifact_type: str  # project_brief, knowledge_map, lesson_plan, lesson_content
    input_hash: str
    schema_version: str
    prompt_version: str
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

Input hash requirements:

- Include project title, goal, source type, current level, time budget, material
  checksum when material exists, prompt version, schema version, and IDs or
  hashes of upstream active artifacts.
- Do not include volatile fields such as timestamps, job IDs, or stage messages.
- If a prompt/schema version changes, old artifacts remain available for
  debugging but should not be reused for new generation.

### Retry Behavior

Add:

- `POST /api/jobs/{id}/retry`

Behavior:

- Only `failed` or `interrupted` jobs can be retried.
- Retry creates a new job with `retry_of_job_id` pointing to the previous job.
- Completed artifacts from previous stages are reused when their `input_hash`
  still matches.
- The failed stage and later dependent stages are rerun.
- The UI should show which stage is being retried.
- Retry must refuse if the project already has learner-owned progress after a
  completed generation, such as assessment turns, tutor sessions, answers,
  mistakes, or reviews.

### Resume Behavior

FastAPI `BackgroundTasks` do not survive process restarts. Handle this
explicitly rather than pretending background work always continues.

Add:

- `POST /api/jobs/{id}/resume`

Behavior:

- If a job is `processing` but has no recent stage update, the frontend can show
  `Generation may have been interrupted` and offer Resume.
- Treat a processing job as stale when its active stage has not updated for at
  least 10 minutes. This threshold is intentionally conservative for slow local
  LLM providers.
- Resume marks the old processing job as `interrupted`, creates a new job with
  `resumed_from_job_id` pointing to the old job, and continues from the first
  incomplete stage.
- Resume starts from the first incomplete stage using persisted artifacts.
- Do not delete existing project data unless the stage explicitly regenerates
  that data.
- Resume must not run concurrently with an existing pending/processing job for
  the same project.

### Stage Failure Rules

- Material parse failure is not LLM retryable. Show a clear message:
  `No readable text was extracted. Scanned PDFs require OCR, which is not supported yet.`
- LLM JSON failure is retryable. Keep one automatic repair attempt, then fail
  the stage with a clear provider/model message.
- Lesson-plan coverage failure is retryable.
- First lesson content failure is retryable and should not delete the knowledge
  map or lesson plan.
- A failed stage must set both `Job.error` and the relevant `JobStage.error`.
- If stage failure leaves partial rows from that stage, mark the stage failed and
  clean or supersede those partial rows before retrying. Do not leave ambiguous
  active rows.

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
    created_at: datetime
```

Rules:

- Every saved `KnowledgePoint` must have at least one mapping.
- Project detail should show the mapped lesson action for every knowledge point.
- Lesson detail should show the knowledge points covered by that lesson.
- Project progress should be computed from knowledge-point mastery.
- Prevent duplicate mappings for the same `(lesson_id, knowledge_point_id)` in
  service logic even if SQLite compatibility constraints are kept simple.
- Prefer exactly one `primary` mapping per knowledge point; additional mappings
  should use `supporting`.

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

Resume semantics:

- Starting an assessment for a lesson must return the existing unfinished
  assessment for that user and lesson when one exists, instead of creating a
  duplicate.
- Browser close, navigation away, or local interruption does not complete the
  assessment. The assessment remains `active` and can be continued later.
- If the active assessment has an unanswered turn, the UI should show that turn
  first. Otherwise it should ask the backend for the next question needed to
  reach the lesson mastery threshold.
- `end` is only for intentionally finishing the assessment early or when the
  mastery threshold has been reached. Ending early records a summary but does
  not mark the lesson mastered unless mastery rules say so.

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
    updated_at: datetime

class AssessmentTurn(SQLModel, table=True):
    id: int | None
    assessment_id: int
    project_id: int
    lesson_id: int
    knowledge_point_id: int | None
    quiz_item_id: int | None
    status: str  # asked, answered, skipped
    question: str
    user_answer: str | None
    feedback: str | None
    score: float | None
    mastery_delta: float | None
    missing_concepts_json: str
    next_action: str | None
    citations_json: str
    created_at: datetime
    answered_at: datetime | None
```

Assessment flow:

1. Start assessment for a lesson.
2. Pick the lowest-mastery covered knowledge point, or rotate through uncovered
   points.
3. Generate one question through `backend/app/services/ai.py`.
4. Persist the question as an `AssessmentTurn(status="asked")`.
5. User answers the latest unanswered turn.
6. AI evaluates the answer with a small JSON response:

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

7. Clamp `score` and `mastery_delta` to safe ranges in backend code. Do not
   trust the model to decide arbitrary progress changes.
8. Update:
   - `KnowledgePoint.mastery`
   - `LearningGap`
   - compatibility `QuizItem`, `MistakeRecord`, and `ReviewTask` when weak or
     incorrect
   - `LearningEvent`
   - `ProjectTracker.mastery`
9. Ask a follow-up question or finish with a summary.

Compatibility with existing review/mistake records:

- Existing `MistakeRecord` and `ReviewTask` require a `quiz_item_id`.
- For dynamic assessment, create a `QuizItem` snapshot for the turn when a
  review/mistake is needed. The snapshot should use the assessment question as
  `prompt`, store a short rubric or expected idea in `answer`, store the model
  feedback in `explanation`, and point to the assessed knowledge point.
- Set `AssessmentTurn.quiz_item_id` to that snapshot for traceability.
- This keeps old review/mistake APIs working without destructive SQLite schema
  changes.

Assessment rules:

- Continue assessment until lesson mastery is at least `0.80`, unless the
  learner intentionally ends early.
- After every 3 answered turns in one sitting, show a lightweight continue/pause
  affordance in the UI so learners can stop without losing state.
- Create a review task when `is_correct=false` or `score < 0.70`.
- Create or update a medium-severity learning gap when `0.70 <= score < 0.80`.
- Increase mastery by at most `0.12` per strong answer and decrease by at most
  `0.05` per weak answer.

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
- update `LearningProject.progress_percent` from project mastery after quiz,
  assessment, and session-summary updates

Pass criteria:

- A project can be considered passed when project mastery is at least `0.80`
  and no high-severity learning gaps remain open.
- When pass criteria are met, set `LearningProject.status` to `passed` and
  record `passed_at`.
- This pass UI can be simple in this slice; do not build a full certificate or
  exam mode.

## Backend Implementation Scope

Update or add:

- `backend/app/models.py`
  - additive `LearningProject` field: `passed_at`
  - additive `SourceMaterial` fields: `storage_path`, `file_checksum`, and
    `error`
  - additive `KnowledgePoint` fields: `client_key`, `difficulty`,
    `estimated_weight`, and `source_locator`
  - `JobStage`
  - `GenerationArtifact`
  - `LessonKnowledgePoint`
  - `AssessmentSession`
  - `AssessmentTurn`
  - additive `Job` fields for current stage/progress, retry, and resume
- `backend/app/database.py`
  - additive SQLite schema updates for every new model and new column
  - no destructive migration against local data
  - no attempt to make existing non-null foreign keys nullable in this slice
- `backend/app/schemas.py`
  - material project creation schema that accepts metadata plus a required file
  - job timeline responses
  - generation artifact diagnostics if needed
  - lesson knowledge mapping reads
  - assessment request/response types
- `backend/app/services/jobs.py`
  - staged pipeline orchestration
  - persisted stage updates
  - retry/resume entry points
  - no all-at-once generation
  - file-backed material intake stage
  - idempotent stage cleanup/reuse helpers
- `backend/app/services/ai.py`
  - `generate_project_brief`
  - `generate_knowledge_map`
  - `generate_lesson_plan`
  - `generate_lesson_content`
  - `generate_assessment_question`
  - `evaluate_assessment_answer`
  - schema-specific JSON response validation for each function
  - keep all LLM calls centralized here
- `backend/app/services/learning.py`
  - knowledge-to-lesson mapping helpers
  - mastery calculation
  - automatic project pass detection and `passed_at` updates
  - tracker updates
  - learning gap updates
  - assessment mastery update helpers
  - compatibility quiz snapshot helper for mistake/review creation
- `backend/app/routers/jobs.py`
  - job detail includes stages
  - retry endpoint
  - resume endpoint
- `backend/app/routers/lessons.py`
  - lesson detail includes covered knowledge points and mastery
  - avoid relying on manual completion
  - `POST /api/lessons/{lesson_id}/prepare` for later lesson content jobs
- new or existing router for assessments

Schema compatibility notes:

- Keep old `QuizItem`, quiz answer, mistake, and review endpoints passing while
  the frontend moves away from fixed lesson quizzes.
- New tests may still exercise the old quiz path until it is intentionally
  deprecated.
- Because APGL currently uses additive SQLite compatibility instead of Alembic,
  prefer adding columns/tables and service-level invariants over destructive
  table rebuilds.

## Frontend Implementation Scope

Update or add:

- `frontend/src/api/types.ts`
  - stage timeline types
  - assessment types
  - lesson knowledge point mapping types
- `frontend/src/api/client.ts`
  - combined material project creation with required file upload
  - job retry/resume
  - assessment APIs
  - lesson preparation API
- `frontend/src/pages/CreateProjectPage.tsx`
  - require a file before submitting a material project
  - create material projects and upload the file in one user action
- `frontend/src/pages/JobStatusPage.tsx`
  - replace simple loading panel with job timeline
  - show material diagnostics
  - show a single `Continue generation` action for retry/resume recovery
  - explain why continuation is needed and which stage will continue
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
  - show lesson preparation state for lessons whose tutor explanation has not
    been generated yet
  - preserve AI Tutor chat
- review/mistake pages
  - keep compatibility with existing mistakes/reviews
  - show weak points grouped by project and knowledge point where possible

## Test Plan

Backend tests:

- Skill project generation runs through staged pipeline with mock AI.
- Material project creation requires a file and persists metadata, local file
  path, and checksum in one create flow.
- Material project generation runs through material parse, chunking, FTS, brief,
  knowledge map, lesson plan, and first lesson preparation from the persisted
  file.
- Empty/scanned PDF fails at material parse with a clear OCR message.
- Job detail returns ordered stages and current progress.
- Failed LLM JSON at knowledge map stage marks only that stage failed.
- Project brief and first lesson content LLM responses parse through
  schema-specific validation.
- `POST /api/jobs/{id}/retry` reuses completed artifacts and reruns failed and
  dependent stages.
- Interrupted/stale processing job can be resumed from the last completed stage.
- Retry/resume refuses when another job is pending/processing for the same
  project.
- Retry/resume refuses completed projects that already have learner-owned
  progress.
- Every knowledge point is mapped to at least one lesson.
- Lesson detail returns covered knowledge points and lesson mastery.
- Later lesson content can be prepared without mutating `GET` lesson endpoints.
- Starting assessment chooses a mapped knowledge point.
- Starting assessment again for an unfinished lesson assessment resumes the
  existing assessment instead of creating a duplicate.
- An assessment can be interrupted and later continued from the unanswered turn
  or next needed question.
- Answer evaluation updates mastery, learning gaps, review/mistake records, and
  tracker progress.
- Dynamic assessment creates a compatibility `QuizItem` snapshot when it needs
  to create a mistake/review task.
- Low-score answers below `0.70` create review tasks even when not strictly
  incorrect.
- Project status changes to `passed` and `passed_at` is set when project mastery
  reaches `0.80` with no high-severity gaps.
- `APGL_MOCK_AI=true` path works.
- Mocked OpenAI-compatible Chat Completions path works.

Frontend verification:

- `npm run build` passes.
- Job status page shows timeline for skill project.
- Job status page shows timeline and material diagnostics for material project.
- Material project creation requires file selection before submit.
- Job failure or stale interruption shows stage-specific context and a
  `Continue generation` action.
- Lesson page has no fixed `Check understanding` block.
- Lesson page does not depend on manual `Mark complete`.
- Dynamic assessment can be started, answered, interrupted, resumed, and
  reflected in mastery UI.
- Later lessons with unprepared content show a clear preparation state.

Manual smoke test:

1. Start backend and frontend.
2. Register or log in.
3. Create a skill project for Git.
4. Watch job timeline complete.
5. Verify project knowledge map has lesson actions for every point.
6. Open lesson 1.
7. Start assessment and answer at least one tutor question.
8. Confirm mastery/weak points/tracker update.
9. Create a material project with a Markdown or small PDF file in the project
   creation form.
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

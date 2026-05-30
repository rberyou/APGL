from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)


class UserSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class LearningProject(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    title: str
    goal: str
    source_type: str = Field(index=True)
    current_level: str | None = None
    time_budget_minutes: int | None = None
    status: str = Field(default="active", index=True)
    progress_percent: int = 0
    passed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TutorProfile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, unique=True, foreign_key="learningproject.id")
    teaching_style: str = "socratic"
    response_rules: str = (
        "Ask what the learner already understands, explain in short chunks, "
        "check understanding, and cite source material when available."
    )
    require_citations: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectTracker(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, unique=True, foreign_key="learningproject.id")
    mastery: float = 0.0
    mastered_topics_json: str = "[]"
    learning_gaps_json: str = "[]"
    next_plan: str = "Start the first tutor session."
    last_session_id: int | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class SourceMaterial(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    filename: str
    content_type: str
    raw_text: str
    storage_path: str | None = None
    file_checksum: str | None = None
    error: str | None = None
    status: str = Field(default="uploaded", index=True)
    page_count: int = 0
    text_page_count: int = 0
    character_count: int = 0
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)


class SourceChunk(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    material_id: int = Field(index=True, foreign_key="sourcematerial.id")
    position: int
    title: str
    content: str
    locator: str | None = None


class KnowledgePoint(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    client_key: str | None = Field(default=None, index=True)
    name: str
    explanation: str
    difficulty: str = "core"
    estimated_weight: float = 1.0
    source_locator: str | None = None
    mastery: float = 0.0
    source_chunk_id: int | None = Field(default=None, foreign_key="sourcechunk.id")


class KnowledgeEdge(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    source_id: int = Field(index=True, foreign_key="knowledgepoint.id")
    target_id: int = Field(index=True, foreign_key="knowledgepoint.id")
    relation_type: str = Field(default="related_to", index=True)


class LessonUnit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    title: str
    summary: str
    content: str
    order_index: int = Field(index=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class LessonKnowledgePoint(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True, foreign_key="lessonunit.id")
    knowledge_point_id: int = Field(index=True, foreign_key="knowledgepoint.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    coverage_role: str = "primary"
    order_index: int = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class LessonStep(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True, foreign_key="lessonunit.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    step_type: str = Field(default="explain", index=True)
    title: str
    body: str
    order_index: int = Field(index=True)


class QuizItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lesson_id: int = Field(index=True, foreign_key="lessonunit.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    knowledge_point_id: int | None = Field(default=None, foreign_key="knowledgepoint.id")
    question_type: str = "short_answer"
    prompt: str
    options_json: str | None = None
    answer: str
    explanation: str


class UserAnswer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    quiz_item_id: int = Field(index=True, foreign_key="quizitem.id")
    user_id: int = Field(index=True, foreign_key="user.id")
    answer: str
    is_correct: bool
    feedback: str
    created_at: datetime = Field(default_factory=utc_now)


class MistakeRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    quiz_item_id: int = Field(index=True, foreign_key="quizitem.id")
    user_id: int = Field(index=True, foreign_key="user.id")
    knowledge_point_id: int | None = Field(default=None, foreign_key="knowledgepoint.id")
    user_answer: str
    reason: str
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ReviewTask(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    quiz_item_id: int = Field(index=True, foreign_key="quizitem.id")
    mistake_id: int | None = Field(default=None, foreign_key="mistakerecord.id")
    due_at: datetime = Field(index=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class LearningGap(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    knowledge_point_id: int | None = Field(default=None, foreign_key="knowledgepoint.id")
    title: str
    severity: str = Field(default="medium", index=True)
    status: str = Field(default="open", index=True)
    evidence: str = ""
    updated_at: datetime = Field(default_factory=utc_now)


class StudySession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    user_id: int = Field(index=True, foreign_key="user.id")
    lesson_id: int | None = Field(default=None, index=True, foreign_key="lessonunit.id")
    status: str = Field(default="active", index=True)
    focus: str = ""
    summary: str | None = None
    next_plan: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None


class TutorMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="studysession.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    user_id: int = Field(index=True, foreign_key="user.id")
    role: str = Field(index=True)
    content: str
    citations_json: str = "[]"
    created_at: datetime = Field(default_factory=utc_now)


class SourceCitation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    source_chunk_id: int = Field(index=True, foreign_key="sourcechunk.id")
    lesson_id: int | None = Field(default=None, index=True, foreign_key="lessonunit.id")
    lesson_step_id: int | None = Field(default=None, index=True, foreign_key="lessonstep.id")
    tutor_message_id: int | None = Field(default=None, index=True, foreign_key="tutormessage.id")
    label: str
    excerpt: str = ""


class LearningEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    user_id: int = Field(index=True, foreign_key="user.id")
    event_type: str = Field(index=True)
    knowledge_point_id: int | None = Field(default=None, foreign_key="knowledgepoint.id")
    lesson_id: int | None = Field(default=None, foreign_key="lessonunit.id")
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=utc_now)


class AssessmentSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    lesson_id: int = Field(index=True, foreign_key="lessonunit.id")
    user_id: int = Field(index=True, foreign_key="user.id")
    status: str = Field(default="active", index=True)
    mode: str = "quiz"
    summary: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class AssessmentTurn(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    assessment_id: int = Field(index=True, foreign_key="assessmentsession.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    lesson_id: int = Field(index=True, foreign_key="lessonunit.id")
    knowledge_point_id: int | None = Field(default=None, foreign_key="knowledgepoint.id")
    quiz_item_id: int | None = Field(default=None, foreign_key="quizitem.id")
    status: str = Field(default="asked", index=True)
    question: str
    user_answer: str | None = None
    feedback: str | None = None
    score: float | None = None
    mastery_delta: float | None = None
    missing_concepts_json: str = "[]"
    next_action: str | None = None
    citations_json: str = "[]"
    created_at: datetime = Field(default_factory=utc_now)
    answered_at: datetime | None = None


class JobStage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(index=True, foreign_key="job.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    stage_key: str = Field(index=True)
    label: str
    status: str = Field(default="pending", index=True)
    order_index: int = Field(index=True)
    message: str = ""
    details_json: str = "{}"
    error: str | None = None
    is_retryable: bool = True
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class GenerationArtifact(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    job_id: int = Field(index=True, foreign_key="job.id")
    material_id: int | None = Field(default=None, foreign_key="sourcematerial.id")
    stage_key: str = Field(index=True)
    artifact_type: str = Field(index=True)
    input_hash: str = Field(index=True)
    schema_version: str
    prompt_version: str
    content_json: str
    status: str = Field(default="active", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    material_id: int | None = Field(default=None, foreign_key="sourcematerial.id")
    job_type: str
    status: str = Field(default="pending", index=True)
    error: str | None = None
    stage_key: str | None = None
    stage_label: str | None = None
    progress_percent: int = 0
    message: str = ""
    error_stage: str | None = None
    retry_of_job_id: int | None = Field(default=None, foreign_key="job.id")
    resumed_from_job_id: int | None = Field(default=None, foreign_key="job.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

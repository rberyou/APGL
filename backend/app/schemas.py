from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    goal: str = Field(min_length=2, max_length=1000)
    source_type: str = Field(pattern="^(skill|material)$")
    current_level: str | None = None
    time_budget_minutes: int | None = Field(default=None, ge=5, le=600)


class ProjectRead(BaseModel):
    id: int
    title: str
    goal: str
    source_type: str
    current_level: str | None
    time_budget_minutes: int | None
    status: str
    progress_percent: int
    passed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreateResponse(BaseModel):
    project: ProjectRead
    job_id: int | None = None


class MaterialRead(BaseModel):
    id: int
    project_id: int
    filename: str
    content_type: str
    status: str
    storage_path: str | None = None
    file_checksum: str | None = None
    error: str | None = None
    page_count: int
    text_page_count: int
    character_count: int
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialUploadResponse(BaseModel):
    material: MaterialRead
    job_id: int


class JobRead(BaseModel):
    id: int
    project_id: int
    material_id: int | None
    job_type: str
    status: str
    error: str | None
    stage_key: str | None = None
    stage_label: str | None = None
    progress_percent: int = 0
    message: str = ""
    error_stage: str | None = None
    retry_of_job_id: int | None = None
    resumed_from_job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobStageRead(BaseModel):
    id: int
    job_id: int
    project_id: int
    stage_key: str
    label: str
    status: str
    order_index: int
    message: str
    details_json: str
    error: str | None
    is_retryable: bool
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobDetailRead(JobRead):
    stages: list[JobStageRead] = []


class KnowledgePointRead(BaseModel):
    id: int
    client_key: str | None = None
    name: str
    explanation: str
    difficulty: str = "core"
    estimated_weight: float = 1.0
    source_locator: str | None = None
    mastery: float

    model_config = ConfigDict(from_attributes=True)


class LessonRead(BaseModel):
    id: int
    project_id: int
    title: str
    summary: str
    content: str
    order_index: int
    status: str
    knowledge_points: list[KnowledgePointRead] = []
    mastery: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class LessonStepRead(BaseModel):
    id: int
    lesson_id: int
    project_id: int
    step_type: str
    title: str
    body: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class QuizItemRead(BaseModel):
    id: int
    lesson_id: int
    question_type: str
    prompt: str
    options_json: str | None

    model_config = ConfigDict(from_attributes=True)


class AnswerCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


class AnswerResult(BaseModel):
    is_correct: bool
    feedback: str
    explanation: str
    review_task_id: int | None = None


class ReviewTaskRead(BaseModel):
    id: int
    quiz_item_id: int
    prompt: str
    due_at: datetime
    status: str


class ReviewSubmit(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


class MistakeRead(BaseModel):
    id: int
    quiz_item_id: int
    prompt: str
    user_answer: str
    reason: str
    status: str
    created_at: datetime


class MaterialStatus(BaseModel):
    project_id: int
    material_id: int | None
    filename: str | None
    status: str
    page_count: int
    text_page_count: int
    character_count: int
    chunk_count: int
    readable: bool
    message: str


class KnowledgeMapNode(BaseModel):
    id: int
    client_key: str | None = None
    name: str
    explanation: str
    difficulty: str = "core"
    estimated_weight: float = 1.0
    source_locator: str | None = None
    mastery: float
    lesson_ids: list[int]
    lesson_titles: list[str]


class KnowledgeMapEdge(BaseModel):
    id: int
    source_id: int
    target_id: int
    relation_type: str


class KnowledgeMapRead(BaseModel):
    project_id: int
    nodes: list[KnowledgeMapNode]
    edges: list[KnowledgeMapEdge]


class LearningGapRead(BaseModel):
    id: int | None = None
    title: str
    severity: str
    status: str = "open"
    evidence: str = ""


class ProjectTrackerRead(BaseModel):
    project_id: int
    mastery: float
    progress_percent: int
    mastered_topics: list[str]
    learning_gaps: list[LearningGapRead]
    next_plan: str
    last_session_id: int | None = None
    updated_at: datetime


class StudySessionCreate(BaseModel):
    lesson_id: int | None = None
    focus: str | None = None


class StudySessionRead(BaseModel):
    id: int
    project_id: int
    user_id: int
    lesson_id: int | None
    status: str
    focus: str
    summary: str | None
    next_plan: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TutorMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class TutorCitationRead(BaseModel):
    chunk_id: int | None = None
    title: str
    locator: str | None = None
    excerpt: str


class TutorMessageRead(BaseModel):
    id: int
    session_id: int
    project_id: int
    role: str
    content: str
    citations: list[TutorCitationRead] = []
    created_at: datetime


class AssessmentTurnRead(BaseModel):
    id: int
    assessment_id: int
    project_id: int
    lesson_id: int
    knowledge_point_id: int | None
    quiz_item_id: int | None
    status: str
    question: str
    user_answer: str | None
    feedback: str | None
    score: float | None
    mastery_delta: float | None
    missing_concepts: list[str] = []
    next_action: str | None
    citations: list[TutorCitationRead] = []
    created_at: datetime
    answered_at: datetime | None


class AssessmentSessionRead(BaseModel):
    id: int
    project_id: int
    lesson_id: int
    user_id: int
    status: str
    mode: str
    summary: str | None
    lesson_mastery: float
    turns_answered: int
    current_turn: AssessmentTurnRead | None = None
    turns: list[AssessmentTurnRead] = []
    started_at: datetime
    ended_at: datetime | None
    updated_at: datetime


class AssessmentAnswerCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)

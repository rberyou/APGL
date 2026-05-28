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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgePointRead(BaseModel):
    id: int
    name: str
    explanation: str
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

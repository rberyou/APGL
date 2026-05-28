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
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SourceMaterial(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    filename: str
    content_type: str
    raw_text: str
    status: str = Field(default="uploaded", index=True)
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
    name: str
    explanation: str
    mastery: float = 0.0
    source_chunk_id: int | None = Field(default=None, foreign_key="sourcechunk.id")


class LessonUnit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    title: str
    summary: str
    content: str
    order_index: int = Field(index=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=utc_now)


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


class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    project_id: int = Field(index=True, foreign_key="learningproject.id")
    material_id: int | None = Field(default=None, foreign_key="sourcematerial.id")
    job_type: str
    status: str = Field(default="pending", index=True)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

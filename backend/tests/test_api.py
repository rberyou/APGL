import json
import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite:///./backend/data/test.db"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from app.config import settings
from app.database import engine
from app.main import app
from app.models import LearningProject, LessonUnit
from app.services import ai
from app.services import jobs


@pytest.fixture(autouse=True)
def mock_ai_by_default():
    original = {
        "apgl_mock_ai": settings.apgl_mock_ai,
        "llm_api_key": settings.llm_api_key,
        "llm_base_url": settings.llm_base_url,
        "llm_model_fast": settings.llm_model_fast,
        "llm_model_smart": settings.llm_model_smart,
        "llm_api_mode": settings.llm_api_mode,
        "openai_api_key": settings.openai_api_key,
        "openai_base_url": settings.openai_base_url,
        "max_upload_bytes": settings.max_upload_bytes,
    }
    settings.apgl_mock_ai = True
    settings.llm_api_key = None
    settings.llm_base_url = None
    settings.llm_model_fast = None
    settings.llm_model_smart = None
    settings.llm_api_mode = "chat_completions"
    settings.openai_api_key = None
    settings.openai_base_url = None
    yield
    for key, value in original.items():
        setattr(settings, key, value)


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def auth_client() -> TestClient:
    reset_db()
    client = TestClient(app)
    response = client.post(
        "/api/auth/register",
        json={"email": "learner@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    return client


def test_register_login_and_me():
    reset_db()
    client = TestClient(app)
    response = client.post(
        "/api/auth/register",
        json={"email": "learner@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "learner@example.com"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "learner@example.com"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_public_config_includes_upload_limit():
    reset_db()
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["max_upload_bytes"] == settings.max_upload_bytes


def test_skill_job_fails_when_llm_returns_no_lessons(monkeypatch):
    client = auth_client()
    monkeypatch.setattr(
        jobs,
        "generate_skill_plan",
        lambda *_: {"knowledge_points": [], "lessons": []},
    )

    response = client.post(
        "/api/projects",
        json={
            "title": "Empty plan",
            "goal": "Trigger an empty plan.",
            "source_type": "skill",
            "current_level": "Beginner",
            "time_budget_minutes": 30,
        },
    )

    assert response.status_code == 200
    job = client.get(f"/api/jobs/{response.json()['job_id']}")
    assert job.status_code == 200
    assert job.json()["status"] == "failed"
    assert "did not return any lessons" in job.json()["error"]

    latest = client.get(f"/api/jobs/projects/{response.json()['project']['id']}/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == job.json()["id"]
    assert latest.json()["status"] == "failed"


def test_generate_endpoint_recovers_project_without_lessons():
    client = auth_client()
    with Session(engine) as db:
        project = LearningProject(
            user_id=1,
            title="Git",
            goal="Learn Git fundamentals.",
            source_type="skill",
            current_level="Beginner",
            time_budget_minutes=30,
            status="active",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id

    response = client.post(f"/api/projects/{project_id}/generate")
    assert response.status_code == 200
    assert response.json()["job_id"]

    job = client.get(f"/api/jobs/{response.json()['job_id']}")
    assert job.status_code == 200
    assert job.json()["status"] == "completed"

    lessons = client.get(f"/api/projects/{project_id}/lessons")
    assert lessons.status_code == 200
    assert len(lessons.json()) >= 1


def test_store_plan_accepts_string_items():
    reset_db()
    with Session(engine) as db:
        project = LearningProject(
            user_id=1,
            title="Git",
            goal="Learn Git.",
            source_type="skill",
            status="generating",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        jobs._store_plan(
            db,
            project,
            {
                "knowledge_points": ["commit", "branch"],
                "lessons": [
                    {
                        "title": "Git basics",
                        "summary": "Learn basic commands.",
                        "content": "Use git status.",
                        "quiz": ["What does git status do?"],
                    }
                ],
            },
        )

        lessons = db.exec(select(LessonUnit).where(LessonUnit.project_id == project.id)).all()
        assert len(lessons) == 1


def test_skill_project_generates_lessons():
    client = auth_client()
    response = client.post(
        "/api/projects",
        json={
            "title": "Python basics",
            "goal": "Understand Python enough to write small scripts.",
            "source_type": "skill",
            "current_level": "Beginner",
            "time_budget_minutes": 30,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"]

    job = client.get(f"/api/jobs/{payload['job_id']}")
    assert job.status_code == 200
    assert job.json()["status"] == "completed"

    lessons = client.get(f"/api/projects/{payload['project']['id']}/lessons")
    assert lessons.status_code == 200
    assert len(lessons.json()) >= 1


def test_material_upload_quiz_mistake_and_review_flow():
    client = auth_client()
    project_response = client.post(
        "/api/projects",
        json={
            "title": "Learning notes",
            "goal": "Study the provided notes.",
            "source_type": "material",
            "current_level": "Intermediate",
            "time_budget_minutes": 25,
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["project"]["id"]

    upload = client.post(
        f"/api/projects/{project_id}/materials",
        files={
            "file": (
                "notes.md",
                b"# Retrieval practice\n\nReviewing mistakes improves memory and recall.",
                "text/markdown",
            )
        },
    )
    assert upload.status_code == 200
    job_id = upload.json()["job_id"]
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "completed"

    lessons = client.get(f"/api/projects/{project_id}/lessons").json()
    assert lessons
    lesson_id = lessons[0]["id"]

    quiz = client.get(f"/api/lessons/{lesson_id}/quiz").json()
    assert quiz
    answer = client.post(
        f"/api/quiz-items/{quiz[0]['id']}/answer",
        json={"answer": "I do not know yet."},
    )
    assert answer.status_code == 200
    assert answer.json()["is_correct"] is False
    assert answer.json()["review_task_id"]

    reviews = client.get("/api/reviews/today")
    assert reviews.status_code == 200
    assert len(reviews.json()) == 1

    mistakes = client.get("/api/mistakes")
    assert mistakes.status_code == 200
    assert len(mistakes.json()) == 1


def test_material_upload_size_limit_message():
    client = auth_client()
    project_response = client.post(
        "/api/projects",
        json={
            "title": "Small notes",
            "goal": "Test upload limits.",
            "source_type": "material",
            "current_level": "Beginner",
            "time_budget_minutes": 20,
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["project"]["id"]

    original_limit = settings.max_upload_bytes
    settings.max_upload_bytes = 8
    try:
        upload = client.post(
            f"/api/projects/{project_id}/materials",
            files={"file": ("too-large.txt", b"123456789", "text/plain")},
        )
    finally:
        settings.max_upload_bytes = original_limit

    assert upload.status_code == 413
    assert "Maximum upload size" in upload.json()["detail"]


def test_skill_job_fails_without_llm_config_when_mock_disabled():
    client = auth_client()
    settings.apgl_mock_ai = False
    settings.llm_api_key = None
    settings.openai_api_key = None

    response = client.post(
        "/api/projects",
        json={
            "title": "Vulkan",
            "goal": "Learn Vulkan.",
            "source_type": "skill",
            "current_level": "Beginner",
            "time_budget_minutes": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    job = client.get(f"/api/jobs/{payload['job_id']}")
    assert job.status_code == 200
    assert job.json()["status"] == "failed"
    assert "LLM_API_KEY is required" in job.json()["error"]


def test_chat_completions_response_generates_plan(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == "provider-smart"
            content = {
                "knowledge_points": [
                    {"name": "Concept", "explanation": "Understand one concept."}
                ],
                "lessons": [
                    {
                        "title": "Provider lesson",
                        "summary": "Generated by compatible chat completions.",
                        "content": "Study the concept and answer a question.",
                        "quiz": [
                            {
                                "question_type": "short_answer",
                                "prompt": "What did you learn?",
                                "answer": "The core concept.",
                                "explanation": "Checks recall.",
                            }
                        ],
                    }
                ],
            }
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(content))
                    )
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    settings.apgl_mock_ai = False
    settings.llm_api_key = "test-key"
    settings.llm_base_url = "https://provider.example.com/v1"
    settings.llm_model_smart = "provider-smart"
    monkeypatch.setattr(ai, "_client", lambda: fake_client)

    plan = ai.generate_skill_plan("Vulkan", "Learn Vulkan rendering.", "Beginner")

    assert plan["lessons"][0]["title"] == "Provider lesson"
    assert plan["knowledge_points"][0]["name"] == "Concept"


def test_json_parser_handles_reasoning_text_before_json():
    content = '<think>I will return {"not": "this"}.</think>\n\n{"ok": true}\nDone.'
    assert ai._json_from_text(content) == {"ok": True}


def test_json_parser_skips_unrelated_json_before_plan():
    content = 'Example: {"shape": "wrong"}\n\n{"knowledge_points": [], "lessons": [{"title": "A"}]}'
    assert ai._json_from_text(content) == {
        "knowledge_points": [],
        "lessons": [{"title": "A"}],
    }

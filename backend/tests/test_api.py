from sqlmodel import SQLModel
from starlette.testclient import TestClient

from app.database import engine
from app.main import app


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


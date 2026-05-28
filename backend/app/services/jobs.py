import json

from sqlmodel import Session, select

from app.database import engine
from app.models import (
    Job,
    KnowledgePoint,
    LearningProject,
    LessonUnit,
    QuizItem,
    SourceChunk,
    SourceMaterial,
    utc_now,
)
from app.services.ai import generate_material_plan, generate_skill_plan
from app.services.materials import chunk_text


def create_job(
    db: Session,
    user_id: int,
    project_id: int,
    job_type: str,
    material_id: int | None = None,
) -> Job:
    job = Job(
        user_id=user_id,
        project_id=project_id,
        material_id=material_id,
        job_type=job_type,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _set_job_status(db: Session, job: Job, status: str, error: str | None = None) -> None:
    job.status = status
    job.error = error
    job.updated_at = utc_now()
    db.add(job)
    db.commit()


def _set_project_status(db: Session, project_id: int, status: str) -> None:
    project = db.get(LearningProject, project_id)
    if project:
        project.status = status
        project.updated_at = utc_now()
        db.add(project)
        db.commit()


def _store_plan(db: Session, project: LearningProject, plan: dict) -> None:
    knowledge_points = plan.get("knowledge_points") or []
    lessons = plan.get("lessons") or []
    if not lessons:
        raise ValueError("The LLM did not return any lessons. Please regenerate the learning path.")

    kp_rows: list[KnowledgePoint] = []
    for item in knowledge_points[:8]:
        row = KnowledgePoint(
            project_id=project.id,
            name=str(item.get("name") or "Knowledge point")[:160],
            explanation=str(item.get("explanation") or ""),
        )
        db.add(row)
        kp_rows.append(row)
    db.commit()
    for row in kp_rows:
        db.refresh(row)

    for lesson_index, item in enumerate(lessons[:6], start=1):
        lesson = LessonUnit(
            project_id=project.id,
            title=str(item.get("title") or f"Lesson {lesson_index}")[:200],
            summary=str(item.get("summary") or ""),
            content=str(item.get("content") or ""),
            order_index=lesson_index,
        )
        db.add(lesson)
        db.commit()
        db.refresh(lesson)

        quiz_items = item.get("quiz") or []
        for quiz_index, quiz in enumerate(quiz_items[:3]):
            kp = kp_rows[(lesson_index + quiz_index - 1) % len(kp_rows)] if kp_rows else None
            db.add(
                QuizItem(
                    lesson_id=lesson.id,
                    project_id=project.id,
                    knowledge_point_id=kp.id if kp else None,
                    question_type=str(quiz.get("question_type") or "short_answer"),
                    prompt=str(quiz.get("prompt") or quiz.get("question") or "Explain the key idea."),
                    options_json=json.dumps(quiz.get("options")) if quiz.get("options") else None,
                    answer=str(quiz.get("answer") or ""),
                    explanation=str(quiz.get("explanation") or ""),
                )
            )
    project.status = "active"
    project.updated_at = utc_now()
    db.add(project)
    db.commit()


def process_skill_job(job_id: int) -> None:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            return
        _set_job_status(db, job, "processing")
        try:
            project = db.get(LearningProject, job.project_id)
            if not project:
                raise ValueError("Project not found")
            plan = generate_skill_plan(project.title, project.goal, project.current_level)
            _store_plan(db, project, plan)
            _set_job_status(db, job, "completed")
        except Exception as exc:
            _set_project_status(db, job.project_id, "failed")
            _set_job_status(db, job, "failed", str(exc))


def process_material_job(job_id: int) -> None:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            return
        _set_job_status(db, job, "processing")
        try:
            project = db.get(LearningProject, job.project_id)
            material = db.get(SourceMaterial, job.material_id) if job.material_id else None
            if not project or not material:
                raise ValueError("Project or material not found")

            chunks = chunk_text(material.raw_text)
            if not chunks:
                raise ValueError("No readable text found in material")
            chunk_rows: list[SourceChunk] = []
            for item in chunks:
                row = SourceChunk(
                    project_id=project.id,
                    material_id=material.id,
                    position=int(item["position"]),
                    title=str(item["title"]),
                    content=str(item["content"]),
                    locator=str(item["locator"]),
                )
                db.add(row)
                chunk_rows.append(row)
            material.status = "processed"
            db.add(material)
            db.commit()

            plan = generate_material_plan(
                project.title,
                project.goal,
                [row.content for row in chunk_rows],
            )
            _store_plan(db, project, plan)
            _set_job_status(db, job, "completed")
        except Exception as exc:
            _set_project_status(db, job.project_id, "failed")
            if job.material_id:
                material = db.get(SourceMaterial, job.material_id)
                if material:
                    material.status = "failed"
                    db.add(material)
                    db.commit()
            _set_job_status(db, job, "failed", str(exc))

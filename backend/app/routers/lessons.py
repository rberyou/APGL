from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import LearningProject, LessonUnit, User, utc_now
from app.schemas import JobRead, LessonRead
from app.services.jobs import prepare_lesson_job, process_lesson_prepare_job
from app.services.learning import lesson_detail_payload


router = APIRouter(tags=["lessons"])


def _project_for_lesson(db: Session, lesson: LessonUnit, user: User) -> LearningProject:
    project = db.get(LearningProject, lesson.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return project


@router.get("/projects/{project_id}/lessons", response_model=list[LessonRead])
def list_lessons(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = db.get(LearningProject, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    lessons = db.exec(
        select(LessonUnit)
        .where(LessonUnit.project_id == project_id)
        .order_by(LessonUnit.order_index)
    ).all()
    return [lesson_detail_payload(db, lesson) for lesson in lessons]


@router.get("/lessons/{lesson_id}", response_model=LessonRead)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    lesson = db.get(LessonUnit, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _project_for_lesson(db, lesson, user)
    return lesson_detail_payload(db, lesson)


@router.post("/lessons/{lesson_id}/prepare", response_model=JobRead)
def prepare_lesson(
    lesson_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    lesson = db.get(LessonUnit, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _project_for_lesson(db, lesson, user)
    if lesson.content.strip():
        job = prepare_lesson_job(db, user.id, lesson)
        job.status = "completed"
        db.add(job)
        db.commit()
        return job
    job = prepare_lesson_job(db, user.id, lesson)
    background_tasks.add_task(process_lesson_prepare_job, job.id, lesson.id)
    return job


@router.post("/lessons/{lesson_id}/complete", response_model=LessonRead)
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    lesson = db.get(LessonUnit, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    project = _project_for_lesson(db, lesson, user)
    lesson.status = "completed"
    db.add(lesson)

    lessons = db.exec(select(LessonUnit).where(LessonUnit.project_id == project.id)).all()
    completed = sum(1 for item in lessons if item.status == "completed" or item.id == lesson.id)
    project.progress_percent = int((completed / max(1, len(lessons))) * 100)
    project.updated_at = utc_now()
    db.add(project)
    db.commit()
    db.refresh(lesson)
    return lesson

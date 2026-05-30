from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import AssessmentSession, LearningProject, LessonUnit, User
from app.schemas import AssessmentAnswerCreate, AssessmentSessionRead
from app.services.ai import AIServiceError
from app.services.learning import (
    answer_assessment,
    assessment_payload,
    complete_assessment,
    get_assessment,
    start_assessment,
)


router = APIRouter(tags=["assessments"])


def _project_for_lesson(db: Session, lesson: LessonUnit, user: User) -> LearningProject:
    project = db.get(LearningProject, lesson.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return project


def _assessment(db: Session, assessment_id: int, user: User) -> tuple[AssessmentSession, LearningProject]:
    assessment = db.get(AssessmentSession, assessment_id)
    if not assessment or assessment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Assessment not found")
    project = db.get(LearningProject, assessment.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment, project


@router.post("/lessons/{lesson_id}/assessment/start", response_model=AssessmentSessionRead)
def start_lesson_assessment(
    lesson_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    lesson = db.get(LessonUnit, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    project = _project_for_lesson(db, lesson, user)
    try:
        assessment = start_assessment(db, lesson, project, user)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return assessment_payload(db, assessment)


@router.get("/assessments/{assessment_id}", response_model=AssessmentSessionRead)
def read_assessment(
    assessment_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assessment, _ = _assessment(db, assessment_id, user)
    try:
        assessment = get_assessment(db, assessment)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return assessment_payload(db, assessment)


@router.post("/assessments/{assessment_id}/answer", response_model=AssessmentSessionRead)
def answer_assessment_turn(
    assessment_id: int,
    payload: AssessmentAnswerCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assessment, project = _assessment(db, assessment_id, user)
    if assessment.status != "active":
        return assessment_payload(db, assessment)
    try:
        assessment = answer_assessment(db, assessment, project, user, payload.answer)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return assessment_payload(db, assessment)


@router.post("/assessments/{assessment_id}/end", response_model=AssessmentSessionRead)
def end_assessment(
    assessment_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assessment, _ = _assessment(db, assessment_id, user)
    if assessment.status == "active":
        assessment = complete_assessment(db, assessment)
    return assessment_payload(db, assessment)

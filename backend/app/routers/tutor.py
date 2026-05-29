import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import LearningProject, LessonUnit, StudySession, User
from app.schemas import (
    KnowledgeMapRead,
    LessonStepRead,
    ProjectTrackerRead,
    StudySessionCreate,
    StudySessionRead,
    TutorMessageCreate,
    TutorMessageRead,
)
from app.services.ai import AIServiceError
from app.services.learning import (
    end_session,
    knowledge_map,
    lesson_steps,
    list_project_sessions,
    list_session_messages,
    project_tracker,
    send_tutor_message,
    start_session,
)


router = APIRouter(tags=["tutor"])


def _project(db: Session, project_id: int, user: User) -> LearningProject:
    project = db.get(LearningProject, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _session(db: Session, session_id: int, user: User) -> tuple[StudySession, LearningProject]:
    session = db.get(StudySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    project = _project(db, session.project_id, user)
    return session, project


@router.get("/projects/{project_id}/tracker", response_model=ProjectTrackerRead)
def get_tracker(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return project_tracker(db, _project(db, project_id, user))


@router.get("/projects/{project_id}/knowledge-map", response_model=KnowledgeMapRead)
def get_knowledge_map(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return knowledge_map(db, _project(db, project_id, user))


@router.get("/lessons/{lesson_id}/steps", response_model=list[LessonStepRead])
def get_lesson_steps(
    lesson_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    lesson = db.get(LessonUnit, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _project(db, lesson.project_id, user)
    return lesson_steps(db, lesson)


@router.post("/projects/{project_id}/sessions", response_model=StudySessionRead)
def create_session(
    project_id: int,
    payload: StudySessionCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = _project(db, project_id, user)
    if payload.lesson_id:
        lesson = db.get(LessonUnit, payload.lesson_id)
        if not lesson or lesson.project_id != project.id:
            raise HTTPException(status_code=404, detail="Lesson not found")
    return start_session(db, project, user, payload.lesson_id, payload.focus)


@router.get("/projects/{project_id}/sessions", response_model=list[StudySessionRead])
def get_sessions(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return list_project_sessions(db, _project(db, project_id, user))


@router.get("/sessions/{session_id}/messages", response_model=list[TutorMessageRead])
def get_messages(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    session, _ = _session(db, session_id, user)
    return [_message_payload(message) for message in list_session_messages(db, session)]


@router.post("/sessions/{session_id}/messages", response_model=TutorMessageRead)
def create_message(
    session_id: int,
    payload: TutorMessageCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    session, project = _session(db, session_id, user)
    if session.status != "active":
        raise HTTPException(status_code=409, detail="This tutor session is already closed")
    try:
        message = send_tutor_message(db, session, project, user, payload.content)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _message_payload(message)


@router.post("/sessions/{session_id}/end", response_model=StudySessionRead)
def close_session(
    session_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    session, project = _session(db, session_id, user)
    if session.status != "active":
        return session
    try:
        return end_session(db, session, project, user)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _message_payload(message):
    try:
        citations = json.loads(message.citations_json or "[]")
    except json.JSONDecodeError:
        citations = []
    return {
        "id": message.id,
        "session_id": message.session_id,
        "project_id": message.project_id,
        "role": message.role,
        "content": message.content,
        "citations": citations,
        "created_at": message.created_at,
    }

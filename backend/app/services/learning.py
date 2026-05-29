from __future__ import annotations

import json

from sqlmodel import Session, select

from app.models import (
    KnowledgeEdge,
    KnowledgePoint,
    LearningEvent,
    LearningGap,
    LearningProject,
    LessonStep,
    LessonUnit,
    ProjectTracker,
    QuizItem,
    SourceChunk,
    SourceCitation,
    StudySession,
    TutorMessage,
    TutorProfile,
    User,
    utc_now,
)
from app.services.ai import generate_tutor_reply, summarize_tutor_session
from app.services.retrieval import search_project_chunks


def ensure_project_state(db: Session, project: LearningProject) -> None:
    profile = db.exec(
        select(TutorProfile).where(TutorProfile.project_id == project.id)
    ).first()
    if not profile:
        db.add(TutorProfile(project_id=project.id))

    tracker = db.exec(
        select(ProjectTracker).where(ProjectTracker.project_id == project.id)
    ).first()
    if not tracker:
        db.add(
            ProjectTracker(
                project_id=project.id,
                next_plan="Start a tutor session and explain what you already know.",
            )
        )
    db.commit()
    _ensure_knowledge_edges(db, project.id)
    _ensure_lesson_steps(db, project.id)


def project_tracker(db: Session, project: LearningProject) -> dict:
    ensure_project_state(db, project)
    tracker = db.exec(
        select(ProjectTracker).where(ProjectTracker.project_id == project.id)
    ).one()
    open_gaps = db.exec(
        select(LearningGap)
        .where(LearningGap.project_id == project.id)
        .where(LearningGap.status == "open")
        .order_by(LearningGap.updated_at.desc())
    ).all()
    return {
        "project_id": project.id,
        "mastery": tracker.mastery,
        "progress_percent": project.progress_percent,
        "mastered_topics": _json_list(tracker.mastered_topics_json),
        "learning_gaps": [
            {
                "id": gap.id,
                "title": gap.title,
                "severity": gap.severity,
                "status": gap.status,
                "evidence": gap.evidence,
            }
            for gap in open_gaps
        ],
        "next_plan": tracker.next_plan,
        "last_session_id": tracker.last_session_id,
        "updated_at": tracker.updated_at,
    }


def knowledge_map(db: Session, project: LearningProject) -> dict:
    ensure_project_state(db, project)
    points = db.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.project_id == project.id)
        .order_by(KnowledgePoint.id)
    ).all()
    lessons = db.exec(
        select(LessonUnit)
        .where(LessonUnit.project_id == project.id)
        .order_by(LessonUnit.order_index)
    ).all()
    quiz_items = db.exec(
        select(QuizItem).where(QuizItem.project_id == project.id)
    ).all()
    lesson_by_id = {lesson.id: lesson for lesson in lessons}
    lesson_ids_by_kp: dict[int, set[int]] = {}
    for quiz in quiz_items:
        if quiz.knowledge_point_id and quiz.lesson_id:
            lesson_ids_by_kp.setdefault(quiz.knowledge_point_id, set()).add(quiz.lesson_id)
    edges = db.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.project_id == project.id)
    ).all()
    return {
        "project_id": project.id,
        "nodes": [
            {
                "id": point.id,
                "name": point.name,
                "explanation": point.explanation,
                "mastery": point.mastery,
                "lesson_ids": sorted(lesson_ids_by_kp.get(point.id or 0, set())),
                "lesson_titles": [
                    lesson_by_id[lesson_id].title
                    for lesson_id in sorted(lesson_ids_by_kp.get(point.id or 0, set()))
                    if lesson_id in lesson_by_id
                ],
            }
            for point in points
        ],
        "edges": [
            {
                "id": edge.id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
            }
            for edge in edges
        ],
    }


def lesson_steps(db: Session, lesson: LessonUnit) -> list[LessonStep]:
    _ensure_lesson_steps(db, lesson.project_id)
    return db.exec(
        select(LessonStep)
        .where(LessonStep.lesson_id == lesson.id)
        .order_by(LessonStep.order_index)
    ).all()


def start_session(
    db: Session,
    project: LearningProject,
    user: User,
    lesson_id: int | None,
    focus: str | None,
) -> StudySession:
    ensure_project_state(db, project)
    lesson = db.get(LessonUnit, lesson_id) if lesson_id else None
    session = StudySession(
        project_id=project.id,
        user_id=user.id,
        lesson_id=lesson.id if lesson else None,
        focus=focus or (lesson.title if lesson else project.goal),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    opening = TutorMessage(
        session_id=session.id,
        project_id=project.id,
        user_id=user.id,
        role="assistant",
        content=(
            f"Let's start with {session.focus}. Tell me what you already understand, "
            "where you feel stuck, or ask for a quick explanation."
        ),
    )
    db.add(opening)
    db.commit()
    return session


def list_project_sessions(db: Session, project: LearningProject) -> list[StudySession]:
    ensure_project_state(db, project)
    return db.exec(
        select(StudySession)
        .where(StudySession.project_id == project.id)
        .order_by(StudySession.started_at.desc())
    ).all()


def list_session_messages(db: Session, session: StudySession) -> list[TutorMessage]:
    return db.exec(
        select(TutorMessage)
        .where(TutorMessage.session_id == session.id)
        .order_by(TutorMessage.created_at)
    ).all()


def send_tutor_message(
    db: Session,
    session: StudySession,
    project: LearningProject,
    user: User,
    content: str,
) -> TutorMessage:
    user_message = TutorMessage(
        session_id=session.id,
        project_id=project.id,
        user_id=user.id,
        role="user",
        content=content,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    chunks = search_project_chunks(db, project.id, f"{session.focus} {content}", limit=4)
    tracker = project_tracker(db, project)
    history = [
        {"role": message.role, "content": message.content}
        for message in list_session_messages(db, session)
    ]
    reply = generate_tutor_reply(
        project.title,
        project.goal,
        session.focus,
        content,
        [_chunk_context(chunk) for chunk in chunks],
        history,
        json.dumps(
            {
                "mastery": tracker["mastery"],
                "learning_gaps": tracker["learning_gaps"][:5],
                "next_plan": tracker["next_plan"],
            },
            ensure_ascii=False,
        ),
    )
    citations = [_citation_payload(chunk) for chunk in chunks]
    assistant_message = TutorMessage(
        session_id=session.id,
        project_id=project.id,
        user_id=user.id,
        role="assistant",
        content=_format_tutor_reply(reply),
        citations_json=json.dumps(citations, ensure_ascii=False),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    for chunk in chunks:
        if chunk.id:
            db.add(
                SourceCitation(
                    project_id=project.id,
                    source_chunk_id=chunk.id,
                    tutor_message_id=assistant_message.id,
                    label=chunk.locator or chunk.title,
                    excerpt=chunk.content[:500],
                )
            )
    db.add(
        LearningEvent(
            project_id=project.id,
            user_id=user.id,
            event_type="tutor_message",
            lesson_id=session.lesson_id,
            metadata_json=json.dumps({"session_id": session.id}, ensure_ascii=False),
        )
    )
    db.commit()
    return assistant_message


def end_session(db: Session, session: StudySession, project: LearningProject, user: User) -> StudySession:
    messages = [
        {"role": message.role, "content": message.content}
        for message in list_session_messages(db, session)
    ]
    summary = summarize_tutor_session(project.title, project.goal, session.focus, messages)
    session.status = "completed"
    session.summary = summary["summary"]
    session.next_plan = summary["next_plan"]
    session.ended_at = utc_now()
    db.add(session)

    tracker = db.exec(
        select(ProjectTracker).where(ProjectTracker.project_id == project.id)
    ).first()
    if not tracker:
        tracker = ProjectTracker(project_id=project.id)
    tracker.last_session_id = session.id
    tracker.next_plan = summary["next_plan"]
    tracker.mastered_topics_json = json.dumps(summary["mastered_topics"], ensure_ascii=False)
    tracker.learning_gaps_json = json.dumps(summary["learning_gaps"], ensure_ascii=False)
    tracker.mastery = _recalculate_project_mastery(db, project.id)
    tracker.updated_at = utc_now()
    db.add(tracker)

    for item in summary["learning_gaps"]:
        db.add(
            LearningGap(
                project_id=project.id,
                title=str(item.get("title") or "Learning gap")[:200],
                severity=str(item.get("severity") or "medium")[:40],
                evidence=str(item.get("evidence") or ""),
            )
        )
    project.updated_at = utc_now()
    project.progress_percent = max(project.progress_percent, int(tracker.mastery * 100))
    db.add(project)
    db.add(
        LearningEvent(
            project_id=project.id,
            user_id=user.id,
            event_type="session_completed",
            lesson_id=session.lesson_id,
            metadata_json=json.dumps({"session_id": session.id}, ensure_ascii=False),
        )
    )
    db.commit()
    db.refresh(session)
    return session


def update_mastery_from_answer(
    db: Session,
    project_id: int,
    user_id: int,
    knowledge_point_id: int | None,
    lesson_id: int,
    is_correct: bool,
) -> None:
    if knowledge_point_id:
        point = db.get(KnowledgePoint, knowledge_point_id)
        if point:
            point.mastery = min(1.0, point.mastery + 0.15) if is_correct else max(0.0, point.mastery - 0.05)
            db.add(point)
            if not is_correct:
                db.add(
                    LearningGap(
                        project_id=project_id,
                        knowledge_point_id=point.id,
                        title=f"Review {point.name}",
                        severity="high",
                        evidence="Quiz answer was marked incorrect.",
                    )
                )
    tracker = db.exec(
        select(ProjectTracker).where(ProjectTracker.project_id == project_id)
    ).first()
    if tracker:
        tracker.mastery = _recalculate_project_mastery(db, project_id)
        tracker.updated_at = utc_now()
        db.add(tracker)
    db.add(
        LearningEvent(
            project_id=project_id,
            user_id=user_id,
            event_type="quiz_answer_correct" if is_correct else "quiz_answer_incorrect",
            knowledge_point_id=knowledge_point_id,
            lesson_id=lesson_id,
        )
    )


def _ensure_knowledge_edges(db: Session, project_id: int) -> None:
    existing = db.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.project_id == project_id)
    ).first()
    if existing:
        return
    points = db.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.project_id == project_id)
        .order_by(KnowledgePoint.id)
    ).all()
    for previous, current in zip(points, points[1:]):
        db.add(
            KnowledgeEdge(
                project_id=project_id,
                source_id=previous.id,
                target_id=current.id,
                relation_type="prerequisite",
            )
        )
    db.commit()


def _ensure_lesson_steps(db: Session, project_id: int) -> None:
    existing = db.exec(
        select(LessonStep).where(LessonStep.project_id == project_id)
    ).first()
    if existing:
        return
    lessons = db.exec(
        select(LessonUnit)
        .where(LessonUnit.project_id == project_id)
        .order_by(LessonUnit.order_index)
    ).all()
    for lesson in lessons:
        steps = [
            ("orient", "Set the target", lesson.summary or "Clarify what this lesson is for."),
            ("explain", "Tutor explanation", lesson.content or "Work through the core idea with the tutor."),
            ("practice", "Practice check", "Explain the idea in your own words, then ask the tutor to challenge your understanding."),
        ]
        for index, (step_type, title, body) in enumerate(steps, start=1):
            db.add(
                LessonStep(
                    lesson_id=lesson.id,
                    project_id=project_id,
                    step_type=step_type,
                    title=title,
                    body=body,
                    order_index=index,
                )
            )
    db.commit()


def _recalculate_project_mastery(db: Session, project_id: int) -> float:
    points = db.exec(select(KnowledgePoint).where(KnowledgePoint.project_id == project_id)).all()
    if not points:
        return 0.0
    return round(sum(point.mastery for point in points) / len(points), 2)


def _json_list(value: str) -> list:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _chunk_context(chunk: SourceChunk) -> str:
    return f"{chunk.locator or chunk.title}\n{chunk.content[:1800]}"


def _citation_payload(chunk: SourceChunk) -> dict:
    return {
        "chunk_id": chunk.id,
        "title": chunk.title,
        "locator": chunk.locator,
        "excerpt": chunk.content[:260],
    }


def _format_tutor_reply(reply: dict) -> str:
    parts = [str(reply.get("answer") or "").strip()]
    questions = reply.get("follow_up_questions") or []
    if questions:
        parts.append("Check yourself: " + " ".join(str(item) for item in questions))
    actions = reply.get("suggested_actions") or []
    if actions:
        parts.append("Next: " + "; ".join(str(item) for item in actions))
    return "\n\n".join(part for part in parts if part)

from __future__ import annotations

import json

from datetime import timedelta

from sqlmodel import Session, select

from app.models import (
    KnowledgeEdge,
    KnowledgePoint,
    LearningEvent,
    LearningGap,
    LearningProject,
    LessonKnowledgePoint,
    LessonStep,
    LessonUnit,
    AssessmentSession,
    AssessmentTurn,
    MistakeRecord,
    ProjectTracker,
    QuizItem,
    ReviewTask,
    SourceChunk,
    SourceCitation,
    StudySession,
    TutorMessage,
    TutorProfile,
    User,
    utc_now,
)
from app.services.ai import (
    evaluate_assessment_answer,
    generate_assessment_question,
    generate_tutor_reply,
    summarize_tutor_session,
)
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
    lesson_by_id = {lesson.id: lesson for lesson in lessons}
    lesson_ids_by_kp: dict[int, set[int]] = {}
    mappings = db.exec(
        select(LessonKnowledgePoint).where(LessonKnowledgePoint.project_id == project.id)
    ).all()
    for mapping in mappings:
        lesson_ids_by_kp.setdefault(mapping.knowledge_point_id, set()).add(mapping.lesson_id)
    edges = db.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.project_id == project.id)
    ).all()
    return {
        "project_id": project.id,
        "nodes": [
            {
                "id": point.id,
                "client_key": point.client_key,
                "name": point.name,
                "explanation": point.explanation,
                "difficulty": point.difficulty,
                "estimated_weight": point.estimated_weight,
                "source_locator": point.source_locator,
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


def lesson_detail_payload(db: Session, lesson: LessonUnit) -> dict:
    points = lesson_knowledge_points(db, lesson)
    mastery = lesson_mastery(db, lesson.id)
    return {
        "id": lesson.id,
        "project_id": lesson.project_id,
        "title": lesson.title,
        "summary": lesson.summary,
        "content": lesson.content,
        "order_index": lesson.order_index,
        "status": lesson.status,
        "knowledge_points": points,
        "mastery": mastery,
    }


def lesson_knowledge_points(db: Session, lesson: LessonUnit) -> list[KnowledgePoint]:
    mappings = db.exec(
        select(LessonKnowledgePoint)
        .where(LessonKnowledgePoint.lesson_id == lesson.id)
        .order_by(LessonKnowledgePoint.order_index)
    ).all()
    points: list[KnowledgePoint] = []
    for mapping in mappings:
        point = db.get(KnowledgePoint, mapping.knowledge_point_id)
        if point:
            points.append(point)
    return points


def lesson_mastery(db: Session, lesson_id: int) -> float:
    mappings = db.exec(
        select(LessonKnowledgePoint).where(LessonKnowledgePoint.lesson_id == lesson_id)
    ).all()
    if not mappings:
        return 0.0
    values = []
    for mapping in mappings:
        point = db.get(KnowledgePoint, mapping.knowledge_point_id)
        if point:
            values.append(point.mastery)
    return round(sum(values) / len(values), 2) if values else 0.0


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


def start_assessment(db: Session, lesson: LessonUnit, project: LearningProject, user: User) -> AssessmentSession:
    existing = db.exec(
        select(AssessmentSession)
        .where(AssessmentSession.lesson_id == lesson.id)
        .where(AssessmentSession.user_id == user.id)
        .where(AssessmentSession.status == "active")
        .order_by(AssessmentSession.started_at.desc())
    ).first()
    if existing:
        _ensure_assessment_turn(db, existing, lesson, project)
        return existing
    assessment = AssessmentSession(
        project_id=project.id,
        lesson_id=lesson.id,
        user_id=user.id,
        mode="quiz",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    _ensure_assessment_turn(db, assessment, lesson, project)
    return assessment


def get_assessment(db: Session, assessment: AssessmentSession) -> AssessmentSession:
    lesson = db.get(LessonUnit, assessment.lesson_id)
    project = db.get(LearningProject, assessment.project_id)
    if lesson and project and assessment.status == "active":
        _ensure_assessment_turn(db, assessment, lesson, project)
    return assessment


def answer_assessment(
    db: Session,
    assessment: AssessmentSession,
    project: LearningProject,
    user: User,
    answer: str,
) -> AssessmentSession:
    turn = _current_unanswered_turn(db, assessment.id)
    if not turn:
        lesson = db.get(LessonUnit, assessment.lesson_id)
        if not lesson:
            raise ValueError("Lesson not found")
        _ensure_assessment_turn(db, assessment, lesson, project)
        turn = _current_unanswered_turn(db, assessment.id)
    if not turn:
        raise ValueError("No active assessment question is available.")
    point = db.get(KnowledgePoint, turn.knowledge_point_id) if turn.knowledge_point_id else None
    expected = _turn_expected_idea(turn)
    result = evaluate_assessment_answer(
        turn.question,
        expected,
        answer,
        _kp_dict(point) if point else {},
    )
    score = _clamp(float(result.get("score") or 0.0), 0.0, 1.0)
    raw_delta = float(result.get("mastery_delta") or 0.0)
    if score >= 0.8:
        delta = _clamp(raw_delta, 0.0, 0.12)
    else:
        delta = _clamp(raw_delta, -0.05, 0.08)
    if point:
        point.mastery = _clamp(point.mastery + delta, 0.0, 1.0)
        db.add(point)
    missing = [str(item) for item in (result.get("missing_concepts") or [])[:8]]
    turn.status = "answered"
    turn.user_answer = answer
    turn.feedback = str(result.get("feedback") or "")
    turn.score = score
    turn.mastery_delta = delta
    turn.missing_concepts_json = json.dumps(missing, ensure_ascii=False)
    turn.next_action = str(result.get("next_action") or ("move_on" if score >= 0.8 else "ask_follow_up"))
    turn.answered_at = utc_now()
    db.add(turn)
    review_task_id = None
    if (not bool(result.get("is_correct"))) or score < 0.70:
        review_task_id = _create_assessment_review(db, turn, project, user, point)
    elif score < 0.80 and point:
        _upsert_learning_gap(
            db,
            project.id,
            point.id,
            f"Practice {point.name}",
            "medium",
            turn.feedback or "Assessment showed partial understanding.",
        )
    db.add(
        LearningEvent(
            project_id=project.id,
            user_id=user.id,
            event_type="assessment_answer",
            knowledge_point_id=point.id if point else None,
            lesson_id=assessment.lesson_id,
            metadata_json=json.dumps(
                {"assessment_id": assessment.id, "turn_id": turn.id, "score": score, "review_task_id": review_task_id},
                ensure_ascii=False,
            ),
        )
    )
    assessment.updated_at = utc_now()
    db.add(assessment)
    db.commit()
    refresh_project_mastery(db, project.id)
    if lesson_mastery(db, assessment.lesson_id) >= 0.80:
        complete_assessment(db, assessment, "Lesson mastery threshold reached.")
    else:
        lesson = db.get(LessonUnit, assessment.lesson_id)
        if lesson:
            _ensure_assessment_turn(db, assessment, lesson, project)
    return assessment


def complete_assessment(db: Session, assessment: AssessmentSession, summary: str | None = None) -> AssessmentSession:
    assessment.status = "completed"
    assessment.summary = summary or "Assessment ended before mastery was complete."
    assessment.ended_at = utc_now()
    assessment.updated_at = assessment.ended_at
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def assessment_payload(db: Session, assessment: AssessmentSession) -> dict:
    turns = db.exec(
        select(AssessmentTurn)
        .where(AssessmentTurn.assessment_id == assessment.id)
        .order_by(AssessmentTurn.created_at)
    ).all()
    current = next((turn for turn in turns if turn.status == "asked"), None)
    return {
        "id": assessment.id,
        "project_id": assessment.project_id,
        "lesson_id": assessment.lesson_id,
        "user_id": assessment.user_id,
        "status": assessment.status,
        "mode": assessment.mode,
        "summary": assessment.summary,
        "lesson_mastery": lesson_mastery(db, assessment.lesson_id),
        "turns_answered": sum(1 for turn in turns if turn.status == "answered"),
        "current_turn": _turn_payload(current) if current else None,
        "turns": [_turn_payload(turn) for turn in turns],
        "started_at": assessment.started_at,
        "ended_at": assessment.ended_at,
        "updated_at": assessment.updated_at,
    }


def refresh_project_mastery(db: Session, project_id: int) -> float:
    mastery = _recalculate_project_mastery(db, project_id)
    tracker = db.exec(select(ProjectTracker).where(ProjectTracker.project_id == project_id)).first()
    if not tracker:
        tracker = ProjectTracker(project_id=project_id)
    tracker.mastery = mastery
    tracker.next_plan = _next_plan(db, project_id, mastery)
    tracker.updated_at = utc_now()
    db.add(tracker)
    project = db.get(LearningProject, project_id)
    if project:
        project.progress_percent = int(round(mastery * 100))
        high_gaps = db.exec(
            select(LearningGap)
            .where(LearningGap.project_id == project_id)
            .where(LearningGap.status == "open")
            .where(LearningGap.severity == "high")
        ).first()
        if mastery >= 0.80 and not high_gaps and project.status != "passed":
            project.status = "passed"
            project.passed_at = utc_now()
        project.updated_at = utc_now()
        db.add(project)
    db.commit()
    return mastery


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
    refresh_project_mastery(db, project_id)


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
    weights = [point.estimated_weight if point.estimated_weight > 0 else 0 for point in points]
    total = sum(weights)
    if total <= 0:
        return round(sum(point.mastery for point in points) / len(points), 2)
    return round(sum(point.mastery * weight for point, weight in zip(points, weights)) / total, 2)


def _ensure_assessment_turn(
    db: Session,
    assessment: AssessmentSession,
    lesson: LessonUnit,
    project: LearningProject,
) -> None:
    if _current_unanswered_turn(db, assessment.id):
        return
    if lesson_mastery(db, lesson.id) >= 0.80:
        complete_assessment(db, assessment, "Lesson mastery threshold reached.")
        return
    point = _lowest_mastery_lesson_point(db, lesson)
    if not point:
        return
    recent = [
        _turn_payload(turn)
        for turn in db.exec(
            select(AssessmentTurn)
            .where(AssessmentTurn.assessment_id == assessment.id)
            .order_by(AssessmentTurn.created_at.desc())
            .limit(5)
        ).all()
    ]
    chunks = search_project_chunks(db, project.id, f"{lesson.title} {point.name}", limit=3)
    question = generate_assessment_question(
        project.title,
        lesson.title,
        _kp_dict(point),
        recent,
        [_chunk_context(chunk) for chunk in chunks],
    )
    turn = AssessmentTurn(
        assessment_id=assessment.id,
        project_id=project.id,
        lesson_id=lesson.id,
        knowledge_point_id=point.id,
        question=str(question.get("question") or ""),
        citations_json=json.dumps(question.get("citations") or [], ensure_ascii=False),
        missing_concepts_json=json.dumps(
            {"expected_idea": str(question.get("expected_idea") or point.explanation)},
            ensure_ascii=False,
        ),
    )
    db.add(turn)
    assessment.updated_at = utc_now()
    db.add(assessment)
    db.commit()


def _current_unanswered_turn(db: Session, assessment_id: int) -> AssessmentTurn | None:
    return db.exec(
        select(AssessmentTurn)
        .where(AssessmentTurn.assessment_id == assessment_id)
        .where(AssessmentTurn.status == "asked")
        .order_by(AssessmentTurn.created_at.desc())
    ).first()


def _lowest_mastery_lesson_point(db: Session, lesson: LessonUnit) -> KnowledgePoint | None:
    points = lesson_knowledge_points(db, lesson)
    if not points:
        return db.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.project_id == lesson.project_id)
            .order_by(KnowledgePoint.mastery, KnowledgePoint.id)
        ).first()
    return min(points, key=lambda point: (point.mastery, point.id or 0))


def _create_assessment_review(
    db: Session,
    turn: AssessmentTurn,
    project: LearningProject,
    user: User,
    point: KnowledgePoint | None,
) -> int | None:
    quiz = QuizItem(
        lesson_id=turn.lesson_id,
        project_id=project.id,
        knowledge_point_id=point.id if point else None,
        question_type="dynamic_assessment",
        prompt=turn.question,
        answer=_turn_expected_idea(turn),
        explanation=turn.feedback or "",
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    turn.quiz_item_id = quiz.id
    db.add(turn)
    mistake = MistakeRecord(
        quiz_item_id=quiz.id,
        user_id=user.id,
        knowledge_point_id=point.id if point else None,
        user_answer=turn.user_answer or "",
        reason=turn.feedback or "Assessment answer needs review.",
    )
    db.add(mistake)
    db.commit()
    db.refresh(mistake)
    review = ReviewTask(
        user_id=user.id,
        quiz_item_id=quiz.id,
        mistake_id=mistake.id,
        due_at=utc_now(),
    )
    db.add(review)
    if point:
        _upsert_learning_gap(
            db,
            project.id,
            point.id,
            f"Review {point.name}",
            "high" if (turn.score or 0) < 0.7 else "medium",
            turn.feedback or "Assessment answer needs review.",
        )
    db.commit()
    db.refresh(review)
    return review.id


def _upsert_learning_gap(
    db: Session,
    project_id: int,
    point_id: int | None,
    title: str,
    severity: str,
    evidence: str,
) -> None:
    gap = db.exec(
        select(LearningGap)
        .where(LearningGap.project_id == project_id)
        .where(LearningGap.knowledge_point_id == point_id)
        .where(LearningGap.status == "open")
    ).first()
    if not gap:
        gap = LearningGap(project_id=project_id, knowledge_point_id=point_id, title=title)
    gap.severity = severity
    gap.evidence = evidence
    gap.updated_at = utc_now()
    db.add(gap)


def _turn_expected_idea(turn: AssessmentTurn) -> str:
    try:
        parsed = json.loads(turn.missing_concepts_json or "{}")
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        return str(parsed.get("expected_idea") or "")
    return ""


def _turn_payload(turn: AssessmentTurn | None) -> dict | None:
    if not turn:
        return None
    try:
        missing = json.loads(turn.missing_concepts_json or "[]")
    except json.JSONDecodeError:
        missing = []
    expected = None
    if isinstance(missing, dict):
        expected = missing.get("expected_idea")
        missing = []
    try:
        citations = json.loads(turn.citations_json or "[]")
    except json.JSONDecodeError:
        citations = []
    return {
        "id": turn.id,
        "assessment_id": turn.assessment_id,
        "project_id": turn.project_id,
        "lesson_id": turn.lesson_id,
        "knowledge_point_id": turn.knowledge_point_id,
        "quiz_item_id": turn.quiz_item_id,
        "status": turn.status,
        "question": turn.question,
        "user_answer": turn.user_answer,
        "feedback": turn.feedback,
        "score": turn.score,
        "mastery_delta": turn.mastery_delta,
        "missing_concepts": missing if isinstance(missing, list) else [],
        "next_action": turn.next_action or ("expected: " + str(expected) if expected and turn.status == "answered" else None),
        "citations": citations if isinstance(citations, list) else [],
        "created_at": turn.created_at,
        "answered_at": turn.answered_at,
    }


def _kp_dict(point: KnowledgePoint | None) -> dict:
    if not point:
        return {}
    return {
        "id": point.id,
        "client_key": point.client_key,
        "name": point.name,
        "explanation": point.explanation,
        "difficulty": point.difficulty,
        "estimated_weight": point.estimated_weight,
        "mastery": point.mastery,
    }


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _next_plan(db: Session, project_id: int, mastery: float) -> str:
    lesson = db.exec(
        select(LessonUnit)
        .where(LessonUnit.project_id == project_id)
        .order_by(LessonUnit.order_index)
    ).first()
    if mastery >= 0.8:
        return "Project mastery is strong. Review remaining weak points or start a new challenge."
    if lesson:
        return f"Continue with {lesson.title} and use Quiz me to raise mastery."
    return "Continue generation, then start the first lesson."


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

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import (
    LearningProject,
    LessonUnit,
    MistakeRecord,
    QuizItem,
    ReviewTask,
    User,
    UserAnswer,
    utc_now,
)
from app.schemas import AnswerCreate, AnswerResult, QuizItemRead
from app.services.ai import AIServiceError
from app.services.ai import grade_answer
from app.services.learning import update_mastery_from_answer


router = APIRouter(tags=["quiz"])


def _assert_quiz_owner(db: Session, quiz: QuizItem, user: User) -> None:
    project = db.get(LearningProject, quiz.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Quiz item not found")


@router.get("/lessons/{lesson_id}/quiz", response_model=list[QuizItemRead])
def get_lesson_quiz(
    lesson_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    lesson = db.get(LessonUnit, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    project = db.get(LearningProject, lesson.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return db.exec(select(QuizItem).where(QuizItem.lesson_id == lesson_id)).all()


@router.post("/quiz-items/{quiz_item_id}/answer", response_model=AnswerResult)
def answer_quiz_item(
    quiz_item_id: int,
    payload: AnswerCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    quiz = db.get(QuizItem, quiz_item_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz item not found")
    _assert_quiz_owner(db, quiz, user)

    try:
        graded = grade_answer(quiz.prompt, quiz.answer, payload.answer)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    user_answer = UserAnswer(
        quiz_item_id=quiz.id,
        user_id=user.id,
        answer=payload.answer,
        is_correct=graded["is_correct"],
        feedback=graded["feedback"],
    )
    db.add(user_answer)
    review_task_id = None
    if not graded["is_correct"]:
        mistake = MistakeRecord(
            quiz_item_id=quiz.id,
            user_id=user.id,
            knowledge_point_id=quiz.knowledge_point_id,
            user_answer=payload.answer,
            reason=graded["feedback"],
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
        db.commit()
        db.refresh(review)
        review_task_id = review.id
    else:
        db.commit()
    update_mastery_from_answer(
        db,
        quiz.project_id,
        user.id,
        quiz.knowledge_point_id,
        quiz.lesson_id,
        graded["is_correct"],
    )
    db.commit()

    return AnswerResult(
        is_correct=graded["is_correct"],
        feedback=graded["feedback"],
        explanation=quiz.explanation,
        review_task_id=review_task_id,
    )

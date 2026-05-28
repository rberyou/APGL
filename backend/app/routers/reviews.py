from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import QuizItem, ReviewTask, User, utc_now
from app.schemas import AnswerResult, ReviewSubmit, ReviewTaskRead
from app.services.ai import AIServiceError
from app.services.ai import grade_answer


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/today", response_model=list[ReviewTaskRead])
def today_reviews(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    tasks = db.exec(
        select(ReviewTask)
        .where(ReviewTask.user_id == user.id)
        .where(ReviewTask.status == "pending")
        .where(ReviewTask.due_at <= utc_now())
        .order_by(ReviewTask.due_at)
    ).all()
    result: list[ReviewTaskRead] = []
    for task in tasks:
        quiz = db.get(QuizItem, task.quiz_item_id)
        if quiz:
            result.append(
                ReviewTaskRead(
                    id=task.id,
                    quiz_item_id=task.quiz_item_id,
                    prompt=quiz.prompt,
                    due_at=task.due_at,
                    status=task.status,
                )
            )
    return result


@router.post("/{review_id}/submit", response_model=AnswerResult)
def submit_review(
    review_id: int,
    payload: ReviewSubmit,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    task = db.get(ReviewTask, review_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Review task not found")
    quiz = db.get(QuizItem, task.quiz_item_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz item not found")

    try:
        graded = grade_answer(quiz.prompt, quiz.answer, payload.answer)
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if graded["is_correct"]:
        task.status = "completed"
        next_review_id = None
    else:
        task.status = "completed"
        next_task = ReviewTask(
            user_id=user.id,
            quiz_item_id=quiz.id,
            mistake_id=task.mistake_id,
            due_at=utc_now() + timedelta(days=1),
        )
        db.add(next_task)
        db.commit()
        db.refresh(next_task)
        next_review_id = next_task.id
    db.add(task)
    db.commit()
    return AnswerResult(
        is_correct=graded["is_correct"],
        feedback=graded["feedback"],
        explanation=quiz.explanation,
        review_task_id=next_review_id,
    )

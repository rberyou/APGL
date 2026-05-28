from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import MistakeRecord, QuizItem, User
from app.schemas import MistakeRead


router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("", response_model=list[MistakeRead])
def list_mistakes(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    mistakes = db.exec(
        select(MistakeRecord)
        .where(MistakeRecord.user_id == user.id)
        .order_by(MistakeRecord.created_at.desc())
    ).all()
    result: list[MistakeRead] = []
    for mistake in mistakes:
        quiz = db.get(QuizItem, mistake.quiz_item_id)
        if quiz:
            result.append(
                MistakeRead(
                    id=mistake.id,
                    quiz_item_id=mistake.quiz_item_id,
                    prompt=quiz.prompt,
                    user_answer=mistake.user_answer,
                    reason=mistake.reason,
                    status=mistake.status,
                    created_at=mistake.created_at,
                )
            )
    return result

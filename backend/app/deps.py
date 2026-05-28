from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User, UserSession, utc_now


def get_current_user(
    request: Request, db: Session = Depends(get_session)
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    session_row = db.get(UserSession, token)
    if not session_row or session_row.expires_at <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    user = db.exec(select(User).where(User.id == session_row.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

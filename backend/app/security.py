from datetime import timedelta
import secrets

from passlib.context import CryptContext
from sqlmodel import Session

from app.config import settings
from app.models import UserSession, utc_now


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_session(session: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(days=settings.session_days)
    session.add(UserSession(id=token, user_id=user_id, expires_at=expires_at))
    session.commit()
    return token


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(key=settings.session_cookie_name)

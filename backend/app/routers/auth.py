from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.deps import get_current_user
from app.models import User, UserSession
from app.schemas import AuthRequest, UserRead
from app.security import (
    clear_session_cookie,
    create_session,
    hash_password,
    set_session_cookie,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="A valid email is required")
    return normalized


@router.post("/register", response_model=UserRead)
def register(payload: AuthRequest, response: Response, db: Session = Depends(get_session)):
    email = _normalize_email(payload.email)
    existing = db.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session(db, user.id)
    set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserRead)
def login(payload: AuthRequest, response: Response, db: Session = Depends(get_session)):
    email = _normalize_email(payload.email)
    user = db.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_session(db, user.id)
    set_session_cookie(response, token)
    return user


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session)):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session_row = db.get(UserSession, token)
        if session_row:
            db.delete(session_row)
            db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user



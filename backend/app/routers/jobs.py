from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import Job, User
from app.schemas import JobRead


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/projects/{project_id}/latest", response_model=JobRead)
def get_latest_project_job(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    job = db.exec(
        select(Job)
        .where(Job.project_id == project_id)
        .where(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

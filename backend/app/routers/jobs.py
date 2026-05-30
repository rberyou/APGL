from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import Job, JobStage, User
from app.schemas import JobDetailRead, JobRead
from app.services.jobs import process_generation_job, resume_job, retry_job


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobDetailRead)
def get_job(
    job_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_payload(db, job)


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


@router.post("/{job_id}/retry", response_model=JobRead)
def retry_generation_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        new_job = retry_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(process_generation_job, new_job.id)
    return new_job


@router.post("/{job_id}/resume", response_model=JobRead)
def resume_generation_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        new_job = resume_job(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(process_generation_job, new_job.id)
    return new_job


def _job_payload(db: Session, job: Job) -> dict:
    stages = db.exec(
        select(JobStage).where(JobStage.job_id == job.id).order_by(JobStage.order_index)
    ).all()
    data = JobRead.model_validate(job).model_dump()
    data["stages"] = stages
    return data

import hashlib
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models import Job, LearningProject, LessonUnit, SourceMaterial, User, utc_now
from app.schemas import ProjectCreate, ProjectCreateResponse, ProjectRead
from app.services.jobs import create_job, process_material_job, process_skill_job
from app.services.learning import ensure_project_state
from app.routers.materials import _store_upload, _format_upload_limit
from app.config import settings


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    return db.exec(
        select(LearningProject)
        .where(LearningProject.user_id == user.id)
        .order_by(LearningProject.created_at.desc())
    ).all()


@router.post("", response_model=ProjectCreateResponse)
def create_project(
    payload: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = LearningProject(
        user_id=user.id,
        title=payload.title.strip(),
        goal=payload.goal.strip(),
        source_type=payload.source_type,
        current_level=payload.current_level,
        time_budget_minutes=payload.time_budget_minutes,
        status="generating" if payload.source_type == "skill" else "active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    ensure_project_state(db, project)

    job_id = None
    if payload.source_type == "skill":
        job = create_job(db, user.id, project.id, "skill_plan_generation")
        job_id = job.id
        background_tasks.add_task(process_skill_job, job.id)
    return ProjectCreateResponse(project=project, job_id=job_id)


@router.post("/material", response_model=ProjectCreateResponse)
async def create_material_project(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    goal: str = Form(...),
    current_level: str | None = Form(default=None),
    time_budget_minutes: int | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum upload size is {_format_upload_limit(settings.max_upload_bytes)}.",
        )
    filename = file.filename or "material.txt"
    if Path(filename).suffix.lower() not in {".pdf", ".md", ".markdown", ".txt"}:
        raise HTTPException(status_code=400, detail="Only PDF, Markdown, and text files are supported")
    project = LearningProject(
        user_id=user.id,
        title=title.strip(),
        goal=goal.strip(),
        source_type="material",
        current_level=current_level,
        time_budget_minutes=time_budget_minutes,
        status="generating",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    ensure_project_state(db, project)
    storage_path = _store_upload(project.id, filename, data)
    material = SourceMaterial(
        project_id=project.id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        raw_text="",
        status="uploaded",
        storage_path=str(storage_path),
        file_checksum=hashlib.sha256(data).hexdigest(),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    job = create_job(db, user.id, project.id, "material_plan_generation", material.id)
    background_tasks.add_task(process_material_job, job.id)
    db.refresh(project)
    return ProjectCreateResponse(project=project, job_id=job.id)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = db.get(LearningProject, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/generate", response_model=ProjectCreateResponse)
def generate_project_lessons(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = db.get(LearningProject, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_lessons = db.exec(
        select(LessonUnit).where(LessonUnit.project_id == project.id)
    ).first()
    if existing_lessons:
        raise HTTPException(status_code=409, detail="This project already has lessons")

    running_job = db.exec(
        select(Job)
        .where(Job.project_id == project.id)
        .where(Job.status.in_(["pending", "processing"]))
        .order_by(Job.created_at.desc())
    ).first()
    if running_job:
        return ProjectCreateResponse(project=project, job_id=running_job.id)

    material_id = None
    job_type = "skill_plan_generation"
    processor = process_skill_job
    if project.source_type == "material":
        material = db.exec(
            select(SourceMaterial)
            .where(SourceMaterial.project_id == project.id)
            .order_by(SourceMaterial.created_at.desc())
        ).first()
        if not material:
            raise HTTPException(
                status_code=400,
                detail="Upload a material file before generating lessons",
            )
        material_id = material.id
        job_type = "material_plan_generation"
        processor = process_material_job

    project.status = "generating"
    project.updated_at = utc_now()
    db.add(project)
    db.commit()
    db.refresh(project)

    job = create_job(db, user.id, project.id, job_type, material_id)
    background_tasks.add_task(processor, job.id)
    return ProjectCreateResponse(project=project, job_id=job.id)

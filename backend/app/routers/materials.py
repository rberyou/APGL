from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.deps import get_current_user
from app.models import LearningProject, SourceMaterial, User
from app.schemas import MaterialUploadResponse
from app.services.jobs import create_job, process_material_job
from app.services.materials import extract_text


router = APIRouter(prefix="/projects/{project_id}/materials", tags=["materials"])


@router.post("", response_model=MaterialUploadResponse)
async def upload_material(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = db.get(LearningProject, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File is too large")

    try:
        text = extract_text(file.filename or "material.txt", file.content_type or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not text:
        raise HTTPException(status_code=400, detail="No readable text found")

    material = SourceMaterial(
        project_id=project.id,
        filename=file.filename or "material.txt",
        content_type=file.content_type or "application/octet-stream",
        raw_text=text,
        status="uploaded",
    )
    db.add(material)
    project.status = "generating"
    db.add(project)
    db.commit()
    db.refresh(material)

    job = create_job(db, user.id, project.id, "material_plan_generation", material.id)
    background_tasks.add_task(process_material_job, job.id)
    return MaterialUploadResponse(material=material, job_id=job.id)


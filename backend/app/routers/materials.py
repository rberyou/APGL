from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.deps import get_current_user
from app.models import LearningProject, SourceMaterial, User
from app.schemas import MaterialStatus, MaterialUploadResponse
from app.services.jobs import create_job, process_material_job
from app.services.materials import extract_material


router = APIRouter(prefix="/projects/{project_id}/materials", tags=["materials"])


def _format_upload_limit(bytes_count: int) -> str:
    return f"{bytes_count / 1024 / 1024:.0f} MB"


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
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum upload size is {_format_upload_limit(settings.max_upload_bytes)}.",
        )

    try:
        parsed = extract_material(file.filename or "material.txt", file.content_type or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not parsed.text:
        raise HTTPException(
            status_code=400,
            detail="No readable text found. Scanned PDFs and OCR are not supported in this version.",
        )

    material = SourceMaterial(
        project_id=project.id,
        filename=file.filename or "material.txt",
        content_type=file.content_type or "application/octet-stream",
        raw_text=parsed.text,
        status="uploaded",
        page_count=parsed.page_count,
        text_page_count=parsed.text_page_count,
        character_count=parsed.character_count,
    )
    db.add(material)
    project.status = "generating"
    db.add(project)
    db.commit()
    db.refresh(material)

    job = create_job(db, user.id, project.id, "material_plan_generation", material.id)
    background_tasks.add_task(process_material_job, job.id)
    return MaterialUploadResponse(material=material, job_id=job.id)


@router.get("/status", response_model=MaterialStatus)
def material_status(
    project_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    project = db.get(LearningProject, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    material = db.exec(
        select(SourceMaterial)
        .where(SourceMaterial.project_id == project_id)
        .order_by(SourceMaterial.created_at.desc())
    ).first()
    if not material:
        return MaterialStatus(
            project_id=project_id,
            material_id=None,
            filename=None,
            status="missing",
            page_count=0,
            text_page_count=0,
            character_count=0,
            chunk_count=0,
            readable=False,
            message="No material has been uploaded for this learning space.",
        )
    readable = material.character_count > 0 and material.chunk_count > 0
    message = (
        f"Parsed {material.chunk_count} chunks from {material.character_count} characters."
        if readable
        else "Material uploaded, but no searchable chunks are ready yet."
    )
    return MaterialStatus(
        project_id=project_id,
        material_id=material.id,
        filename=material.filename,
        status=material.status,
        page_count=material.page_count,
        text_page_count=material.text_page_count,
        character_count=material.character_count,
        chunk_count=material.chunk_count,
        readable=readable,
        message=message,
    )

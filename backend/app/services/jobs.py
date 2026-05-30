from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, delete, select

from app.database import engine
from app.models import (
    GenerationArtifact,
    Job,
    JobStage,
    KnowledgeEdge,
    KnowledgePoint,
    LearningProject,
    LessonKnowledgePoint,
    LessonStep,
    LessonUnit,
    QuizItem,
    SourceCitation,
    SourceChunk,
    SourceMaterial,
    utc_now,
)
from app.services.ai import (
    generate_knowledge_map,
    generate_lesson_content,
    generate_lesson_plan,
    generate_material_plan,
    generate_project_brief,
    generate_skill_plan,
)
from app.services.learning import ensure_project_state, refresh_project_mastery
from app.services.materials import chunk_text, extract_material
from app.services.retrieval import clear_project_index, index_source_chunks, search_project_chunks


PROMPT_VERSION = "v2.0"
SCHEMA_VERSION = "v2.0"

STAGES = [
    ("understand_goal", "Understand learning goal"),
    ("parse_material", "Parse learning material"),
    ("build_source_index", "Build source index"),
    ("project_brief", "Create project brief"),
    ("knowledge_map", "Build knowledge map"),
    ("lesson_plan", "Plan tutor learning path"),
    ("prepare_first_lesson", "Prepare first lesson"),
    ("ready", "Ready"),
]


def create_job(
    db: Session,
    user_id: int,
    project_id: int,
    job_type: str,
    material_id: int | None = None,
    retry_of_job_id: int | None = None,
    resumed_from_job_id: int | None = None,
) -> Job:
    existing = db.exec(
        select(Job)
        .where(Job.project_id == project_id)
        .where(Job.status.in_(["pending", "processing"]))
        .order_by(Job.created_at.desc())
    ).first()
    if existing:
        return existing
    job = Job(
        user_id=user_id,
        project_id=project_id,
        material_id=material_id,
        job_type=job_type,
        retry_of_job_id=retry_of_job_id,
        resumed_from_job_id=resumed_from_job_id,
        stage_key="understand_goal",
        stage_label="Understand learning goal",
        message="Generation is queued.",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _ensure_stages(db, job)
    return job


def process_skill_job(job_id: int) -> None:
    process_generation_job(job_id)


def process_material_job(job_id: int) -> None:
    process_generation_job(job_id)


def process_lesson_prepare_job(job_id: int, lesson_id: int | None = None) -> None:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            return
        try:
            _set_job_status(db, job, "processing", message="Preparing lesson content.")
            _ensure_stages(db, job, only_lesson_prepare=True)
            project = _project(db, job)
            lesson = db.get(LessonUnit, lesson_id) if lesson_id else _first_unprepared_lesson(db, project.id)
            if not lesson:
                raise ValueError("No lesson needs preparation.")
            _run_stage(db, job, "prepare_first_lesson", lambda: _stage_prepare_lesson(db, job, project, lesson))
            _run_stage(db, job, "ready", lambda: _stage_ready(db, job, project))
        except Exception as exc:
            _fail_job(db, job, str(exc), job.stage_key)


def process_generation_job(job_id: int) -> None:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            return
        try:
            _set_job_status(db, job, "processing", message="Starting staged generation.")
            _ensure_stages(db, job)
            project = _project(db, job)
            project.status = "generating"
            project.updated_at = utc_now()
            db.add(project)
            db.commit()

            _run_stage(db, job, "understand_goal", lambda: _stage_understand_goal(db, job, project))
            if project.source_type == "material":
                _run_stage(db, job, "parse_material", lambda: _stage_parse_material(db, job, project))
                _run_stage(db, job, "build_source_index", lambda: _stage_build_source_index(db, job, project))
            else:
                _skip_stage(
                    db,
                    job,
                    "parse_material",
                    "No source material was uploaded. APGL will start from the learning goal and the configured LLM's model knowledge.",
                )
                _skip_stage(db, job, "build_source_index", "No source index is needed for a skill-goal project.")

            _run_stage(db, job, "project_brief", lambda: _stage_project_brief(db, job, project))
            _run_stage(db, job, "knowledge_map", lambda: _stage_knowledge_map(db, job, project))
            _run_stage(db, job, "lesson_plan", lambda: _stage_lesson_plan(db, job, project))
            first = _first_unprepared_lesson(db, project.id) or db.exec(
                select(LessonUnit)
                .where(LessonUnit.project_id == project.id)
                .order_by(LessonUnit.order_index)
            ).first()
            if first:
                _run_stage(db, job, "prepare_first_lesson", lambda: _stage_prepare_lesson(db, job, project, first))
            _run_stage(db, job, "ready", lambda: _stage_ready(db, job, project))
            _set_job_status(db, job, "completed", message="Learning space is ready.", progress=100)
        except Exception as exc:
            _set_project_status(db, job.project_id, "failed")
            _fail_job(db, job, str(exc), job.stage_key)


def retry_job(db: Session, job: Job) -> Job:
    if job.status not in {"failed", "interrupted"}:
        raise ValueError("Only failed or interrupted jobs can be continued.")
    _assert_no_running_job(db, job.project_id)
    new_job = create_job(
        db,
        job.user_id,
        job.project_id,
        job.job_type,
        job.material_id,
        retry_of_job_id=job.id,
    )
    return new_job


def resume_job(db: Session, job: Job) -> Job:
    if job.status == "processing":
        job.status = "interrupted"
        job.updated_at = utc_now()
        db.add(job)
        db.commit()
    if job.status not in {"failed", "interrupted"}:
        raise ValueError("Only failed or interrupted jobs can be continued.")
    _assert_no_running_job(db, job.project_id)
    new_job = create_job(
        db,
        job.user_id,
        job.project_id,
        job.job_type,
        job.material_id,
        resumed_from_job_id=job.id,
    )
    return new_job


def prepare_lesson_job(db: Session, user_id: int, lesson: LessonUnit) -> Job:
    existing = db.exec(
        select(Job)
        .where(Job.project_id == lesson.project_id)
        .where(Job.job_type == "lesson_content_generation")
        .where(Job.status.in_(["pending", "processing"]))
        .order_by(Job.created_at.desc())
    ).first()
    if existing:
        return existing
    return create_job(db, user_id, lesson.project_id, "lesson_content_generation")


def _ensure_stages(db: Session, job: Job, only_lesson_prepare: bool = False) -> None:
    existing = {
        stage.stage_key
        for stage in db.exec(select(JobStage).where(JobStage.job_id == job.id)).all()
    }
    stages = [item for item in STAGES if not only_lesson_prepare or item[0] in {"prepare_first_lesson", "ready"}]
    for index, (key, label) in enumerate(stages, start=1):
        if key not in existing:
            db.add(
                JobStage(
                    job_id=job.id,
                    project_id=job.project_id,
                    stage_key=key,
                    label=label,
                    order_index=index,
                    message="Pending",
                )
            )
    db.commit()


def _stage(db: Session, job: Job, key: str) -> JobStage:
    stage = db.exec(
        select(JobStage).where(JobStage.job_id == job.id).where(JobStage.stage_key == key)
    ).one()
    return stage


def _run_stage(db: Session, job: Job, key: str, fn) -> None:
    stage = _stage(db, job, key)
    if stage.status in {"completed", "skipped"}:
        return
    stage.status = "running"
    stage.started_at = stage.started_at or utc_now()
    stage.updated_at = utc_now()
    stage.error = None
    db.add(stage)
    _set_job_status(
        db,
        job,
        "processing",
        stage_key=stage.stage_key,
        stage_label=stage.label,
        message=stage.label,
        progress=_stage_progress(stage.order_index - 1),
    )
    try:
        message, details = fn()
    except Exception as exc:
        stage.status = "failed"
        stage.error = str(exc)
        stage.message = "Failed"
        stage.updated_at = utc_now()
        db.add(stage)
        db.commit()
        raise
    stage.status = "completed"
    stage.message = message
    stage.details_json = json.dumps(details or {}, ensure_ascii=False)
    stage.completed_at = utc_now()
    stage.updated_at = stage.completed_at
    db.add(stage)
    _set_job_status(
        db,
        job,
        "processing",
        stage_key=stage.stage_key,
        stage_label=stage.label,
        message=message,
        progress=_stage_progress(stage.order_index),
    )


def _skip_stage(db: Session, job: Job, key: str, message: str) -> None:
    stage = _stage(db, job, key)
    if stage.status == "skipped":
        return
    now = utc_now()
    stage.status = "skipped"
    stage.message = message
    stage.started_at = stage.started_at or now
    stage.completed_at = now
    stage.updated_at = now
    db.add(stage)
    db.commit()


def _stage_understand_goal(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    ensure_project_state(db, project)
    return "Learning space created.", {"source_type": project.source_type, "title": project.title}


def _stage_parse_material(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    material = _material(db, job, project)
    if not material.storage_path:
        raise ValueError("Uploaded material file is missing from local storage.")
    data = Path(material.storage_path).read_bytes()
    try:
        parsed = extract_material(material.filename, material.content_type, data)
    except ValueError as exc:
        material.status = "failed"
        material.error = str(exc)
        db.add(material)
        db.commit()
        raise
    if not parsed.text:
        message = "No readable text was extracted. Scanned PDFs require OCR, which is not supported yet."
        material.status = "failed"
        material.error = message
        db.add(material)
        db.commit()
        raise ValueError(message)
    material.raw_text = parsed.text
    material.page_count = parsed.page_count
    material.text_page_count = parsed.text_page_count
    material.character_count = parsed.character_count
    material.status = "parsed"
    material.error = None
    db.add(material)
    db.commit()
    return (
        f"{material.filename}, {material.page_count} pages, {material.text_page_count} text pages",
        {"character_count": material.character_count},
    )


def _stage_build_source_index(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    material = _material(db, job, project)
    chunks = chunk_text(material.raw_text)
    if not chunks:
        raise ValueError("No readable text was extracted. Scanned PDFs require OCR, which is not supported yet.")
    db.exec(delete(SourceCitation).where(SourceCitation.project_id == project.id))
    db.exec(delete(SourceChunk).where(SourceChunk.project_id == project.id))
    clear_project_index(db, project.id)
    db.commit()
    rows: list[SourceChunk] = []
    for item in chunks:
        row = SourceChunk(
            project_id=project.id,
            material_id=material.id,
            position=int(item["position"]),
            title=str(item["title"]),
            content=str(item["content"]),
            locator=str(item["locator"]),
        )
        db.add(row)
        rows.append(row)
    material.status = "processed"
    material.chunk_count = len(rows)
    material.character_count = len(material.raw_text)
    material.error = None
    db.add(material)
    db.commit()
    for row in rows:
        db.refresh(row)
    index_source_chunks(db, rows)
    db.commit()
    return f"{len(rows)} chunks indexed.", {"chunk_count": len(rows)}


def _stage_project_brief(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    input_hash = _input_hash(project, "project_brief", _material_checksum(db, job))
    artifact = _active_artifact(db, project.id, "project_brief", input_hash)
    if artifact:
        data = json.loads(artifact.content_json)
    else:
        data = generate_project_brief(
            project.title,
            project.goal,
            project.source_type,
            project.current_level,
            _material_excerpt(db, project.id),
        )
        _store_artifact(db, job, "project_brief", "project_brief", input_hash, data)
    return str(data.get("recommended_strategy") or "Project brief created.")[:240], data


def _stage_knowledge_map(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    brief = _artifact_json(db, project.id, "project_brief") or {}
    context_chunks = [_chunk_context(chunk) for chunk in _project_chunks(db, project.id, limit=8)]
    input_hash = _input_hash(project, "knowledge_map", _artifact_hash(db, project.id, "project_brief"), _material_checksum(db, job))
    artifact = _active_artifact(db, project.id, "knowledge_map", input_hash)
    data = json.loads(artifact.content_json) if artifact else generate_knowledge_map(
        project.title, project.goal, brief, project.source_type, context_chunks
    )
    _replace_knowledge_map(db, project, data)
    if not artifact:
        _store_artifact(db, job, "knowledge_map", "knowledge_map", input_hash, data)
    count = len(data.get("knowledge_points") or [])
    return f"Identified {count} knowledge points.", {"knowledge_points": count}


def _stage_lesson_plan(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    brief = _artifact_json(db, project.id, "project_brief") or {}
    points = _saved_kp_payload(db, project.id)
    input_hash = _input_hash(project, "lesson_plan", _artifact_hash(db, project.id, "knowledge_map"))
    artifact = _active_artifact(db, project.id, "lesson_plan", input_hash)
    data = json.loads(artifact.content_json) if artifact else generate_lesson_plan(
        project.title, project.goal, brief, points
    )
    details = _replace_lesson_plan(db, project, data)
    if not artifact:
        _store_artifact(db, job, "lesson_plan", "lesson_plan", input_hash, data)
    return f"Planned {details['lesson_count']} lessons.", details


def _stage_prepare_lesson(db: Session, job: Job, project: LearningProject, lesson: LessonUnit) -> tuple[str, dict]:
    kps = _lesson_kp_payload(db, lesson.id)
    chunks = [_chunk_payload(chunk) for chunk in _context_for_lesson(db, project.id, lesson, kps)]
    input_hash = _input_hash(project, f"lesson_content:{lesson.id}", _artifact_hash(db, project.id, "lesson_plan"))
    artifact = _active_artifact(db, project.id, f"lesson_content:{lesson.id}", input_hash)
    data = json.loads(artifact.content_json) if artifact else generate_lesson_content(
        lesson.title, lesson.summary, project.goal, kps, chunks
    )
    lesson.content = str(data.get("tutor_explanation") or "")
    lesson.status = "ready" if lesson.content else "pending"
    db.add(lesson)
    db.exec(delete(LessonStep).where(LessonStep.lesson_id == lesson.id))
    db.exec(delete(SourceCitation).where(SourceCitation.lesson_id == lesson.id))
    _create_lesson_steps(db, lesson, data)
    for citation in data.get("source_citations") or []:
        chunk_id = citation.get("source_chunk_id")
        if chunk_id and db.get(SourceChunk, int(chunk_id)):
            db.add(
                SourceCitation(
                    project_id=project.id,
                    source_chunk_id=int(chunk_id),
                    lesson_id=lesson.id,
                    label=str(citation.get("label") or "Source"),
                    excerpt=str(citation.get("excerpt") or "")[:500],
                )
            )
    db.commit()
    if not artifact:
        _store_artifact(db, job, f"lesson_content:{lesson.id}", "lesson_content", input_hash, data)
    return f"Prepared {lesson.title}.", {"lesson_id": lesson.id}


def _stage_ready(db: Session, job: Job, project: LearningProject) -> tuple[str, dict]:
    ensure_project_state(db, project)
    refresh_project_mastery(db, project.id)
    project = db.get(LearningProject, project.id)
    if project:
        project.status = "active"
        project.updated_at = utc_now()
        db.add(project)
        db.commit()
    return "Ready to learn.", {"project_id": project.id if project else job.project_id}


def _replace_knowledge_map(db: Session, project: LearningProject, data: dict[str, Any]) -> None:
    db.exec(delete(KnowledgeEdge).where(KnowledgeEdge.project_id == project.id))
    db.exec(delete(LessonKnowledgePoint).where(LessonKnowledgePoint.project_id == project.id))
    db.exec(delete(QuizItem).where(QuizItem.project_id == project.id))
    db.exec(delete(LessonStep).where(LessonStep.project_id == project.id))
    db.exec(delete(LessonUnit).where(LessonUnit.project_id == project.id))
    db.exec(delete(KnowledgePoint).where(KnowledgePoint.project_id == project.id))
    db.commit()
    items = [item for item in (data.get("knowledge_points") or []) if isinstance(item, dict)]
    if not items:
        raise ValueError("The LLM did not return any knowledge points.")
    weights = _normalized_weights(items)
    key_to_row: dict[str, KnowledgePoint] = {}
    for index, item in enumerate(items, start=1):
        key = str(item.get("client_key") or _slug(item.get("name") or f"point-{index}", index))[:120]
        row = KnowledgePoint(
            project_id=project.id,
            client_key=key,
            name=str(item.get("name") or item.get("title") or f"Knowledge point {index}")[:160],
            explanation=str(item.get("explanation") or item.get("description") or ""),
            difficulty=str(item.get("difficulty") or "core")[:40],
            estimated_weight=weights[index - 1],
            source_locator=str(item.get("source_locator") or "")[:160] or None,
        )
        db.add(row)
        key_to_row[key] = row
    db.commit()
    for row in key_to_row.values():
        db.refresh(row)
    invalid_edges = 0
    for edge in data.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        source = key_to_row.get(str(edge.get("source_client_key") or ""))
        target = key_to_row.get(str(edge.get("target_client_key") or ""))
        if not source or not target:
            invalid_edges += 1
            continue
        db.add(
            KnowledgeEdge(
                project_id=project.id,
                source_id=source.id,
                target_id=target.id,
                relation_type=str(edge.get("relation_type") or "related_to")[:40],
            )
        )
    db.commit()


def _replace_lesson_plan(db: Session, project: LearningProject, data: dict[str, Any]) -> dict[str, Any]:
    points = db.exec(select(KnowledgePoint).where(KnowledgePoint.project_id == project.id)).all()
    by_key = {point.client_key: point for point in points if point.client_key}
    db.exec(delete(LessonKnowledgePoint).where(LessonKnowledgePoint.project_id == project.id))
    db.exec(delete(QuizItem).where(QuizItem.project_id == project.id))
    db.exec(delete(SourceCitation).where(SourceCitation.project_id == project.id).where(SourceCitation.tutor_message_id == None))  # noqa: E711
    db.exec(delete(LessonStep).where(LessonStep.project_id == project.id))
    db.exec(delete(LessonUnit).where(LessonUnit.project_id == project.id))
    db.commit()
    items = [item for item in (data.get("lessons") or []) if isinstance(item, dict)]
    if not items:
        raise ValueError("The LLM did not return any lessons.")
    lesson_rows: list[LessonUnit] = []
    for index, item in enumerate(items[:8], start=1):
        lesson = LessonUnit(
            project_id=project.id,
            title=str(item.get("title") or f"Lesson {index}")[:200],
            summary=str(item.get("summary") or ""),
            content="",
            order_index=int(item.get("order_index") or index),
            status="pending",
        )
        db.add(lesson)
        lesson_rows.append(lesson)
    db.commit()
    for row in lesson_rows:
        db.refresh(row)
    mapped: set[int] = set()
    fallbacks: list[str] = []
    for index, (lesson, item) in enumerate(zip(lesson_rows, items), start=1):
        keys = [str(key) for key in (item.get("covered_knowledge_client_keys") or [])]
        selected = [by_key[key] for key in keys if key in by_key]
        if not selected and points:
            selected = [_best_point_for_lesson(points, lesson)]
            fallbacks.append(lesson.title)
        for order, point in enumerate(selected, start=1):
            if _has_mapping(db, lesson.id, point.id):
                continue
            db.add(
                LessonKnowledgePoint(
                    lesson_id=lesson.id,
                    knowledge_point_id=point.id,
                    project_id=project.id,
                    coverage_role="primary" if point.id not in mapped else "supporting",
                    order_index=order,
                )
            )
            mapped.add(point.id)
    for point in points:
        if point.id in mapped:
            continue
        lesson = _best_lesson_for_point(lesson_rows, point) or lesson_rows[-1]
        db.add(
            LessonKnowledgePoint(
                lesson_id=lesson.id,
                knowledge_point_id=point.id,
                project_id=project.id,
                coverage_role="primary",
                order_index=len(mapped) + 1,
            )
        )
        mapped.add(point.id)
        fallbacks.append(f"{point.name} -> {lesson.title}")
    db.commit()
    if points and len(mapped) < len(points):
        raise ValueError("No complete lesson-to-knowledge mapping could be formed.")
    return {"lesson_count": len(lesson_rows), "fallback_mappings": fallbacks}


def _create_lesson_steps(db: Session, lesson: LessonUnit, data: dict[str, Any]) -> None:
    examples = "\n".join(f"- {item}" for item in _string_list(data.get("examples"))[:4])
    practice = "\n".join(
        f"- {item}" for item in _string_list(data.get("practice_suggestions"))[:4]
    )
    steps = [
        ("orient", "Set the target", lesson.summary or "Clarify what this lesson is for."),
        ("explain", "Tutor explanation", lesson.content or "Ask the tutor to prepare this lesson."),
        ("practice", "Practice suggestions", practice or examples or "Ask the tutor for one applied challenge."),
    ]
    for index, (step_type, title, body) in enumerate(steps, start=1):
        db.add(
            LessonStep(
                lesson_id=lesson.id,
                project_id=lesson.project_id,
                step_type=step_type,
                title=title,
                body=body,
                order_index=index,
            )
        )


def _store_plan(
    db: Session,
    project: LearningProject,
    plan: dict,
    source_chunks: list[SourceChunk] | None = None,
) -> None:
    """Compatibility helper used by older tests and recovery paths."""
    data = {
        "knowledge_points": [
            {
                "client_key": _slug(str(item.get("name") or item.get("title") or item), index)
                if isinstance(item, dict)
                else _slug(str(item), index),
                "name": str(item.get("name") or item.get("title") or item) if isinstance(item, dict) else str(item),
                "explanation": str(item.get("explanation") or item.get("description") or "")
                if isinstance(item, dict)
                else "",
                "difficulty": "core",
                "estimated_weight": 1,
                "source_locator": source_chunks[0].locator if source_chunks else None,
            }
            for index, item in enumerate((plan.get("knowledge_points") or [])[:8], start=1)
        ],
        "edges": [],
    }
    if not data["knowledge_points"]:
        data["knowledge_points"] = [
            {
                "client_key": "core-idea",
                "name": project.title,
                "explanation": project.goal,
                "difficulty": "core",
                "estimated_weight": 1,
            }
        ]
    _replace_knowledge_map(db, project, data)
    lesson_data = {"lessons": []}
    for index, item in enumerate((plan.get("lessons") or [])[:8], start=1):
        if not isinstance(item, dict):
            item = {"title": f"Lesson {index}", "summary": str(item), "content": str(item)}
        lesson_data["lessons"].append(
            {
                "title": str(item.get("title") or f"Lesson {index}"),
                "summary": str(item.get("summary") or ""),
                "order_index": index,
                "covered_knowledge_client_keys": [
                    data["knowledge_points"][(index - 1) % len(data["knowledge_points"])]["client_key"]
                ],
            }
        )
    if not lesson_data["lessons"]:
        raise ValueError("The LLM did not return any lessons. Please regenerate the learning path.")
    _replace_lesson_plan(db, project, lesson_data)
    first = db.exec(select(LessonUnit).where(LessonUnit.project_id == project.id).order_by(LessonUnit.order_index)).first()
    if first:
        first.content = str((plan.get("lessons") or [{}])[0].get("content") or first.summary)
        first.status = "ready"
        db.add(first)
    project.status = "active"
    project.updated_at = utc_now()
    db.add(project)
    db.commit()
    ensure_project_state(db, project)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if not isinstance(value, list):
        value = [value]
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = item.get("activity") or item.get("title") or item.get("instructions") or item
            if isinstance(text, dict):
                text = json.dumps(text, ensure_ascii=False)
        else:
            text = item
        cleaned = str(text).strip()
        if cleaned:
            result.append(cleaned)
    return result


def _active_artifact(db: Session, project_id: int, stage_key: str, input_hash: str) -> GenerationArtifact | None:
    return db.exec(
        select(GenerationArtifact)
        .where(GenerationArtifact.project_id == project_id)
        .where(GenerationArtifact.stage_key == stage_key)
        .where(GenerationArtifact.input_hash == input_hash)
        .where(GenerationArtifact.status == "active")
        .order_by(GenerationArtifact.created_at.desc())
    ).first()


def _store_artifact(
    db: Session,
    job: Job,
    stage_key: str,
    artifact_type: str,
    input_hash: str,
    content: dict[str, Any],
) -> None:
    for old in db.exec(
        select(GenerationArtifact)
        .where(GenerationArtifact.project_id == job.project_id)
        .where(GenerationArtifact.stage_key == stage_key)
        .where(GenerationArtifact.status == "active")
    ).all():
        old.status = "superseded"
        old.updated_at = utc_now()
        db.add(old)
    db.add(
        GenerationArtifact(
            project_id=job.project_id,
            job_id=job.id,
            material_id=job.material_id,
            stage_key=stage_key,
            artifact_type=artifact_type,
            input_hash=input_hash,
            schema_version=SCHEMA_VERSION,
            prompt_version=PROMPT_VERSION,
            content_json=json.dumps(content, ensure_ascii=False),
        )
    )
    db.commit()


def _artifact_json(db: Session, project_id: int, artifact_type: str) -> dict[str, Any] | None:
    artifact = db.exec(
        select(GenerationArtifact)
        .where(GenerationArtifact.project_id == project_id)
        .where(GenerationArtifact.artifact_type == artifact_type)
        .where(GenerationArtifact.status == "active")
        .order_by(GenerationArtifact.created_at.desc())
    ).first()
    return json.loads(artifact.content_json) if artifact else None


def _artifact_hash(db: Session, project_id: int, artifact_type: str) -> str:
    data = _artifact_json(db, project_id, artifact_type) or {}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _input_hash(project: LearningProject, stage_key: str, *extra: str | None) -> str:
    payload = {
        "project": {
            "title": project.title,
            "goal": project.goal,
            "source_type": project.source_type,
            "current_level": project.current_level,
            "time_budget_minutes": project.time_budget_minutes,
        },
        "stage_key": stage_key,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "extra": [item for item in extra if item],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _set_job_status(
    db: Session,
    job: Job,
    status: str,
    error: str | None = None,
    stage_key: str | None = None,
    stage_label: str | None = None,
    message: str | None = None,
    progress: int | None = None,
) -> None:
    job.status = status
    job.error = error
    if stage_key is not None:
        job.stage_key = stage_key
    if stage_label is not None:
        job.stage_label = stage_label
    if message is not None:
        job.message = message
    if progress is not None:
        job.progress_percent = progress
    job.updated_at = utc_now()
    db.add(job)
    db.commit()
    db.refresh(job)


def _fail_job(db: Session, job: Job, error: str, stage_key: str | None) -> None:
    job.status = "failed"
    job.error = error
    job.error_stage = stage_key
    job.message = error
    job.updated_at = utc_now()
    db.add(job)
    db.commit()


def _set_project_status(db: Session, project_id: int, status: str) -> None:
    project = db.get(LearningProject, project_id)
    if project:
        project.status = status
        project.updated_at = utc_now()
        db.add(project)
        db.commit()


def _assert_no_running_job(db: Session, project_id: int) -> None:
    running = db.exec(
        select(Job)
        .where(Job.project_id == project_id)
        .where(Job.status.in_(["pending", "processing"]))
    ).first()
    if running:
        raise ValueError("Another generation job is already running for this project.")


def _project(db: Session, job: Job) -> LearningProject:
    project = db.get(LearningProject, job.project_id)
    if not project:
        raise ValueError("Project not found")
    return project


def _material(db: Session, job: Job, project: LearningProject) -> SourceMaterial:
    material = db.get(SourceMaterial, job.material_id) if job.material_id else None
    if not material:
        material = db.exec(
            select(SourceMaterial)
            .where(SourceMaterial.project_id == project.id)
            .order_by(SourceMaterial.created_at.desc())
        ).first()
    if not material:
        raise ValueError("Material projects require a file before generation can start.")
    return material


def _project_chunks(db: Session, project_id: int, limit: int = 8) -> list[SourceChunk]:
    return db.exec(
        select(SourceChunk).where(SourceChunk.project_id == project_id).order_by(SourceChunk.position).limit(limit)
    ).all()


def _material_excerpt(db: Session, project_id: int) -> str | None:
    chunks = _project_chunks(db, project_id, limit=3)
    return "\n\n".join(chunk.content for chunk in chunks) if chunks else None


def _material_checksum(db: Session, job: Job) -> str | None:
    material = db.get(SourceMaterial, job.material_id) if job.material_id else None
    return material.file_checksum if material else None


def _saved_kp_payload(db: Session, project_id: int) -> list[dict[str, Any]]:
    points = db.exec(select(KnowledgePoint).where(KnowledgePoint.project_id == project_id).order_by(KnowledgePoint.id)).all()
    return [_kp_payload(point) for point in points]


def _lesson_kp_payload(db: Session, lesson_id: int) -> list[dict[str, Any]]:
    mappings = db.exec(
        select(LessonKnowledgePoint).where(LessonKnowledgePoint.lesson_id == lesson_id).order_by(LessonKnowledgePoint.order_index)
    ).all()
    payload = []
    for mapping in mappings:
        point = db.get(KnowledgePoint, mapping.knowledge_point_id)
        if point:
            payload.append(_kp_payload(point))
    return payload


def _kp_payload(point: KnowledgePoint) -> dict[str, Any]:
    return {
        "id": point.id,
        "client_key": point.client_key,
        "name": point.name,
        "explanation": point.explanation,
        "difficulty": point.difficulty,
        "estimated_weight": point.estimated_weight,
        "mastery": point.mastery,
        "source_locator": point.source_locator,
    }


def _context_for_lesson(
    db: Session, project_id: int, lesson: LessonUnit, points: list[dict[str, Any]]
) -> list[SourceChunk]:
    query = " ".join([lesson.title, lesson.summary, *[str(point.get("name")) for point in points]])
    return search_project_chunks(db, project_id, query, limit=4)


def _chunk_context(chunk: SourceChunk) -> str:
    return f"{chunk.locator or chunk.title}\n{chunk.content[:1800]}"


def _chunk_payload(chunk: SourceChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "title": chunk.title,
        "locator": chunk.locator,
        "content": chunk.content[:1800],
    }


def _first_unprepared_lesson(db: Session, project_id: int) -> LessonUnit | None:
    return db.exec(
        select(LessonUnit)
        .where(LessonUnit.project_id == project_id)
        .where(LessonUnit.content == "")
        .order_by(LessonUnit.order_index)
    ).first()


def _normalized_weights(items: list[dict[str, Any]]) -> list[float]:
    values = []
    for item in items:
        try:
            value = float(item.get("estimated_weight"))
        except (TypeError, ValueError):
            value = 0
        values.append(value if value > 0 else 0)
    total = sum(values)
    if total <= 0:
        return [round(1 / len(items), 4)] * len(items)
    return [round(value / total, 4) for value in values]


def _slug(value: Any, index: int) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return (slug or f"point-{index}")[:80]


def _token_overlap(left: str, right: str) -> int:
    import re

    a = {word.lower() for word in re.findall(r"[A-Za-z0-9]{3,}", left)}
    b = {word.lower() for word in re.findall(r"[A-Za-z0-9]{3,}", right)}
    return len(a & b)


def _best_point_for_lesson(points: list[KnowledgePoint], lesson: LessonUnit) -> KnowledgePoint:
    text = f"{lesson.title} {lesson.summary}"
    return max(points, key=lambda point: _token_overlap(text, f"{point.name} {point.explanation}"))


def _best_lesson_for_point(lessons: list[LessonUnit], point: KnowledgePoint) -> LessonUnit | None:
    if not lessons:
        return None
    text = f"{point.name} {point.explanation}"
    return max(lessons, key=lambda lesson: _token_overlap(text, f"{lesson.title} {lesson.summary}"))


def _has_mapping(db: Session, lesson_id: int, point_id: int | None) -> bool:
    if point_id is None:
        return True
    return bool(
        db.exec(
            select(LessonKnowledgePoint)
            .where(LessonKnowledgePoint.lesson_id == lesson_id)
            .where(LessonKnowledgePoint.knowledge_point_id == point_id)
        ).first()
    )


def _stage_progress(completed_index: int) -> int:
    return min(100, int((completed_index / max(1, len(STAGES))) * 100))

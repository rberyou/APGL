from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session, select

from app.models import SourceChunk


def clear_project_index(db: Session, project_id: int) -> None:
    ensure_fts_table(db)
    db.exec(text("DELETE FROM source_chunk_fts WHERE project_id = :project_id").bindparams(project_id=project_id))


def index_source_chunks(db: Session, chunks: list[SourceChunk]) -> None:
    ensure_fts_table(db)
    for chunk in chunks:
        if chunk.id is None:
            continue
        db.exec(
            text(
                """
                INSERT INTO source_chunk_fts(chunk_id, project_id, title, content, locator)
                VALUES (:chunk_id, :project_id, :title, :content, :locator)
                """
            ).bindparams(
                chunk_id=chunk.id,
                project_id=chunk.project_id,
                title=chunk.title,
                content=chunk.content,
                locator=chunk.locator or "",
            )
        )


def search_project_chunks(db: Session, project_id: int, query: str, limit: int = 5) -> list[SourceChunk]:
    ensure_fts_table(db)
    clean_query = _fts_query(query)
    rows = db.exec(
        text(
            """
            SELECT chunk_id
            FROM source_chunk_fts
            WHERE project_id = :project_id
              AND source_chunk_fts MATCH :query
            ORDER BY bm25(source_chunk_fts)
            LIMIT :limit
            """
        ).bindparams(project_id=project_id, query=clean_query, limit=limit)
    ).all()
    chunk_ids = [int(row[0]) for row in rows]
    if not chunk_ids:
        return db.exec(
            select(SourceChunk)
            .where(SourceChunk.project_id == project_id)
            .order_by(SourceChunk.position)
            .limit(limit)
        ).all()
    chunks = db.exec(select(SourceChunk).where(SourceChunk.id.in_(chunk_ids))).all()
    by_id = {chunk.id: chunk for chunk in chunks}
    return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]


def _fts_query(query: str) -> str:
    words = [word for word in query.replace('"', " ").split() if len(word) > 1]
    if not words:
        return "*"
    return " OR ".join(f'"{word}"' for word in words[:12])


def ensure_fts_table(db: Session) -> None:
    db.exec(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS source_chunk_fts
            USING fts5(
                chunk_id UNINDEXED,
                project_id UNINDEXED,
                title,
                content,
                locator
            )
            """
        )
    )

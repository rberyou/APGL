from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

from app.config import settings


def _connect_args() -> dict[str, bool]:
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(settings.database_url, connect_args=_connect_args())


def init_db() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    if settings.database_url.startswith("sqlite"):
        _ensure_sqlite_schema()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def _ensure_sqlite_schema() -> None:
    """Small additive compatibility layer for local SQLite databases."""
    with engine.begin() as connection:
        material_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(sourcematerial)")).all()
        }
        for column, definition in {
            "page_count": "INTEGER NOT NULL DEFAULT 0",
            "text_page_count": "INTEGER NOT NULL DEFAULT 0",
            "character_count": "INTEGER NOT NULL DEFAULT 0",
            "chunk_count": "INTEGER NOT NULL DEFAULT 0",
        }.items():
            if column not in material_columns:
                connection.execute(
                    text(f"ALTER TABLE sourcematerial ADD COLUMN {column} {definition}")
                )

        connection.execute(
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

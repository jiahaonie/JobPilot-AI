"""Database engine and session lifecycle."""

import sqlite3
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def _engine_options(database_url: str) -> dict[str, object]:
    """Return options that keep SQLite usable with FastAPI request handlers."""

    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def _enable_sqlite_foreign_keys(
    dbapi_connection: sqlite3.Connection,
    _connection_record: object,
) -> None:
    """Enable foreign-key enforcement for every new SQLite connection."""

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


class Database:
    """Small composition object that makes the persistence boundary testable."""

    def __init__(self, settings: Settings) -> None:
        self.engine: Engine = create_engine(
            settings.database_url,
            **_engine_options(settings.database_url),
        )
        if settings.database_url.startswith("sqlite"):
            event.listen(self.engine, "connect", _enable_sqlite_foreign_keys)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a session and roll back if the caller raises."""

        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Generator[Session]:
        """Expose the session context as a FastAPI dependency."""

        with self.session() as session:
            yield session

    def create_all(self) -> None:
        """Create tables only for explicitly isolated test databases."""

        from app.models import (  # noqa: F401
            Job,  # noqa: F401
            JobRequirementRow,
            KnowledgeDocument,
            MatchReportRow,
            Resume,
            ResumeAnalysis,
        )
        from app.models.base import Base

        Base.metadata.create_all(bind=self.engine)

    def dispose(self) -> None:
        """Release the underlying connection pool."""

        self.engine.dispose()


def get_db(request: Request) -> Generator[Session]:
    """Resolve the database configured on the current FastAPI application."""

    database: Database = request.app.state.database
    yield from database.get_session()

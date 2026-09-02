"""数据库引擎与会话生命周期。"""

import sqlite3
from collections.abc import Generator, Iterator
from contextlib import contextmanager

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def _engine_options(database_url: str) -> dict[str, object]:
    """返回确保 SQLite 可供 FastAPI 请求处理器使用的选项。"""
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def _enable_sqlite_foreign_keys(
    dbapi_connection: sqlite3.Connection,
    _connection_record: object,
) -> None:
    """为每个新 SQLite 连接启用外键约束。"""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


class Database:
    """使持久化边界可测试的小型组合对象。"""

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
        """提供会话，并在调用方抛出异常时回滚。"""
        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Generator[Session]:
        """将会话上下文作为 FastAPI 依赖提供。"""
        with self.session() as session:
            yield session

    def create_all(self) -> None:
        """仅为明确隔离的测试数据库创建表。"""
        from app.models import (  # noqa: F401
            Job,  # noqa: F401
            JobAnalysis,
            JobRequirementRow,
            JobResume,
            KnowledgeDocument,
            MatchReportRow,
            Resume,
            ResumeAnalysis,
            StudyPlan,
            StudyTask,
        )
        from app.models.base import Base

        Base.metadata.create_all(bind=self.engine)

    def dispose(self) -> None:
        """释放底层连接池。"""
        self.engine.dispose()


def get_db(request: Request) -> Generator[Session]:
    """解析当前 FastAPI 应用配置的数据库。"""
    database: Database = request.app.state.database
    yield from database.get_session()

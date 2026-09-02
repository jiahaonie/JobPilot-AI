"""基于隔离 SQLite 数据库的 Alembic 迁移测试。"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app.core.config import Settings
from app.core.database import Database
from app.main import create_app


def test_upgrade_head_builds_current_schema_and_has_no_model_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {
        "alembic_version",
        "job_requirements",
        "jobs",
        "knowledge_documents",
        "match_reports",
        "resume_analyses",
        "resumes",
    } <= set(inspector.get_table_names())
    foreign_keys = inspector.get_foreign_keys("match_reports")
    assert {
        (foreign_key["referred_table"], foreign_key["options"].get("ondelete"))
        for foreign_key in foreign_keys
    } == {("jobs", "CASCADE"), ("resumes", "CASCADE")}
    engine.dispose()

    command.check(config)


def test_application_never_auto_creates_non_test_schema(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'application.db').as_posix()}"
    settings = Settings(
        environment="development",
        database_url=database_url,
        auto_create_tables=True,
    )
    database = Database(settings)
    application = create_app(settings=settings, database=database)

    with TestClient(application):
        assert inspect(database.engine).get_table_names() == []

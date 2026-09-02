"""基于隔离 SQLite 数据库的 Alembic 迁移测试。"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

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
        "job_analyses",
        "job_requirements",
        "job_resumes",
        "jobs",
        "knowledge_documents",
        "match_reports",
        "resume_analyses",
        "resumes",
        "study_plans",
        "study_tasks",
    } <= set(inspector.get_table_names())
    report_foreign_keys = inspector.get_foreign_keys("match_reports")
    assert {
        (foreign_key["referred_table"], foreign_key["options"].get("ondelete"))
        for foreign_key in report_foreign_keys
    } == {("jobs", "CASCADE"), ("resumes", "CASCADE")}
    binding_foreign_keys = inspector.get_foreign_keys("job_resumes")
    assert {
        (foreign_key["referred_table"], foreign_key["options"].get("ondelete"))
        for foreign_key in binding_foreign_keys
    } == {("jobs", "CASCADE"), ("resumes", "RESTRICT")}
    plan_foreign_keys = inspector.get_foreign_keys("study_plans")
    assert {
        (foreign_key["referred_table"], foreign_key["options"].get("ondelete"))
        for foreign_key in plan_foreign_keys
    } == {("match_reports", "CASCADE")}
    task_foreign_keys = inspector.get_foreign_keys("study_tasks")
    assert {
        (foreign_key["referred_table"], foreign_key["options"].get("ondelete"))
        for foreign_key in task_foreign_keys
    } == {("study_plans", "CASCADE")}
    job_columns = {column["name"]: column for column in inspector.get_columns("jobs")}
    assert job_columns["status"]["nullable"] is True
    engine.dispose()

    command.check(config)


def test_migration_backfills_job_analysis_from_requirements(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "backfill.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "9c06d0cdc7c0")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO jobs (
                    id, company_name, job_title, raw_text, status, created_at, updated_at
                ) VALUES
                    (1, 'A', 'Analyzed', 'Python', 'pending_analysis', CURRENT_TIMESTAMP,
                     CURRENT_TIMESTAMP),
                    (2, 'B', 'Pending', 'FastAPI', 'pending_analysis', CURRENT_TIMESTAMP,
                     CURRENT_TIMESTAMP)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job_requirements (
                    job_id, job_title, required_skills, preferred_skills,
                    responsibilities, evidence, created_at, updated_at
                ) VALUES (
                    1, 'Analyzed', '[]', '[]', '[]', '[]', CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            )
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        statuses = {
            row.job_id: row.status
            for row in connection.execute(
                text("SELECT job_id, status FROM job_analyses ORDER BY job_id")
            )
        }
        job_statuses = list(
            connection.execute(text("SELECT status FROM jobs ORDER BY id")).scalars()
        )
    engine.dispose()

    assert statuses == {1: "ready", 2: "pending"}
    assert job_statuses == [None, None]


def test_migration_refuses_unmapped_active_job_status(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unsafe.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "9c06d0cdc7c0")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO jobs (
                    company_name, job_title, raw_text, status, created_at, updated_at
                ) VALUES (
                    'A', 'Active', 'Python', 'applied', CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            )
        )
    engine.dispose()

    with pytest.raises(RuntimeError, match="without knowing their resume_id"):
        command.upgrade(config, "head")


def test_new_migration_downgrade_restores_pending_analysis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "downgrade.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO jobs (
                    id, company_name, job_title, raw_text, status, created_at, updated_at
                ) VALUES (
                    1, 'A', 'Pending', 'Python', NULL, CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO job_analyses (job_id, status, updated_at)
                VALUES (1, 'pending', CURRENT_TIMESTAMP)
                """
            )
        )
    engine.dispose()

    command.downgrade(config, "9c06d0cdc7c0")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        status = connection.execute(text("SELECT status FROM jobs WHERE id = 1")).scalar_one()
        tables = set(inspect(connection).get_table_names())
    engine.dispose()

    assert status == "pending_analysis"
    assert "job_analyses" not in tables
    assert "job_resumes" not in tables
    assert "study_plans" not in tables
    assert "study_tasks" not in tables


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

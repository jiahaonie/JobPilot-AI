"""Shared test fixtures."""

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Database
from app.main import create_app


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """Use a workspace-local test directory in restricted Windows environments.

    The standard pytest temp root is not accessible in this workspace. These
    directories are intentionally retained for post-test inspection.
    """

    path = (
        Path.cwd()
        / ".pytest-work"
        / f"{request.node.name}-{uuid4().hex}"
    )
    path.mkdir(parents=True, exist_ok=False)
    return path


@pytest.fixture
def application(tmp_path) -> Iterator[FastAPI]:
    """Build an isolated application backed by a temporary SQLite database."""

    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        auto_create_tables=True,
    )
    database = Database(settings)
    yield create_app(settings=settings, database=database)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    """Run the app lifespan for integration tests."""

    with TestClient(application) as test_client:
        yield test_client

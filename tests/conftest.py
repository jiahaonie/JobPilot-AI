"""共享测试夹具。"""

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
    """在受限 Windows 环境中使用工作区内的测试目录。"""
    path = Path.cwd() / ".pytest-work" / f"{request.node.name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


@pytest.fixture
def application(tmp_path) -> Iterator[FastAPI]:
    """构建由临时 SQLite 数据库支持的隔离应用。"""
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        auto_create_tables=True,
        llm_api_key=None,
    )
    database = Database(settings)
    yield create_app(settings=settings, database=database)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    """在集成测试期间运行应用生命周期。"""
    with TestClient(application) as test_client:
        yield test_client

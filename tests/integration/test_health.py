"""健康检查 HTTP 端点测试。"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError


def test_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "JobPilot AI"


def test_readiness_endpoint_checks_database(client) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "JobPilot AI"


def test_readiness_endpoint_returns_503_when_database_is_unavailable(
    client,
    application: FastAPI,
    monkeypatch,
) -> None:
    @contextmanager
    def unavailable_session() -> Iterator[None]:
        raise OperationalError("SELECT 1", {}, RuntimeError("unavailable"))
        yield

    monkeypatch.setattr(application.state.database, "session", unavailable_session)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}

"""健康检查端点。"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Database
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """不访问数据库，返回轻量存活响应。"""
    return HealthResponse(
        status="ok",
        service=request.app.state.settings.app_name,
    )


@router.get("/health/ready", response_model=HealthResponse)
def readiness(request: Request) -> HealthResponse:
    """确认应用可访问数据库，可用于容器编排就绪检查。"""
    database: Database = request.app.state.database
    try:
        with database.session() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc

    return HealthResponse(
        status="ok",
        service=request.app.state.settings.app_name,
    )

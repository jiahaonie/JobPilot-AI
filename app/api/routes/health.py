"""健康检查端点。"""

from fastapi import APIRouter, Request

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """不访问数据库，返回轻量存活响应。"""
    return HealthResponse(
        status="ok",
        service=request.app.state.settings.app_name,
    )

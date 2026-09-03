"""共享响应契约。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """存活检查端点返回的响应。"""

    status: str
    service: str

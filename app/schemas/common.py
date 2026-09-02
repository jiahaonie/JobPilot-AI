"""共享响应契约。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """存活检查端点返回的响应。"""

    status: str
    service: str


class MessageResponse(BaseModel):
    """数据变更端点使用的简单消息响应。"""

    message: str

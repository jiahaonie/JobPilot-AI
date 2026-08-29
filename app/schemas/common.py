"""Shared response contracts."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response returned by the liveness endpoint."""

    status: str
    service: str


class MessageResponse(BaseModel):
    """Simple message response for mutation endpoints."""

    message: str

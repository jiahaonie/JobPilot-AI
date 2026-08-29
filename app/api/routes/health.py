"""Health endpoint."""

from fastapi import APIRouter, Request

from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Return a lightweight liveness response without touching the database."""

    return HealthResponse(
        status="ok",
        service=request.app.state.settings.app_name,
    )

"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.ask import router as ask_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.resumes import router as resumes_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(ask_router)
api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(knowledge_router)
api_router.include_router(resumes_router)

"""FastAPI application composition root."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
) -> FastAPI:
    """Create an application with replaceable settings and persistence."""

    effective_settings = settings or get_settings()
    effective_database = database or Database(effective_settings)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        if effective_settings.auto_create_tables:
            effective_database.create_all()
        yield
        effective_database.dispose()

    application = FastAPI(
        title=effective_settings.app_name,
        debug=effective_settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = effective_settings
    application.state.database = effective_database
    configure_logging()
    register_exception_handlers(application)
    application.include_router(api_router, prefix=effective_settings.api_prefix)
    return application


app = create_app()

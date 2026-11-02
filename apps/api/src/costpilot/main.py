"""Starts the web API. See composition.py for how the modules are connected."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from costpilot.composition import (
    MEGABYTE,
    build_analytics_service,
    build_auth_service,
    build_document_service,
)
from costpilot.modules.analytics.api.routes import router as analytics_router
from costpilot.modules.documents.api.routes import router as documents_router
from costpilot.modules.identity.api.routes import router as identity_router
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database
from costpilot.shared.errors import register_error_handlers
from costpilot.shared.limits import MaxBodySizeMiddleware
from costpilot.shared.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    database = Database(settings.app_database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database.close()

    app = FastAPI(
        title=settings.app_name,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.auth = build_auth_service(settings, database)
    app.state.documents = build_document_service(settings, database)
    app.state.analytics = build_analytics_service(settings, database)
    app.add_middleware(
        MaxBodySizeMiddleware,
        path_prefix=f"{settings.api_prefix}/documents",
        max_bytes=(settings.max_upload_mb + 1) * MEGABYTE,
    )
    register_error_handlers(app)

    router = APIRouter(prefix=settings.api_prefix)

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    router.include_router(identity_router)
    router.include_router(documents_router)
    router.include_router(analytics_router)
    app.include_router(router)
    return app


app = create_app()

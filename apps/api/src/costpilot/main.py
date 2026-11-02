"""Connects the whole backend together. This is the only file that sees every module."""

from fastapi import APIRouter, FastAPI

from costpilot.shared.config import get_settings
from costpilot.shared.errors import register_error_handlers
from costpilot.shared.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
    )
    register_error_handlers(app)

    router = APIRouter(prefix=settings.api_prefix)

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()

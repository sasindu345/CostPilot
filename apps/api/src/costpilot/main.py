"""Connects the whole backend together. This is the only file that sees every module."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import APIRouter, FastAPI

from costpilot.modules.audit.infrastructure.postgres_audit_log import PostgresAuditLog
from costpilot.modules.identity.api.routes import router as identity_router
from costpilot.modules.identity.application.auth_service import AuthService
from costpilot.modules.identity.infrastructure.fernet_secret_box import FernetSecretBox
from costpilot.modules.identity.infrastructure.keycloak_provider import KeycloakProvider
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import Settings, get_settings
from costpilot.shared.database import Database
from costpilot.shared.errors import register_error_handlers
from costpilot.shared.logging import configure_logging


def build_auth_service(settings: Settings, database: Database) -> AuthService:
    provider = KeycloakProvider(
        public_url=settings.keycloak_public_url,
        internal_url=settings.keycloak_internal_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret.get_secret_value(),
        redirect_uri=f"{settings.app_public_url}{settings.api_prefix}/auth/callback",
        post_logout_redirect_uri=settings.app_public_url,
    )
    return AuthService(
        provider=provider,
        repository=PostgresIdentityRepository(database),
        secret_box=FernetSecretBox(settings.session_encryption_key.get_secret_value()),
        audit_log=PostgresAuditLog(database),
        session_lifetime=timedelta(hours=settings.session_lifetime_hours),
        login_lifetime_seconds=settings.login_lifetime_seconds,
    )


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
    register_error_handlers(app)

    router = APIRouter(prefix=settings.api_prefix)

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    router.include_router(identity_router)
    app.include_router(router)
    return app


app = create_app()

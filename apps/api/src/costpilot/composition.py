"""Builds the real objects and connects modules. The API and the worker both start from here."""

from datetime import UTC, date, datetime, timedelta

from costpilot.modules.analytics.application.analytics_service import AnalyticsService
from costpilot.modules.analytics.infrastructure.numpy_unusual_cost_detector import (
    NumpyUnusualCostDetector,
)
from costpilot.modules.analytics.infrastructure.postgres_store import PostgresAnalyticsStore
from costpilot.modules.audit.infrastructure.postgres_audit_log import PostgresAuditLog
from costpilot.modules.billing.application.import_service import BillImportService
from costpilot.modules.billing.infrastructure.postgres_store import PostgresBillingStore
from costpilot.modules.documents.application.document_service import DocumentService
from costpilot.modules.documents.application.job_runner import JobRunner
from costpilot.modules.documents.application.ports import FileStorage
from costpilot.modules.documents.infrastructure.local_storage import LocalFileStorage
from costpilot.modules.documents.infrastructure.postgres_repository import (
    PostgresDocumentRepository,
)
from costpilot.modules.documents.infrastructure.s3_storage import S3FileStorage
from costpilot.modules.identity.application.auth_service import AuthService
from costpilot.modules.identity.infrastructure.fernet_secret_box import FernetSecretBox
from costpilot.modules.identity.infrastructure.keycloak_provider import KeycloakProvider
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import Settings
from costpilot.shared.database import Database

MEGABYTE = 1024 * 1024


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


def build_file_storage(settings: Settings) -> FileStorage:
    if settings.storage_backend == "s3":
        return S3FileStorage(bucket=settings.s3_bucket, region=settings.aws_region)
    return LocalFileStorage(settings.storage_local_path)


def build_bill_importer(settings: Settings, database: Database) -> BillImportService:
    return BillImportService(
        store=PostgresBillingStore(database),
        batch_size=settings.import_batch_size,
    )


def today_utc() -> date:
    return datetime.now(UTC).date()


def build_analytics_service(settings: Settings, database: Database) -> AnalyticsService:
    return AnalyticsService(
        store=PostgresAnalyticsStore(database),
        detector=NumpyUnusualCostDetector(
            history_months=settings.unusual_history_months,
            min_history_months=settings.unusual_min_history_months,
            threshold=settings.unusual_threshold,
            min_increase_percent=settings.unusual_min_increase_percent,
            min_increase_amount=settings.unusual_min_increase_amount,
        ),
        top_service_limit=settings.top_service_limit,
        today=today_utc,
    )


def build_document_service(settings: Settings, database: Database) -> DocumentService:
    return DocumentService(
        repository=PostgresDocumentRepository(database),
        storage=build_file_storage(settings),
        audit_log=PostgresAuditLog(database),
        importer=build_bill_importer(settings, database),
        list_limit=settings.document_list_limit,
    )


def build_job_runner(settings: Settings, database: Database) -> JobRunner:
    return JobRunner(
        repository=PostgresDocumentRepository(database),
        storage=build_file_storage(settings),
        importer=build_bill_importer(settings, database),
        max_unpacked_bytes=settings.max_unpacked_mb * MEGABYTE,
        max_attempts=settings.job_max_attempts,
        retry_delay=timedelta(seconds=settings.job_retry_seconds),
        stale_after=timedelta(minutes=settings.job_stale_minutes),
    )

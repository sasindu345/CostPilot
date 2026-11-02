"""Builds the real objects and connects modules. The API and the worker both start from here."""

from datetime import UTC, date, datetime, timedelta

from qdrant_client import AsyncQdrantClient

from costpilot.modules.analytics.application.analytics_service import AnalyticsService
from costpilot.modules.analytics.infrastructure.numpy_unusual_cost_detector import (
    NumpyUnusualCostDetector,
)
from costpilot.modules.analytics.infrastructure.postgres_store import PostgresAnalyticsStore
from costpilot.modules.assistant.application.assistant_service import AssistantService
from costpilot.modules.assistant.application.specialists import SpecialistAgents
from costpilot.modules.assistant.infrastructure.gemini_chat_model import GeminiChatModel
from costpilot.modules.assistant.infrastructure.langgraph_workflow import (
    LangGraphEvidenceWorkflow,
)
from costpilot.modules.assistant.infrastructure.postgres_store import (
    PostgresConversationStore,
    PostgresUsageLimiter,
)
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
from costpilot.modules.knowledge.application.indexer import KnowledgeIndexer
from costpilot.modules.knowledge.application.search_service import KnowledgeSearchService
from costpilot.modules.knowledge.infrastructure.gemini_embedder import GeminiEmbedder
from costpilot.modules.knowledge.infrastructure.html_page_loader import HtmlPageLoader
from costpilot.modules.knowledge.infrastructure.langchain_splitter import LangChainTextSplitter
from costpilot.modules.knowledge.infrastructure.qdrant_index import QdrantVectorIndex
from costpilot.modules.recommendations.application.recommendation_service import (
    RecommendationService,
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
        usage_change_limit=settings.usage_change_limit,
        today=today_utc,
    )


def build_recommendation_service(settings: Settings, database: Database) -> RecommendationService:
    return RecommendationService(
        analytics=build_analytics_service(settings, database),
        min_monthly_cost=settings.recommendation_min_monthly_cost,
        steady_ratio=settings.recommendation_steady_ratio,
        docs_urls={"aws": settings.aws_docs_url},
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


def _build_embedder(settings: Settings) -> GeminiEmbedder:
    return GeminiEmbedder(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
        retries=settings.embedding_retries,
        retry_seconds=settings.embedding_retry_seconds,
    )


def _build_vector_index(settings: Settings) -> QdrantVectorIndex:
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.get_secret_value() or None,
    )
    return QdrantVectorIndex(
        client=client,
        collection=settings.knowledge_collection,
        dimensions=settings.embedding_dimensions,
    )


def build_knowledge_indexer(settings: Settings) -> KnowledgeIndexer:
    return KnowledgeIndexer(
        loader=HtmlPageLoader(
            allowed_hosts=settings.knowledge_allowed_hosts,
            max_bytes=settings.knowledge_max_page_bytes,
            timeout_seconds=settings.knowledge_timeout_seconds,
        ),
        splitter=LangChainTextSplitter(settings.chunk_size, settings.chunk_overlap),
        embedder=_build_embedder(settings),
        index=_build_vector_index(settings),
        allowed_hosts=settings.knowledge_allowed_hosts,
    )


def build_knowledge_search(settings: Settings) -> KnowledgeSearchService:
    return KnowledgeSearchService(
        embedder=_build_embedder(settings),
        index=_build_vector_index(settings),
        limit=settings.search_limit,
        min_score=settings.search_min_score,
    )


def build_assistant_service(settings: Settings, database: Database) -> AssistantService:
    model = GeminiChatModel(
        api_key=settings.gemini_api_key,
        answer_model=settings.gemini_answer_model,
        router_model=settings.gemini_router_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        retries=settings.gemini_retries,
    )
    return AssistantService(
        store=PostgresConversationStore(database),
        limiter=PostgresUsageLimiter(database),
        model=model,
        workflow=LangGraphEvidenceWorkflow(
            model, SpecialistAgents(model, settings.assistant_ai_specialists)
        ),
        analytics=build_analytics_service(settings, database),
        knowledge=build_knowledge_search(settings),
        recommendations=build_recommendation_service(settings, database),
        audit_log=PostgresAuditLog(database),
        daily_limit=settings.assistant_daily_limit,
        max_question_length=settings.assistant_max_question_length,
        history_messages=settings.assistant_history_messages,
        conversation_limit=settings.assistant_conversation_limit,
        answer_attempts=settings.assistant_answer_attempts,
        ai_call_limit=settings.assistant_ai_call_limit,
        today=today_utc,
    )

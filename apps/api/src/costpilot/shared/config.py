"""All backend settings. Values come from environment variables, never from code."""

from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    app_name: str = "CostPilot"
    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    app_public_url: str

    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_app_user: str
    postgres_app_password: SecretStr

    keycloak_public_url: str
    keycloak_internal_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: SecretStr

    session_encryption_key: SecretStr
    session_cookie_name: str
    session_cookie_secure: bool
    session_lifetime_hours: int
    login_cookie_name: str = "costpilot_login"
    login_lifetime_seconds: int = 600

    storage_backend: Literal["local", "s3"]
    storage_local_path: str
    s3_bucket: str = ""
    aws_region: str = ""

    aws_docs_url: str
    qdrant_url: str
    qdrant_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")
    gemini_embedding_model: str
    gemini_answer_model: str
    gemini_router_model: str
    gemini_tier: Literal["free", "paid"] = "free"
    gemini_timeout_seconds: float = 30
    gemini_retries: int = 2
    assistant_daily_limit: int = 50
    assistant_max_question_length: int = 1000
    assistant_history_messages: int = 6
    assistant_conversation_limit: int = 20
    assistant_answer_attempts: int = 2
    assistant_ai_call_limit: int = 4
    assistant_ai_specialists: tuple[str, ...] = ("anomaly", "optimization")
    knowledge_sources_path: str = "../../knowledge/sources.yaml"
    knowledge_questions_path: str = "../../knowledge/search-questions.yaml"
    knowledge_collection: str = "cloud_docs"
    knowledge_allowed_hosts: tuple[str, ...] = ("docs.aws.amazon.com",)
    knowledge_max_page_bytes: int = 5_000_000
    knowledge_timeout_seconds: float = 20
    embedding_dimensions: int = 768
    embedding_batch_size: int = 20
    embedding_retries: int = 3
    embedding_retry_seconds: float = 20
    chunk_size: int = 1200
    chunk_overlap: int = 150
    search_limit: int = 5
    search_min_score: float = 0.55
    search_min_hit_rate: float = 0.8

    max_upload_mb: int = 100
    max_unpacked_mb: int = 1024
    document_list_limit: int = 100
    import_batch_size: int = 2000
    worker_poll_seconds: float = 2
    top_service_limit: int = 3
    usage_change_limit: int = 8
    recommendation_min_monthly_cost: Decimal = Decimal(5)
    recommendation_steady_ratio: Decimal = Decimal("1.25")
    unusual_history_months: int = 6
    unusual_min_history_months: int = 3
    unusual_threshold: float = 3.0
    unusual_min_increase_percent: float = 20
    unusual_min_increase_amount: float = 1
    job_max_attempts: int = 3
    job_retry_seconds: int = 30
    job_stale_minutes: int = 15

    def _database_url(self, username: str, password: SecretStr) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=username,
            password=password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def app_database_url(self) -> URL:
        return self._database_url(self.postgres_app_user, self.postgres_app_password)

    @property
    def admin_database_url(self) -> URL:
        return self._database_url(self.postgres_user, self.postgres_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()

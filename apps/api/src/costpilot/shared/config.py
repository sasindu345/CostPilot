"""All backend settings. Values come from environment variables, never from code."""

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

    max_upload_mb: int = 100
    max_unpacked_mb: int = 1024
    document_list_limit: int = 100
    worker_poll_seconds: float = 2
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

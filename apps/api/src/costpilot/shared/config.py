"""All backend settings. Values come from environment variables, never from code."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CostPilot"
    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    api_prefix: str = "/api"


@lru_cache
def get_settings() -> Settings:
    return Settings()

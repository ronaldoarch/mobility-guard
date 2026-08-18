from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Mobility Guard"
    app_env: str = "development"
    database_path: str = "data/mobility_guard.db"
    database_url: str | None = None
    api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    async_explanation_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    anomaly_threshold: float = Field(default=0.65, ge=0, le=1)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

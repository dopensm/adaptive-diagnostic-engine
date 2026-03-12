"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the adaptive diagnostic engine."""

    app_name: str = "AI-Driven Adaptive Diagnostic Engine"
    app_env: str = "development"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_database: str = "adaptive_diagnostic_engine"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    test_question_limit: int = Field(default=10, ge=1, le=50)
    baseline_ability: float = Field(default=0.5, ge=0.1, le=1.0)
    ability_floor: float = Field(default=0.1, ge=0.0, le=1.0)
    ability_ceiling: float = Field(default=1.0, ge=0.1, le=1.0)
    ability_step_scale: float = Field(default=0.18, gt=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()

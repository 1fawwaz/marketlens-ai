"""Shared configuration for MarketLens AI backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE, override=False)


def _clean_secret(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "marketlens"
    postgres_user: str = "marketlens"
    postgres_password: str = "marketlens_dev"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_username: str
    admin_password: str

    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    cors_allowed_origins: str | None = None

    @field_validator("groq_api_key", mode="before")
    @classmethod
    def normalize_optional_secrets(cls, value: str | None) -> str | None:
        return _clean_secret(value)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        if not self.cors_allowed_origins:
            return []
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def resolve_llm_backend(settings: Settings | None = None) -> str:
    """Return groq or deterministic based on GROQ_API_KEY."""
    settings = settings or get_settings()
    return "groq" if settings.groq_api_key else "deterministic"

# app/core/config.py
"""Application configuration (Pydantic Settings v2)."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env burada otomatik yüklenir; ekstra alanları yok say.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server
    port: int = Field(8080, validation_alias="PORT")

    # Gemini
    gemini_api_key: str = Field(..., validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")

    # Google Sheets
    google_application_credentials: str = Field(..., validation_alias="GOOGLE_APPLICATION_CREDENTIALS")
    sheet_id: str = Field(..., validation_alias="SHEET_ID")
    range_people: str = Field("People!A2:K", validation_alias="RANGE_PEOPLE")

    # App
    default_locale: str = Field("tr-TR", validation_alias="DEFAULT_LOCALE")
    cache_ttl_ms: int = Field(60000, validation_alias="CACHE_TTL_MS")

    # Logging
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    # ---- validators / conveniences ----
    @field_validator("google_application_credentials")
    @classmethod
    def _ensure_credentials_exists(cls, v: str) -> str:
        """Make path absolute and ensure the file exists."""
        p = Path(v)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.exists():
            raise FileNotFoundError(f"service account json not found at {p}")
        return str(p)


@lru_cache
def get_settings() -> Settings:
    """Use this to avoid re-parsing env on every import."""
    return Settings()

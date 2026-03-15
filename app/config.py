from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = Field(..., min_length=32)
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://pulsesync:pulsesync@localhost:5432/pulsesync"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")  # type: ignore[assignment]

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── PHI Encryption ────────────────────────────────────────────────────────
    phi_encryption_key: str = Field(..., min_length=32)

    # ── Telephony (Twilio) ────────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_webhook_url: str = ""

    # ── Transcription (Deepgram) ──────────────────────────────────────────────
    deepgram_api_key: str = ""
    transcription_callback_url: str = ""

    # ── AI ────────────────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    classification_model: str = "claude-sonnet-4-6"

    # ── CRM ───────────────────────────────────────────────────────────────────
    hc1_crm_base_url: str = ""
    hc1_crm_api_key: str = ""
    hc1_crm_timeout_seconds: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

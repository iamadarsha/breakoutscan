from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_config_path = Path(__file__).resolve()
API_ENV_FILE = _config_path.parents[2] / ".env"
# In Docker (/app/app/core/config.py) the path is only 4 levels deep,
# so parents[4] would raise IndexError. Fall back to API_ENV_FILE.
REPO_ENV_FILE = _config_path.parents[4] / ".env" if len(_config_path.parents) > 4 else API_ENV_FILE


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ENV_FILE), str(API_ENV_FILE), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = (
        "postgresql+asyncpg://breakoutscan:breakoutscan@localhost:5432/breakoutscan"
    )
    redis_url: str = "redis://localhost:6379/0"
    upstox_api_key: str = ""
    upstox_api_secret: str = ""
    upstox_redirect_uri: str = "http://localhost:8001/auth/upstox/callback"
    upstox_api_version: str = "2.0"
    # Preferred over the OAuth2 flow above for this project's single-owner,
    # server-side-only usage: no browser redirect, 1-year validity, read-only.
    # Generate at https://account.upstox.com/developer/apps (Analytics tab).
    upstox_analytics_token: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""
    next_public_api_url: str = "http://localhost:8001"
    next_public_ws_url: str = "ws://localhost:8001"
    next_public_supabase_url: str = ""
    next_public_supabase_anon_key: str = ""
    gemini_api_key: str = ""
    gemini_backup_api_key: str = ""
    groq_api_key: str = ""
    # Groq retires models; keep the choice in config so a retirement is an env
    # change, and fall through the list when one is gone or rate-limited.
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_models: str = "qwen/qwen3.8-27b,openai/gpt-oss-20b"
    xai_api_key: str = ""
    indian_api_key: str = ""
    telegram_bot_token: str = ""
    fcm_server_key: str = ""
    environment: str = "development"
    debug: bool = False
    market_timezone: str = "Asia/Kolkata"
    redis_short_ttl_seconds: int = 300
    redis_indicator_ttl_seconds: int = 600
    redis_instrument_ttl_seconds: int = 86400
    redis_token_ttl_seconds: int = 28800
    redis_oauth_state_ttl_seconds: int = 600
    nse_fallback_silence_seconds: int = 60

    # CORS — comma-separated extra origins (added on top of hardcoded defaults)
    cors_allowed_origins: str = ""

    # Rate limiting (slowapi / limits syntax: "N/period")
    rate_limit_default: str = "100/minute"
    rate_limit_screener: str = "20/minute"
    rate_limit_ai_refresh: str = "5/minute"

    @model_validator(mode="after")
    def _reject_unsafe_production_defaults(self) -> "Settings":
        """Fail fast at startup rather than silently degrading in production.

        The `localhost:5432` default above is a legitimate local-dev
        convenience, but this VM has no local Postgres — using it in
        production is exactly what caused every candle-persistence write
        to fail silently and grow an unbounded retry buffer (2026-09-14).
        Refusing to start is safer than starting broken.
        """
        if self.environment.lower() != "production":
            return self
        db_url_lower = self.database_url.lower()
        if "localhost" in db_url_lower or "127.0.0.1" in db_url_lower:
            raise ValueError(
                "DATABASE_URL points at localhost/127.0.0.1 while ENVIRONMENT=production. "
                "Set a real DATABASE_URL (see config/production-env.example) — refusing to "
                "start with a database config that cannot work in production."
            )
        if not self.database_url.strip():
            raise ValueError("DATABASE_URL is empty while ENVIRONMENT=production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

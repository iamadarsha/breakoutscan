"""
BreakoutScan Backend Configuration
All settings are read from environment variables (or .env file).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────
    app_name: str = "BreakoutScan"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"  # development | production
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://breakout:breakout_dev_pass@localhost:5432/stockdb"

    # ── Redis ──────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0

    # ── Upstox API ─────────────────────────────────────────────────────────
    upstox_api_key: Optional[str] = None
    upstox_api_secret: Optional[str] = None
    upstox_redirect_uri: str = "http://localhost:8000/auth/callback"
    upstox_base_url: str = "https://api.upstox.com/v2"
    upstox_ws_url: str = "wss://api.upstox.com/v3/feeds/market-data-feed"

    # Upstox instruments CSV URLs
    upstox_nse_instruments_url: str = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz"
    upstox_bse_instruments_url: str = "https://assets.upstox.com/market-quote/instruments/exchange/BSE.csv.gz"

    # ── Supabase ───────────────────────────────────────────────────────────
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None

    # ── Celery ─────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Notifications ──────────────────────────────────────────────────────
    telegram_bot_token: Optional[str] = None
    sendgrid_api_key: Optional[str] = None

    # ── Market Hours (IST = UTC+5:30) ──────────────────────────────────────
    market_open_time: str = "09:15"    # IST
    market_close_time: str = "15:30"   # IST
    pre_market_start: str = "09:00"    # instrument/auth setup
    orb_end_time: str = "09:30"        # Opening Range end (first 15 min)
    after_hours_end: str = "16:00"     # allow delayed data fetch

    # ── Screener ───────────────────────────────────────────────────────────
    screener_universe_size: int = 2000  # total NSE stocks to scan
    screener_batch_size: int = 500      # stocks per Redis pipeline fetch
    max_scan_results: int = 200         # hard cap on results returned

    # ── CORS ───────────────────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://breakoutscan.vercel.app",
        "https://www.breakoutscan.in",
        "https://breakoutscan-api.onrender.com",
    ]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def upstox_configured(self) -> bool:
        return bool(self.upstox_api_key and self.upstox_api_secret)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

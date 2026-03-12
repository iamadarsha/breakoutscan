"""
Upstox OAuth2 Authentication Manager.
Handles access token storage, refresh, and retrieval from Redis.
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
import redis.asyncio as aioredis
import structlog

from config import settings

log = structlog.get_logger(__name__)

# Redis keys
TOKEN_KEY = "upstox:access_token"
TOKEN_EXPIRY_KEY = "upstox:token_expiry"
AUTH_CODE_KEY = "upstox:auth_code"


class UpstoxAuthManager:
    """Manages Upstox OAuth2 tokens stored in Redis."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.base_url = settings.upstox_base_url

    # ── Token retrieval ────────────────────────────────────────────────────

    async def get_access_token(self) -> Optional[str]:
        """Get stored access token. Returns None if not set or expired."""
        token = await self.redis.get(TOKEN_KEY)
        if not token:
            return None
        return token.decode("utf-8") if isinstance(token, bytes) else token

    async def set_access_token(self, token: str, expires_in_seconds: int = 86400):
        """Store access token with TTL (default 24 hours)."""
        await self.redis.setex(TOKEN_KEY, expires_in_seconds, token)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        await self.redis.set(TOKEN_EXPIRY_KEY, expiry.isoformat())
        log.info("access_token_stored", expires_in=expires_in_seconds)

    async def is_token_valid(self) -> bool:
        """Check if we have a valid non-expired token."""
        token = await self.get_access_token()
        return bool(token)

    # ── OAuth2 flow ────────────────────────────────────────────────────────

    def get_login_url(self) -> str:
        """Generate Upstox OAuth2 authorization URL."""
        if not settings.upstox_configured:
            raise ValueError("Upstox API credentials not configured in .env")
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={settings.upstox_api_key}"
            f"&redirect_uri={settings.upstox_redirect_uri}"
        )

    async def exchange_code_for_token(self, auth_code: str) -> dict:
        """Exchange OAuth2 authorization code for access token."""
        if not settings.upstox_configured:
            raise ValueError("Upstox API credentials not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.upstox.com/v2/login/authorization/token",
                data={
                    "code": auth_code,
                    "client_id": settings.upstox_api_key,
                    "client_secret": settings.upstox_api_secret,
                    "redirect_uri": settings.upstox_redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        if access_token:
            # Upstox tokens expire next day, store for 8 hours to be safe
            await self.set_access_token(access_token, expires_in_seconds=28800)
            log.info("oauth2_token_obtained", user=token_data.get("email"))

        return token_data

    # ── Token check with mock fallback ────────────────────────────────────

    async def get_token_or_mock(self) -> Optional[str]:
        """
        Returns a real token if available, or None if in dev mode without credentials.
        Callers should check and use fallback data sources if None is returned.
        """
        token = await self.get_access_token()
        if token:
            return token

        if not settings.upstox_configured:
            log.warning("upstox_not_configured", message="Using fallback data sources")
            return None

        log.error("upstox_token_missing", message="Token not in Redis — login required")
        return None


# ── Singleton factory ──────────────────────────────────────────────────────

_auth_manager: Optional[UpstoxAuthManager] = None


async def get_auth_manager() -> UpstoxAuthManager:
    """FastAPI dependency — returns singleton UpstoxAuthManager."""
    global _auth_manager
    if _auth_manager is None:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
        _auth_manager = UpstoxAuthManager(redis_client)
    return _auth_manager

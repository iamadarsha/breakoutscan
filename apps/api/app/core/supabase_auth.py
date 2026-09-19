"""Verify Supabase-issued access tokens.

Supabase projects sign user tokens with either an asymmetric key (ES256 /
RS256, verified against the project's public JWKS — no secret needed) or, on
older projects, a legacy HS256 shared secret. Which one a token uses is read
from its header, but the algorithm allowlist and the key material are chosen
here, never by the token, so a token cannot downgrade or confuse the check
(e.g. HS256 signed with the public key as the "secret").
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from app.core.config import Settings

logger = logging.getLogger(__name__)

ASYMMETRIC_ALGORITHMS = ("ES256", "RS256")
AUDIENCE = "authenticated"
JWKS_CACHE_SECONDS = 3600

_jwks_clients: dict[str, PyJWKClient] = {}


class AuthNotConfigured(Exception):
    """Server is missing the setting needed to verify this kind of token."""


def _project_url(settings: Settings) -> str:
    return (settings.supabase_url or settings.next_public_supabase_url or "").rstrip("/")


def _jwks_client(jwks_url: str) -> PyJWKClient:
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = PyJWKClient(jwks_url, cache_keys=True, lifespan=JWKS_CACHE_SECONDS, timeout=5)
        _jwks_clients[jwks_url] = client
    return client


async def verify_supabase_token(token: str, settings: Settings) -> dict[str, Any]:
    """Return the verified claims, or raise jwt.InvalidTokenError / AuthNotConfigured."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if alg in ASYMMETRIC_ALGORITHMS:
        base = _project_url(settings)
        if not base:
            raise AuthNotConfigured("SUPABASE_URL is required to verify ES256/RS256 tokens")
        client = _jwks_client(f"{base}/auth/v1/.well-known/jwks.json")
        try:
            signing_key = await asyncio.to_thread(client.get_signing_key_from_jwt, token)
        except PyJWKClientError as exc:
            raise jwt.InvalidTokenError(f"cannot resolve signing key: {exc}") from exc
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=AUDIENCE,
            issuer=f"{base}/auth/v1",
        )

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise AuthNotConfigured("SUPABASE_JWT_SECRET is required to verify HS256 tokens")
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=AUDIENCE,
        )

    raise jwt.InvalidTokenError(f"unsupported token algorithm: {alg!r}")

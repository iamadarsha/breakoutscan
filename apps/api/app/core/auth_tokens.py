"""Verify an access token from whichever identity provider issued it.

Supabase is verified by `supabase_auth` (its own JWKS / legacy secret). Any
other OIDC-style provider is enabled purely through configuration:

    AUTH_ISSUER    exact `iss` claim to trust (e.g. https://securetoken.google.com/<project>)
    AUTH_JWKS_URL  the provider's public key set
    AUTH_AUDIENCE  required `aud` claim (Firebase: the project id)

The issuer allowlist is exact-match and the keys always come from
configuration, never from the token, so a token can only choose *which
configured provider* verifies it — not how.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import jwt
from jwt.exceptions import PyJWKClientError

from app.core.supabase_auth import (
    ASYMMETRIC_ALGORITHMS,
    AuthNotConfigured,
    _jwks_client,
    verify_supabase_token,
)


def _generic_provider(settings: Any, issuer: str | None) -> bool:
    configured = getattr(settings, "auth_issuer", "") or ""
    return bool(configured) and issuer == configured


async def verify_access_token(token: str, settings: Any) -> dict[str, Any]:
    """Return verified claims; raise jwt.InvalidTokenError / AuthNotConfigured."""
    unverified = jwt.decode(token, options={"verify_signature": False})
    header = jwt.get_unverified_header(token)
    alg = header.get("alg")

    if _generic_provider(settings, unverified.get("iss")):
        if alg not in ASYMMETRIC_ALGORITHMS:
            raise jwt.InvalidTokenError(f"unsupported token algorithm: {alg!r}")
        jwks_url = getattr(settings, "auth_jwks_url", "")
        audience = getattr(settings, "auth_audience", "")
        if not jwks_url or not audience:
            raise AuthNotConfigured("AUTH_JWKS_URL and AUTH_AUDIENCE are required")
        client = _jwks_client(jwks_url)
        try:
            signing_key = await asyncio.to_thread(client.get_signing_key_from_jwt, token)
        except PyJWKClientError as exc:
            raise jwt.InvalidTokenError(f"cannot resolve signing key: {exc}") from exc
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=audience,
            issuer=settings.auth_issuer,
        )

    return await verify_supabase_token(token, settings)


def user_id_from_claims(claims: dict[str, Any]) -> str | None:
    """Stable UUID for the token's subject.

    Supabase subjects are already UUIDs and are returned unchanged. Other
    providers use opaque ids (Firebase: 28 chars), so those map to a
    deterministic UUIDv5 scoped by issuer — the database keeps a uuid
    user_id column whichever provider is in use.
    """
    sub = claims.get("sub")
    if not sub:
        return None
    try:
        return str(uuid.UUID(str(sub)))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{claims.get('iss', '')}|{sub}"))

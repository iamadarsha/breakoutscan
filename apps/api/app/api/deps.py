from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Optional

import jwt
from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.auth_tokens import user_id_from_claims, verify_access_token
from app.core.supabase_auth import AuthNotConfigured
from app.db.session import get_db_session

logger = logging.getLogger(__name__)


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> str:
    """Extract and verify user_id from Supabase JWT.

    Returns the user UUID string from the token's ``sub`` claim.
    """
    settings = get_settings()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization[7:]

    try:
        payload = await verify_access_token(token, settings)
    except AuthNotConfigured as exc:
        logger.warning("Auth not configured — rejecting request: %s", exc)
        raise HTTPException(status_code=500, detail="Auth not configured")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = user_id_from_claims(payload)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
    return user_id


async def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """Like get_current_user but returns None for unauthenticated requests."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None

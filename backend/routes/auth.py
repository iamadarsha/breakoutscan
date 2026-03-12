"""
Auth API routes — Upstox OAuth2 flow + Supabase JWT validation.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
import structlog

from config import settings
from data.upstox_auth import get_auth_manager, UpstoxAuthManager

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(auth: UpstoxAuthManager = Depends(get_auth_manager)):
    """Redirect to Upstox OAuth2 login page."""
    if not settings.upstox_configured:
        return {"error": "Upstox credentials not configured", "hint": "Set UPSTOX_API_KEY and UPSTOX_API_SECRET in .env"}
    login_url = auth.get_login_url()
    return RedirectResponse(url=login_url)


@router.get("/callback")
async def oauth_callback(
    code: str,
    auth: UpstoxAuthManager = Depends(get_auth_manager),
):
    """Exchange OAuth2 code for access token."""
    try:
        token_data = await auth.exchange_code_for_token(code)
        return {
            "message": "Authentication successful",
            "access_token_stored": True,
            "email": token_data.get("email"),
        }
    except Exception as e:
        log.error("oauth_callback_error", error=str(e))
        raise HTTPException(status_code=400, detail=f"Authentication failed: {e}")


@router.post("/refresh")
async def refresh_token(auth: UpstoxAuthManager = Depends(get_auth_manager)):
    """Check token status and trigger refresh if needed."""
    is_valid = await auth.is_token_valid()
    token = await auth.get_access_token()
    return {
        "is_valid": is_valid,
        "has_token": bool(token),
        "upstox_configured": settings.upstox_configured,
    }


@router.get("/status")
async def auth_status(auth: UpstoxAuthManager = Depends(get_auth_manager)):
    """Check authentication status."""
    is_valid = await auth.is_token_valid()
    return {
        "upstox_configured": settings.upstox_configured,
        "token_valid": is_valid,
        "mode": "live" if (settings.upstox_configured and is_valid) else "mock",
    }

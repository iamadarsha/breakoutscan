"""
Equifidy AI Suggestions API Routes.
GET  /api/ai-suggestions          — Get cached or fresh AI stock picks
POST /api/ai-suggestions/refresh  — Force regenerate AI picks
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/ai-suggestions", tags=["ai-suggestions"])


@router.get("")
async def get_ai_suggestions():
    """Get AI-powered stock suggestions. Returns cached if available, otherwise generates fresh."""
    from main import get_redis_client
    from services.ai_suggestions import get_cached_suggestions, generate_suggestions

    redis = get_redis_client()

    # Try cache first
    cached = await get_cached_suggestions(redis)
    if cached:
        return cached

    # Generate fresh
    result = await generate_suggestions(redis)
    if result.get("error") and not result.get("suggestions"):
        raise HTTPException(status_code=503, detail=result["error"])

    return result


@router.post("/refresh")
async def refresh_ai_suggestions():
    """Force regenerate AI stock suggestions."""
    from main import get_redis_client
    from services.ai_suggestions import generate_suggestions

    redis = get_redis_client()
    result = await generate_suggestions(redis, force=True)

    if result.get("error") and not result.get("suggestions"):
        raise HTTPException(status_code=503, detail=result["error"])

    return result

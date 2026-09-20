from __future__ import annotations

import asyncio
from datetime import datetime
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.utils.time import now_ist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-suggestions", tags=["ai-suggestions"])

# generate_suggestions()'s internal per-layer timeouts sum to a worst case
# of ~120s (see ai_suggestions.py). This must stay comfortably above that,
# or a slow-but-successful AI response gets silently truncated by this
# outer timeout before the layer itself ever gets a chance to time out.
AI_SUGGESTIONS_OUTER_TIMEOUT = 135

# Track if a background generation is already running
_generating = False


async def _background_generate():
    """Run generation in background so the endpoint returns immediately."""
    global _generating
    if _generating:
        logger.info("background_generate: already running, skipping")
        return
    _generating = True
    try:
        from app.services.ai_suggestions import generate_suggestions
        logger.info("background_generate: starting 3-layer generation")
        result = await asyncio.wait_for(generate_suggestions(), timeout=AI_SUGGESTIONS_OUTER_TIMEOUT)
        total = sum(len(result.get(k, [])) for k in ("intraday", "weekly", "monthly"))
        logger.info("background_generate: done source=%s picks=%d", result.get("source", "?"), total)
    except asyncio.TimeoutError:
        logger.error("background_generate: global %ds timeout exceeded", AI_SUGGESTIONS_OUTER_TIMEOUT)
    except Exception as e:
        logger.error("background_generate_failed: %s %s", type(e).__name__, e, exc_info=True)
    finally:
        _generating = False


_refresh_lock = asyncio.Lock()
REFRESH_REUSE_SECONDS = 300


def _age_seconds(generated_at: str | None) -> float:
    """Seconds since an ISO timestamp; infinity when missing or unparseable so we regenerate."""
    if not generated_at:
        return float("inf")
    try:
        ts = datetime.fromisoformat(generated_at)
    except ValueError:
        return float("inf")
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=now_ist().tzinfo)
    return (now_ist() - ts).total_seconds()


@router.get("")
@limiter.limit(get_settings().rate_limit_default)
async def get_ai_suggestions(request: Request, background_tasks: BackgroundTasks):
    """Return cached AI suggestions instantly. Triggers background generation if no cache."""
    try:
        from app.services.ai_suggestions import get_suggestions

        cached = await get_suggestions()
        if cached:
            return cached

        # No cache — trigger background generation and return empty immediately
        background_tasks.add_task(_background_generate)
        return {
            "intraday": [], "weekly": [], "monthly": [],
            "generated_at": now_ist().isoformat(),
            "headline_count": 0,
            "source": "pending",
            "message": "Generating AI picks in background. Refresh in ~30 seconds.",
        }
    except Exception as exc:
        logger.exception("Failed to get AI suggestions")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/refresh")
@limiter.limit(get_settings().rate_limit_ai_refresh)
async def refresh_ai_suggestions(request: Request):
    """Force regenerate AI stock suggestions (typically 3-10s via Gemini, up to ~120s worst case if every layer falls through)."""
    try:
        from app.services.ai_suggestions import generate_suggestions, get_suggestions

        # One generation at a time; anyone who queued behind it gets its fresh result instead of
        # starting another ~30s Gemini call (protects the quota when many people press Refresh).
        async with _refresh_lock:
            cached = await get_suggestions()
            if cached and _age_seconds(cached.get("generated_at")) < REFRESH_REUSE_SECONDS:
                return cached
            return await asyncio.wait_for(generate_suggestions(), timeout=AI_SUGGESTIONS_OUTER_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error("refresh_ai_suggestions: %ds timeout exceeded", AI_SUGGESTIONS_OUTER_TIMEOUT)
        raise HTTPException(status_code=504, detail="Generation timed out. Picks will be generated in background on next visit.")
    except Exception as exc:
        logger.exception("Failed to refresh AI suggestions")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/debug")
async def debug_ai_suggestions(request: Request):
    """Debug endpoint — shows what data is available for AI suggestion generation."""
    _settings = get_settings()
    if _settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")

    from app.services.redis_cache import get_redis
    from app.services.ai_suggestions import (
        _ensure_symbol_lookup, _SYMBOL_META, _SEED_PATH,
        _extract_headline_symbols, _fetch_news_headlines,
    )

    r = await get_redis()

    # Count price keys
    price_keys = []
    async for key in r.scan_iter(match="price:*", count=500):
        price_keys.append(key)

    # Count indicator keys
    ind_keys = []
    async for key in r.scan_iter(match="ind:*:1d", count=500):
        ind_keys.append(key)

    # Check seed file
    _ensure_symbol_lookup()
    seed_exists = _SEED_PATH.exists()
    seed_count = len(_SYMBOL_META)

    # Sample a price key
    sample_price = None
    if price_keys:
        raw = await r.get(price_keys[0])
        sample_price = {"key": price_keys[0], "value": raw[:200] if raw else None}

    # Check headlines
    try:
        headlines = await asyncio.wait_for(_fetch_news_headlines(), timeout=15)
    except Exception:
        headlines = []

    headline_symbols = _extract_headline_symbols(headlines) if headlines else {}

    # Check current cached result
    from app.services.ai_suggestions import get_suggestions
    cached = await get_suggestions()
    cached_info = None
    if cached:
        cached_info = {
            "source": cached.get("source"),
            "generated_at": cached.get("generated_at"),
            "picks": sum(len(cached.get(k, [])) for k in ("intraday", "weekly", "monthly")),
        }

    return {
        "price_key_count": len(price_keys),
        "indicator_key_count": len(ind_keys),
        "seed_path": str(_SEED_PATH),
        "seed_exists": seed_exists,
        "seed_symbol_count": seed_count,
        "headline_count": len(headlines),
        "headline_symbol_matches": len(headline_symbols),
        "matched_symbols": list(headline_symbols.keys())[:20],
        "sample_price": sample_price,
        "sample_price_keys": price_keys[:5],
        "sample_ind_keys": ind_keys[:5],
        "cached": cached_info,
    }

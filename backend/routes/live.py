"""
Live data API routes — indices, prices, market status, breadth.
"""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter
import redis.asyncio as aioredis
import structlog

from data.nse_fallback import get_nse_session, get_mock_indices, MOCK_STOCKS
from schemas import IndexData, LivePrice, MarketStatus, MarketBreadth

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["live"])


def get_redis() -> aioredis.Redis:
    from main import get_redis_client
    return get_redis_client()


@router.get("/indices", response_model=list[IndexData])
async def get_indices():
    """Live index data — NIFTY50, BANKNIFTY, SENSEX, etc."""
    nse = get_nse_session()
    return await nse.get_all_indices()


@router.get("/market/status", response_model=MarketStatus)
async def get_market_status():
    """Whether markets are currently open."""
    nse = get_nse_session()
    status = await nse.get_market_status()
    return MarketStatus(**status, next_open=None)


@router.get("/market/breadth", response_model=MarketBreadth)
async def get_market_breadth():
    """Advance/decline stats for current trading session."""
    # In production: compute from Redis LTP cache
    # For now: return from NSE indices data
    nse = get_nse_session()
    indices = await nse.get_all_indices()
    nifty = next((i for i in indices if "NIFTY 50" in i.get("name", "")), {})
    advances = nifty.get("advances", 1250)
    declines = nifty.get("declines", 800)
    unchanged = 2089 - advances - declines
    return MarketBreadth(
        advances=advances,
        declines=declines,
        unchanged=max(0, unchanged),
        advance_decline_ratio=round(advances / max(declines, 1), 2),
        new_52w_highs=None,
        new_52w_lows=None,
    )


@router.get("/prices")
async def get_all_prices():
    """Get live LTP for all tracked symbols from Redis cache."""
    redis = get_redis()

    try:
        # Try to get from Redis
        keys = await redis.keys("ltp:*")
        if keys:
            pipe = redis.pipeline()
            for k in keys[:200]:  # Limit to 200
                pipe.get(k)
            values = await pipe.execute()
            result = {}
            for k, v in zip(keys, values):
                if v:
                    symbol = k.decode("utf-8").replace("ltp:", "") if isinstance(k, bytes) else k.replace("ltp:", "")
                    result[symbol] = json.loads(v)
            if result:
                return result
    except Exception:
        pass

    # Fallback: return mock data
    from screener.engine import _DEMO_LTP_DATA
    return _DEMO_LTP_DATA


@router.get("/prices/{symbol}", response_model=LivePrice)
async def get_symbol_price(symbol: str):
    """Get live LTP for a single symbol."""
    redis = get_redis()
    symbol = symbol.upper()

    data = await redis.get(f"ltp:{symbol}")
    if data:
        d = json.loads(data)
        return LivePrice(symbol=symbol, **d)

    # Fallback to NSE
    nse = get_nse_session()
    quote = await nse.get_quote(symbol)
    if not quote:
        # Final fallback: mock data
        from screener.engine import _DEMO_LTP_DATA
        demo = _DEMO_LTP_DATA.get(symbol, {"ltp": 1000.0, "volume": 1000000})
        return LivePrice(symbol=symbol, ltp=demo["ltp"], volume=demo.get("volume"))

    return LivePrice(
        symbol=symbol,
        ltp=quote.get("ltp", 0),
        open=quote.get("open"),
        high=quote.get("high"),
        low=quote.get("low"),
        prev_close=quote.get("prev_close"),
        change=quote.get("change"),
        change_pct=quote.get("change_pct"),
        volume=quote.get("volume"),
    )

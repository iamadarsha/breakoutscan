"""
Watchlist API routes.
"""
from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
import redis.asyncio as aioredis
import structlog

from schemas import WatchlistItem, WatchlistAddRequest

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

# In-memory store for development (replace with Supabase in production)
_WATCHLIST: dict[str, list[str]] = {}

DEMO_USER = "demo-user"


def _get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    return x_user_id or DEMO_USER


@router.get("")
async def get_watchlist(user_id: str = Depends(_get_user_id)):
    """Get user's watchlist with live price data."""
    from screener.engine import _DEMO_STOCK_DATA, _COMPANY_NAMES, _SECTOR_MAP
    symbols = _WATCHLIST.get(user_id, list(_DEMO_STOCK_DATA.keys())[:5])

    result = []
    for sym in symbols:
        data = _DEMO_STOCK_DATA.get(sym, {})
        ltp = data.get("close", [1000.0])[0]
        prev = data.get("close", [1000.0, 990.0])
        change_pct = ((ltp - prev[1]) / prev[1] * 100) if len(prev) > 1 else 0
        result.append({
            "symbol": sym,
            "company_name": _COMPANY_NAMES.get(sym, sym),
            "ltp": round(ltp, 2),
            "change_pct": round(change_pct, 2),
            "volume": data.get("volume", [1000000])[0],
            "rsi_14": round((data.get("rsi_14") or [50])[0], 1),
            "ema20_status": "Above ▲" if ltp > (data.get("ema_20") or [ltp * 0.98])[0] else "Below ▼",
            "sector": _SECTOR_MAP.get(sym),
            "added_at": "2026-03-10T09:15:00Z",
        })
    return result


@router.post("/{symbol}")
async def add_to_watchlist(symbol: str, user_id: str = Depends(_get_user_id)):
    """Add a stock to the watchlist."""
    symbol = symbol.upper()
    if user_id not in _WATCHLIST:
        _WATCHLIST[user_id] = []
    if symbol not in _WATCHLIST[user_id]:
        _WATCHLIST[user_id].append(symbol)
    return {"message": f"{symbol} added to watchlist", "symbol": symbol}


@router.delete("/{symbol}")
async def remove_from_watchlist(symbol: str, user_id: str = Depends(_get_user_id)):
    """Remove a stock from the watchlist."""
    symbol = symbol.upper()
    if user_id in _WATCHLIST:
        _WATCHLIST[user_id] = [s for s in _WATCHLIST[user_id] if s != symbol]
    return {"message": f"{symbol} removed from watchlist"}

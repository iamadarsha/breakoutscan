"""
Stocks API routes — search, detail, OHLCV data.
"""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
import redis.asyncio as aioredis
import structlog

from data.nse_fallback import MOCK_STOCKS
from data.data_initializer import NSE_UNIVERSE, COMPANY_NAMES, SECTOR_MAP

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["stocks"])

NSE_SYMBOLS = NSE_UNIVERSE


@router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """Autocomplete search for stocks by symbol or company name."""
    q_upper = q.upper()
    results = []
    for sym in NSE_SYMBOLS:
        name = COMPANY_NAMES.get(sym, sym)
        if q_upper in sym or q_upper in name.upper():
            results.append({
                "symbol": sym,
                "company_name": name,
                "exchange": "NSE",
                "instrument_key": f"NSE_EQ|{sym}",
            })
    return results[:10]


@router.get("")
async def list_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    exchange: str = "NSE",
    sector: Optional[str] = None,
):
    """Paginated list of all tracked stocks."""
    all_stocks = [
        {
            "symbol": sym,
            "company_name": COMPANY_NAMES.get(sym, sym),
            "exchange": exchange,
            "sector": SECTOR_MAP.get(sym),
        }
        for sym in NSE_SYMBOLS
    ]
    if sector:
        all_stocks = [s for s in all_stocks if s.get("sector") == sector]

    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(all_stocks),
        "page": page,
        "page_size": page_size,
        "has_next": end < len(all_stocks),
        "items": all_stocks[start:end],
    }


@router.get("/{symbol}")
async def get_stock(symbol: str):
    """Get full stock details."""
    symbol = symbol.upper()
    return {
        "symbol": symbol,
        "company_name": COMPANY_NAMES.get(symbol, symbol),
        "exchange": "NSE",
        "sector": SECTOR_MAP.get(symbol),
    }


@router.get("/{symbol}/ohlcv")
async def get_ohlcv(
    symbol: str,
    tf: str = Query("15min", description="Timeframe: 1min, 5min, 15min, 30min, 1hr, daily"),
    bars: int = Query(200, ge=1, le=1000),
):
    """Get OHLCV data for charting — uses real Yahoo Finance data cached in Redis."""
    symbol = symbol.upper()

    # Try to get from CandleBuilder first
    from data.candle_builder import get_candle_builder
    builder = get_candle_builder()
    candles = builder.get_candles(symbol, tf, n=bars)
    if candles:
        return {"symbol": symbol, "timeframe": tf, "bars": candles}

    # Try Redis cached OHLCV from data_initializer
    from main import get_redis_client
    redis = get_redis_client()

    # Map timeframe to Redis key
    tf_key = tf
    if tf in ("1min", "5min", "15min", "30min", "1hr"):
        tf_key = "15min"  # We store intraday as 15min
    else:
        tf_key = "daily"

    try:
        raw = await redis.get(f"ohlcv:{symbol}:{tf_key}")
        if raw:
            all_bars = json.loads(raw)
            # Return requested number of bars
            return {"symbol": symbol, "timeframe": tf, "bars": all_bars[-bars:]}
    except Exception as e:
        log.warning("ohlcv_redis_fetch_failed", symbol=symbol, error=str(e))

    # Final fallback: fetch directly from yfinance
    try:
        from data.data_initializer import _fetch_yf_data, _safe
        import asyncio

        period = "5d" if tf in ("1min", "5min", "15min", "30min") else "6mo"
        interval = "15m" if tf in ("1min", "5min", "15min", "30min") else "1d"
        df = await asyncio.to_thread(_fetch_yf_data, symbol, period, interval)

        if not df.empty:
            result_bars = []
            for i in range(len(df)):
                row = df.iloc[i]
                ts = row.get("timestamp")
                result_bars.append({
                    "ts": str(ts) if ts is not None else "",
                    "open": _safe(row["open"], 0),
                    "high": _safe(row["high"], 0),
                    "low": _safe(row["low"], 0),
                    "close": _safe(row["close"], 0),
                    "volume": int(_safe(row["volume"], 0)),
                })
            return {"symbol": symbol, "timeframe": tf, "bars": result_bars[-bars:]}
    except Exception as e:
        log.warning("ohlcv_yfinance_fallback_failed", symbol=symbol, error=str(e))

    return {"symbol": symbol, "timeframe": tf, "bars": []}


@router.get("/{symbol}/fundamentals")
async def get_fundamentals(symbol: str):
    """Get fundamental data for a stock."""
    symbol = symbol.upper()
    return {
        "symbol": symbol,
        "company_name": COMPANY_NAMES.get(symbol, symbol),
        "sector": SECTOR_MAP.get(symbol),
        "exchange": "NSE",
    }

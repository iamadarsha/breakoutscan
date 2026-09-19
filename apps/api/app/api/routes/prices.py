from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.ohlcv import Ohlcv1Min, OhlcvDaily
from app.schemas.market import LivePrice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/live/{symbol}", response_model=LivePrice)
async def get_live_price(symbol: str):
    """Get current LTP for a symbol from Redis. Returns placeholder if Redis is down."""
    try:
        from app.services.redis_cache import get_json

        data = await get_json(f"price:{symbol.upper()}")
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No live price for {symbol}",
            )
        data.setdefault("symbol", symbol.upper())
        return LivePrice(**data)
    except HTTPException:
        raise
    except Exception:
        logger.warning("Redis unavailable for live price %s — returning placeholder", symbol)
        return LivePrice(symbol=symbol.upper(), ltp=0)


@router.get("/live", response_model=list[LivePrice])
async def get_batch_prices(
    symbols: str = Query(
        ..., description="Comma-separated list of symbols"
    ),
):
    """Get live prices for multiple symbols. Gracefully degrades if Redis is down."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return []
    if len(symbol_list) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 symbols per request")

    results: list[LivePrice] = []
    try:
        from app.services.redis_cache import get_json

        for sym in symbol_list:
            try:
                data = await get_json(f"price:{sym}")
                if data:
                    data.setdefault("symbol", sym)
                    results.append(LivePrice(**data))
                else:
                    results.append(LivePrice(symbol=sym, ltp=0))
            except Exception:
                results.append(LivePrice(symbol=sym, ltp=0))
    except Exception:
        logger.warning("Redis unavailable for batch prices — returning placeholders")
        results = [LivePrice(symbol=sym, ltp=0) for sym in symbol_list]
    return results


@router.get("/history/{symbol}")
async def get_price_history(
    symbol: str,
    timeframe: str = Query("1d", description="1m or 1d"),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLCV history — tries Redis cache first, falls back to DB, then yfinance."""
    symbol = symbol.upper()

    # 1. Try Redis-cached OHLCV first (populated by yahoo_finance bulk compute)
    if timeframe in ("1d", "daily"):
        try:
            from app.services.redis_cache import get_json

            cached = await get_json(f"ohlcv:{symbol}:daily")
            if cached and isinstance(cached, list) and len(cached) > 0:
                data = cached[-limit:] if len(cached) > limit else cached
                return {"symbol": symbol, "timeframe": timeframe, "count": len(data), "data": data}
        except Exception:
            pass

    # 2. DB fallback
    if timeframe == "1m":
        query = (
            select(Ohlcv1Min)
            .where(Ohlcv1Min.symbol == symbol)
            .order_by(Ohlcv1Min.ts.desc())
            .limit(limit)
        )
        if from_date:
            query = query.where(Ohlcv1Min.ts >= from_date)
        if to_date:
            query = query.where(Ohlcv1Min.ts <= to_date)
    else:
        query = (
            select(OhlcvDaily)
            .where(OhlcvDaily.symbol == symbol)
            .order_by(OhlcvDaily.date.desc())
            .limit(limit)
        )
        if from_date:
            query = query.where(OhlcvDaily.date >= from_date)
        if to_date:
            query = query.where(OhlcvDaily.date <= to_date)

    items = []
    try:
        rows = (await db.execute(query)).scalars().all()
        for r in rows:
            if timeframe == "1m":
                items.append(
                    {
                        "symbol": r.symbol,
                        "ts": r.ts.isoformat(),
                        "open": float(r.open),
                        "high": float(r.high),
                        "low": float(r.low),
                        "close": float(r.close),
                        "volume": r.volume,
                    }
                )
            else:
                items.append(
                    {
                        "symbol": r.symbol,
                        "date": r.date.isoformat(),
                        "open": float(r.open),
                        "high": float(r.high),
                        "low": float(r.low),
                        "close": float(r.close),
                        "volume": r.volume,
                        "week_high_52": float(r.week_high_52) if r.week_high_52 else None,
                        "week_low_52": float(r.week_low_52) if r.week_low_52 else None,
                    }
                )
    except Exception:
        logger.warning("DB query failed for %s, trying yfinance fallback", symbol)

    # 3. If DB also empty for daily, try fetching directly from yfinance
    if not items and timeframe in ("1d", "daily"):
        try:
            import asyncio as _asyncio

            from app.services.yahoo_finance import YFinanceProvider

            records = await _asyncio.wait_for(
                _asyncio.to_thread(YFinanceProvider.get_historical, symbol, "6mo", "1d"),
                timeout=15.0,
            )
            if records:
                from datetime import datetime as _dt

                for rec in records[-limit:]:
                    epoch = int(_dt.strptime(rec["date"], "%Y-%m-%d").timestamp()) if isinstance(rec.get("date"), str) else 0
                    items.append({
                        "time": epoch,
                        "open": rec["open"],
                        "high": rec["high"],
                        "low": rec["low"],
                        "close": rec["close"],
                        "volume": rec["volume"],
                    })
        except Exception:
            logger.warning("yfinance fallback also failed for %s", symbol)

    return {"symbol": symbol, "timeframe": timeframe, "count": len(items), "data": items}


@router.get("/indicators/{symbol}")
async def get_indicators(symbol: str):
    """Current daily technical indicators for a symbol, from the `ind:{symbol}:1d` hash."""
    from app.services.redis_cache import hget_all
    from app.utils.redis_keys import indicator_key

    sym = symbol.upper()
    raw = await hget_all(indicator_key(sym, "1d"))
    if not raw:
        raise HTTPException(status_code=404, detail=f"No indicators for {sym}")

    out: dict[str, float | str | None] = {"symbol": sym}
    for field, value in raw.items():
        try:
            out[field] = float(value)
        except (TypeError, ValueError):
            out[field] = None
    return out

from __future__ import annotations

import logging
from datetime import datetime, time, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.stock import Stock
from app.market.regime import MarketRegime, compute_market_regime
from app.schemas.market import (
    IndexData,
    MarketBreadth,
    MarketStatus,
    RegimeOut,
    SectorPerformance,
)
from app.utils.redis_keys import regime_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


async def _get_holiday_dates() -> set[str]:
    """Read the cached NSE holiday calendar (ISO date strings) from Redis.

    Fails open (empty set) on a cache miss rather than blocking this
    route on a live NSE call — `nse_poller.py` refreshes the cache
    roughly daily. An empty result just means "no known holiday today",
    the same behavior as before this check existed.
    """
    from app.services.redis_cache import get_json
    from app.utils.redis_keys import market_holidays_key

    try:
        cached = await get_json(market_holidays_key())
        return set(cached) if cached else set()
    except Exception:
        return set()


def _next_open_skipping_weekends_and_holidays(
    from_dt: datetime, holidays: set[str]
) -> datetime:
    """Roll *from_dt* forward to the next weekday that isn't a known holiday."""
    candidate = from_dt
    for _ in range(10):  # generous bound — holidays never cluster this long
        if candidate.weekday() < 5 and candidate.date().isoformat() not in holidays:
            return candidate.replace(hour=9, minute=15, second=0, microsecond=0)
        candidate += timedelta(days=1)
    return candidate.replace(hour=9, minute=15, second=0, microsecond=0)


async def _market_status_now() -> MarketStatus:
    """Determine market open/close status based on IST time AND the NSE
    holiday calendar — a clock-only check would report "open" on trading
    holidays (caught live on Ganesh Chaturthi, 2026-09-14, where NSE's own
    market_status() disagreed with a naive weekday+time check)."""
    now_ist = datetime.now(IST)
    current_time = now_ist.time()
    weekday = now_ist.weekday()
    holidays = await _get_holiday_dates()
    is_holiday = now_ist.date().isoformat() in holidays

    # Weekend or trading holiday
    if weekday >= 5 or is_holiday:
        next_open_dt = _next_open_skipping_weekends_and_holidays(
            now_ist + timedelta(days=1), holidays
        )
        message = "Market is closed (weekend)" if weekday >= 5 else "Market is closed (holiday)"
        return MarketStatus(
            is_open=False,
            status="closed",
            next_open=next_open_dt,
            message=message,
        )

    if current_time < time(9, 0):
        next_open_dt = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        return MarketStatus(
            is_open=False,
            status="closed",
            next_open=next_open_dt,
            message="Market opens at 9:15 AM IST",
        )

    if time(9, 0) <= current_time < MARKET_OPEN:
        next_open_dt = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        return MarketStatus(
            is_open=False,
            status="pre_open",
            next_open=next_open_dt,
            message="Pre-open session",
        )

    if MARKET_OPEN <= current_time < MARKET_CLOSE:
        next_close_dt = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        return MarketStatus(
            is_open=True,
            status="open",
            next_close=next_close_dt,
            message="Market is open",
        )

    # After close
    next_open_dt = _next_open_skipping_weekends_and_holidays(
        now_ist + timedelta(days=1), holidays
    )
    return MarketStatus(
        is_open=False,
        status="post_close",
        next_open=next_open_dt,
        message="Market is closed for the day",
    )


@router.get("/status", response_model=MarketStatus)
async def market_status():
    """Get current market open/closed status."""
    return await _market_status_now()


@router.get("/breadth", response_model=MarketBreadth)
async def market_breadth():
    """Get advance/decline/unchanged counts from Redis."""
    try:
        from app.services.redis_cache import get_json

        data = await get_json("market:breadth")
        if data:
            return MarketBreadth(**data)
    except Exception:
        pass

    # Fallback: compute from cached prices
    advances = declines = unchanged = 0
    try:
        from app.services.redis_cache import get_redis

        redis = await get_redis()
        keys = await redis.keys("price:*")
        for key in keys:
            from app.services.redis_cache import get_json as _gj

            price_data = await _gj(key.decode() if isinstance(key, bytes) else key)
            if price_data:
                change = price_data.get("change_pct", 0) or 0
                if change > 0:
                    advances += 1
                elif change < 0:
                    declines += 1
                else:
                    unchanged += 1
    except Exception:
        pass

    total = advances + declines + unchanged
    ratio = round(advances / declines, 2) if declines > 0 else None
    return MarketBreadth(
        advances=advances,
        declines=declines,
        unchanged=unchanged,
        total=total,
        advance_decline_ratio=ratio,
    )


MAJOR_INDICES = {
    "NIFTY 50", "NIFTY BANK", "NIFTY IT", "NIFTY PHARMA",
    "NIFTY AUTO", "NIFTY FMCG", "INDIA VIX", "NIFTY MIDCAP 50",
}


@router.get("/indices", response_model=list[IndexData])
async def market_indices():
    """Get major NSE index values."""
    # Try Redis cache first (populated by NSE poller)
    try:
        from app.services.redis_cache import get_json

        cached = await get_json("market:indices")
        if cached:
            return [IndexData(**idx) for idx in cached]
    except Exception:
        pass

    # Fallback: fetch directly from NSE
    try:
        from app.services.nse_fallback import NSEClient

        client = NSEClient()
        raw = await client.get_indices()
        data = raw.get("data", []) if isinstance(raw, dict) else []
        results = []
        for idx in data:
            name = idx.get("index", "")
            if name in MAJOR_INDICES:
                results.append(
                    IndexData(
                        name=name,
                        symbol=name.replace(" ", ""),
                        last=idx.get("last", 0),
                        change=idx.get("change", 0),
                        change_pct=idx.get("percentChange", 0),
                        open=idx.get("open"),
                        high=idx.get("high"),
                        low=idx.get("low"),
                        prev_close=idx.get("previousClose"),
                    )
                )
        return results
    except Exception as exc:
        logger.exception("Failed to fetch indices")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/regime", response_model=RegimeOut)
async def market_regime():
    """Get the current market regime classification plus its raw component
    readings. Reads the Redis key the poller writes every cycle; if that's
    absent/expired, recomputes on-demand from `market:indices` /
    `market:breadth` the same way `/breadth`'s fallback does today."""
    try:
        from app.services.redis_cache import get_json

        cached = await get_json(regime_key())
        if cached:
            return RegimeOut(
                regime=cached.get("regime", MarketRegime.CHOPPY.value),
                vix_level=cached.get("vix_level"),
                nifty_change_pct=cached.get("nifty_change_pct", 0.0),
                advance_decline_ratio=cached.get("advance_decline_ratio", 0.0),
                advances=cached.get("advances", 0),
                declines=cached.get("declines", 0),
                unchanged=cached.get("unchanged", 0),
                extra=cached.get("extra", {}),
            )
    except Exception:
        pass

    # Fallback: recompute on-demand from the same market:indices /
    # market:breadth data the poller already writes, same convention as
    # /breadth's fallback above.
    try:
        from app.services.redis_cache import get_json

        indices = await get_json("market:indices") or []
        breadth = await get_json("market:breadth") or {}
        result = compute_market_regime(indices, breadth)
        return RegimeOut(
            regime=result.regime.value,
            vix_level=result.vix_level,
            nifty_change_pct=result.nifty_change_pct,
            advance_decline_ratio=result.advance_decline_ratio,
            advances=result.advances,
            declines=result.declines,
            unchanged=result.unchanged,
            extra=result.extra,
        )
    except Exception as exc:
        logger.exception("Failed to compute market regime")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors", response_model=list[SectorPerformance])
async def market_sectors(
    db: AsyncSession = Depends(get_db),
):
    """Get sector-wise performance summary."""
    try:
        from app.services.redis_cache import get_json

        cached = await get_json("market:sectors")
        if cached:
            return [SectorPerformance(**s) for s in cached]
    except Exception:
        pass

    # Compute from the sector column and live prices already in Redis.
    from app.services.sector_stats import compute_sector_performance

    rows = (
        await db.execute(
            select(Stock.symbol, Stock.sector).where(
                Stock.sector.isnot(None), Stock.is_active.is_(True)
            )
        )
    ).all()
    sector_by_symbol = {sym: sec for sym, sec in rows if sec}

    change_by_symbol: dict[str, float] = {}
    try:
        import json

        from app.services.redis_cache import get_redis

        redis = await get_redis()
        symbols = list(sector_by_symbol)
        raws = await redis.mget([f"price:{s}" for s in symbols]) if symbols else []
        for sym, raw in zip(symbols, raws):
            if not raw:
                continue
            try:
                change = json.loads(raw).get("change_pct")
            except (ValueError, AttributeError):
                continue
            if change is not None:
                change_by_symbol[sym] = float(change)
    except Exception:
        logger.warning("sector performance: Redis price read failed", exc_info=True)

    computed = compute_sector_performance(sector_by_symbol, change_by_symbol)
    if computed:
        try:
            from app.services.redis_cache import set_json

            await set_json("market:sectors", computed, ttl=60)
        except Exception:
            pass
    return [SectorPerformance(**s) for s in computed]

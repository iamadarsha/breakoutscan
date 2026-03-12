"""
Opening Range Breakout (ORB) logic.
Computes and stores the Opening Range for each stock every day at 9:30 AM IST.
ORB = High / Low of the first 15 minutes (9:15 – 9:30 AM) of trading.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis.asyncio as aioredis
import structlog

from data.candle_builder import CandleBuilder, IST

log = structlog.get_logger(__name__)

ORB_PREFIX = "orb:"
ORB_TTL = 86400  # 24 hours (reset next day)


async def compute_and_store_orb(
    redis: aioredis.Redis,
    candle_builder: CandleBuilder,
    symbols: list[str],
):
    """
    Called at 9:30 AM IST — computes Opening Range for all symbols.
    ORB = max(high) and min(low) of all 5-min candles from 9:15 to 9:30 AM.
    """
    now = datetime.now(tz=IST)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    orb_end = now.replace(hour=9, minute=30, second=0, microsecond=0)

    pipe = redis.pipeline()
    orb_count = 0

    for symbol in symbols:
        candles = candle_builder.snapshot_for_screener(symbol, "5min", n=10)

        # Filter candles within opening range (9:15 - 9:30)
        orb_candles = [
            c for c in candles
            if market_open <= c.ts < orb_end
        ]

        if not orb_candles:
            continue

        orb_high = max(c.high for c in orb_candles)
        orb_low = min(c.low for c in orb_candles)
        orb_open = orb_candles[0].open if orb_candles else None
        orb_volume = sum(c.volume for c in orb_candles)

        orb_data = {
            "high": orb_high,
            "low": orb_low,
            "open": orb_open,
            "volume": orb_volume,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

        pipe.setex(f"{ORB_PREFIX}{symbol}", ORB_TTL, json.dumps(orb_data))
        orb_count += 1

    if orb_count > 0:
        await pipe.execute()
        log.info("orb_computed", symbol_count=orb_count)
    else:
        log.warning("orb_no_data", message="No opening range data available — market may not have opened yet")


async def get_orb(redis: aioredis.Redis, symbol: str) -> Optional[dict]:
    """Retrieve stored ORB data for a symbol."""
    data = await redis.get(f"{ORB_PREFIX}{symbol}")
    return json.loads(data) if data else None


async def evaluate_orb_breakout(
    symbol: str,
    redis: aioredis.Redis,
    candle_builder: CandleBuilder,
    volume_multiplier: float = 2.0,
) -> tuple[bool, list[str]]:
    """
    Check if a symbol has broken above its Opening Range High.
    Returns (passed, matched_conditions).
    """
    now = datetime.now(tz=IST)
    orb_end = now.replace(hour=9, minute=30, second=0, microsecond=0)

    # ORB scan only active after 9:30 AM
    if now < orb_end:
        return False, []

    orb = await get_orb(redis, symbol)
    if not orb:
        return False, []

    orb_high = orb.get("high", 0)
    if not orb_high:
        return False, []

    # Get current candle data
    candles = candle_builder.snapshot_for_screener(symbol, "5min", n=3)
    if not candles:
        return False, []

    current = candles[-1]
    ltp = current.close
    volume = current.volume

    # Check conditions
    matched = []
    conditions_met = True

    # Condition 1: Price above ORB high (with 0.1% buffer)
    if ltp > orb_high * 1.001:
        matched.append(f"Close ({ltp:.2f}) > ORB High ({orb_high:.2f})")
    else:
        conditions_met = False

    # Condition 2: Volume check (use Redis for volume SMA)
    vol_data = await redis.get(f"indicators:{symbol}:5min")
    if vol_data:
        import json
        indicators = json.loads(vol_data)
        vol_sma = (indicators.get("volume_sma_20") or [0])[0]
        if vol_sma and volume >= vol_sma * volume_multiplier:
            matched.append(f"Volume ({volume:,}) > {volume_multiplier}x Average ({vol_sma:,.0f})")
        else:
            conditions_met = False

    return conditions_met, matched


async def get_all_orb_data(redis: aioredis.Redis, symbols: list[str]) -> dict[str, dict]:
    """Batch-fetch ORB data for multiple symbols."""
    pipe = redis.pipeline()
    for s in symbols:
        pipe.get(f"{ORB_PREFIX}{s}")
    results = await pipe.execute()

    import json
    return {
        s: json.loads(r) if r else {}
        for s, r in zip(symbols, results)
    }

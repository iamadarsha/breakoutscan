"""Keep the database inside a free-tier size budget.

1-minute candles are ~46 MB/day for the 500-symbol universe and only the most
recent sessions are ever read (the breakout engine needs a few hours of bars,
the charts use the daily table), so older rows are pure cost. Deletes run in
small batches so they never hold a long lock or burst the connection pool.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

OHLCV_1MIN_KEEP_DAYS = 3
BREAKOUT_EVENTS_KEEP_DAYS = 14
DELETE_BATCH_ROWS = 20_000
STARTUP_DELAY_SECONDS = 600
INTERVAL_SECONDS = 24 * 60 * 60


async def _delete_in_batches(table: str, column: str, cutoff: datetime) -> int:
    # table/column are module constants, never user input.
    statement = text(
        f"DELETE FROM {table} WHERE ctid IN "
        f"(SELECT ctid FROM {table} WHERE {column} < :cutoff LIMIT :n)"
    )
    total = 0
    while True:
        async with SessionLocal() as session:
            result = await session.execute(statement, {"cutoff": cutoff, "n": DELETE_BATCH_ROWS})
            await session.commit()
        deleted = result.rowcount or 0
        total += deleted
        if deleted < DELETE_BATCH_ROWS:
            return total
        await asyncio.sleep(0.5)


async def prune_once(now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    candles = await _delete_in_batches(
        "ohlcv_1min", "ts", now - timedelta(days=OHLCV_1MIN_KEEP_DAYS)
    )
    events = await _delete_in_batches(
        "breakout_events", "triggered_at", now - timedelta(days=BREAKOUT_EVENTS_KEEP_DAYS)
    )
    # Raw analytics events: roll the boundary days up first so the permanent daily totals are complete,
    # then delete. (Rollups are also refreshed every 30 minutes; this is a safety net.)
    from app.services.analytics import IST, rollup_days

    analytics_cutoff = now - timedelta(days=get_settings().analytics_raw_keep_days)
    await rollup_days(days_back=2, today=analytics_cutoff.astimezone(IST).date())
    analytics = await _delete_in_batches("analytics_events", "ts", analytics_cutoff)
    logger.info(
        "data_retention pruned ohlcv_1min=%d breakout_events=%d analytics_events=%d", candles, events, analytics
    )
    return {"ohlcv_1min": candles, "breakout_events": events, "analytics_events": analytics}


async def data_retention_loop() -> None:
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        try:
            await prune_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("data_retention cycle failed")
        await asyncio.sleep(INTERVAL_SECONDS)

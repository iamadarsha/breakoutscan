"""Session-aware candle aggregation with batched persistence.

Supersedes `app.services.candle_builder.CandleBuilder`: reuses the same
Redis-hash-per-symbol+timeframe current-candle store, but completed
1-minute candles are buffered in-process and flushed in a single bulk
upsert on a size threshold, instead of one DB transaction per candle
(the Phase 1-audited persistence bug). Persistence failures are raised to
the caller — who logs with full context and can alert — rather than
silently swallowed.
"""

from __future__ import annotations

import asyncio
import random
import time as _time
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models.ohlcv import Ohlcv1Min, OhlcvDaily
from app.db.session import SessionLocal
from app.services.redis_cache import hget_all, hset_dict
from app.utils.decimals import safe_decimal
from app.utils.redis_keys import TTL_CANDLE_CURRENT, candle_current_key
from app.utils.time import IST, get_candle_boundary

log = structlog.get_logger(__name__)

TIMEFRAMES = ("1min", "5min", "15min")

_FLUSH_BATCH_SIZE = 200

# Hard cap on the in-memory retry buffer. Without this, a genuinely
# unreachable DB (not a transient blip) makes flush_pending() put the
# whole failing batch back every cycle while on_tick() keeps appending —
# unbounded growth on a memory-constrained VM. Caught live (2026-09-14):
# no Postgres was ever connected in this deployment, so every single
# flush attempt failed and the buffer grew continuously, consuming
# memory hand over fist on a box that had already OOM-crashed twice
# that same day. Once the cap is hit, the oldest candles are dropped
# (most-recent-first is more useful than oldest-first for a live system)
# rather than growing forever.
_PENDING_1MIN_MAX = _FLUSH_BATCH_SIZE * 5

# Bounded exponential backoff for retrying a failed persistence batch.
# Without this, on_tick() re-triggers flush_pending() every time the
# pending buffer crosses _FLUSH_BATCH_SIZE again (roughly every ~24s
# across the full 500-symbol universe) — during a sustained DB outage
# that means a fresh connection attempt every ~24s hammering a database
# that's already down, on top of the memory-leak risk _PENDING_1MIN_MAX
# already guards against. Backoff resets only once a write actually
# succeeds, per the standard "don't retry a dead dependency on every tick"
# pattern — never on a timer alone.
_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 60.0)

# Minimum number of candles required to compute the slowest indicator (SMA-200)
_HISTORY_CANDLE_LIMIT = 210


# Bars of aggregated history returned for 5/15-minute requests, and how far back
# the source 1-minute rows are read to build them.
_AGG_BAR_LIMIT = 60
_AGG_LOOKBACK_DAYS = 5
_TF_MINUTES = {"5min": 5, "15min": 15}


async def _fetch_aggregated_candles(symbol: str, minutes: int) -> list[dict[str, Any]]:
    """5/15-minute bars aggregated inside Postgres from the stored 1-minute rows.

    Doing the GROUP BY in the database returns ~60 compact rows per symbol
    instead of hundreds of raw 1-minute rows: it is both the correct
    timeframe (raw 1-minute rows were previously handed back labelled
    "15min") and roughly an order of magnitude less data over the wire.
    The still-forming newest bucket is dropped so only complete bars return.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import text

    now_utc = datetime.now(timezone.utc)
    stmt = text(
        """
        SELECT date_bin(make_interval(mins => :m), ts, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS bucket,
               (array_agg(open ORDER BY ts))[1]      AS open,
               max(high)                             AS high,
               min(low)                              AS low,
               (array_agg(close ORDER BY ts DESC))[1] AS close,
               sum(volume)::bigint                   AS volume
        FROM ohlcv_1min
        WHERE symbol = :symbol AND ts >= :since
        GROUP BY bucket
        ORDER BY bucket DESC
        LIMIT :n
        """
    )
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                stmt,
                {
                    "m": minutes,
                    "symbol": symbol,
                    "since": now_utc - timedelta(days=_AGG_LOOKBACK_DAYS),
                    "n": _AGG_BAR_LIMIT + 1,
                },
            )
        ).all()

    bars = [
        {
            "ts": r.bucket.isoformat(),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": int(r.volume),
        }
        for r in rows
        if r.bucket + timedelta(minutes=minutes) <= now_utc
    ]
    return list(reversed(bars[:_AGG_BAR_LIMIT]))


async def fetch_candle_history(symbol: str, timeframe: str) -> list[dict[str, Any]]:
    """Load recent candles from Postgres, oldest-first.

    Moved here from the now-deleted `app.services.indicator_engine` (Phase
    2.2) — this was the one piece of that module still in active use, via
    `screener_engine.py`'s DSL historical-offset/rolling-function fetches.
    """
    if timeframe in _TF_MINUTES:
        return await _fetch_aggregated_candles(symbol, _TF_MINUTES[timeframe])

    from sqlalchemy import select

    is_intraday = timeframe == "1min"
    async with SessionLocal() as session:
        if is_intraday:
            stmt = (
                select(Ohlcv1Min)
                .where(Ohlcv1Min.symbol == symbol)
                .order_by(Ohlcv1Min.ts.desc())
                .limit(_HISTORY_CANDLE_LIMIT)
            )
            rows = (await session.execute(stmt)).scalars().all()
        else:
            stmt = (
                select(OhlcvDaily)
                .where(OhlcvDaily.symbol == symbol)
                .order_by(OhlcvDaily.date.desc())
                .limit(_HISTORY_CANDLE_LIMIT)
            )
            rows = (await session.execute(stmt)).scalars().all()

    candles: list[dict[str, Any]] = [
        {
            "ts": (r.ts if is_intraday else r.date).isoformat(),
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": int(r.volume),
        }
        for r in reversed(rows)
    ]
    return candles


class CandlePersistenceError(Exception):
    """Raised when a batch of completed candles fails to persist."""


class CandleEngine:
    """Aggregates ticks into multi-timeframe OHLCV candles.

    Callers get completed candles back from `on_tick` immediately for
    pushing onto the event bus / in-memory state; 1-minute candles are
    also queued for batched database persistence via `flush_pending()`.
    """

    def __init__(self) -> None:
        self._pending_1min: list[dict[str, Any]] = []
        self._flush_lock = asyncio.Lock()
        # -1 = no active backoff (never failed, or last attempt succeeded).
        self._backoff_index = -1
        self._next_attempt_at = 0.0

    async def on_tick(
        self,
        symbol: str,
        ltp: float,
        volume_delta: int,
        ts: datetime,
    ) -> list[dict[str, Any]]:
        """Process one tick's price + **delta** volume (e.g. `ltq`, never `vtt`).

        Returns completed candle dicts, one per timeframe that rolled over.
        """
        completed: list[dict[str, Any]] = []

        for tf in TIMEFRAMES:
            boundary = get_candle_boundary(ts, tf)
            key = candle_current_key(symbol, tf)
            candle = await self._get_current(key)

            if candle is None or candle["boundary"] != boundary.isoformat():
                if candle is not None:
                    done = self._finalise(candle, symbol, tf)
                    completed.append(done)
                    if tf == "1min":
                        self._pending_1min.append(done)
                candle = self._new_candle(boundary, ltp, volume_delta)
            else:
                candle = self._update(candle, ltp, volume_delta)

            await self._save_current(key, candle)

        if len(self._pending_1min) >= _FLUSH_BATCH_SIZE:
            await self.flush_pending()

        return completed

    async def flush_pending(self) -> int:
        """Bulk-upsert any buffered 1-minute candles. Returns rows written.

        Raises `CandlePersistenceError` on failure (and puts the batch back
        for a later retry) instead of swallowing it — the old
        `CandleBuilder._persist_1min` logged and dropped failed writes.

        While a backoff window from a prior failure is active, this skips
        the actual DB round-trip entirely (still raises, so callers/tests
        see the same failure contract) rather than hammering a dependency
        that's already known to be down.
        """
        async with self._flush_lock:
            if not self._pending_1min:
                return 0
            now = _time.monotonic()
            if self._backoff_index >= 0 and now < self._next_attempt_at:
                remaining = self._next_attempt_at - now
                raise CandlePersistenceError(
                    f"skipping persistence attempt — backing off after a prior failure "
                    f"(retry in {remaining:.0f}s)"
                )
            batch, self._pending_1min = self._pending_1min, []

        rows = []
        for candle in batch:
            ts = datetime.fromisoformat(candle["ts"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=IST)
            rows.append(
                {
                    "symbol": candle["symbol"],
                    "ts": ts,
                    "open": safe_decimal(candle["open"], Decimal(0)),
                    "high": safe_decimal(candle["high"], Decimal(0)),
                    "low": safe_decimal(candle["low"], Decimal(0)),
                    "close": safe_decimal(candle["close"], Decimal(0)),
                    "volume": candle["volume"],
                }
            )

        try:
            async with SessionLocal() as session:
                stmt = pg_insert(Ohlcv1Min).values(rows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "ts"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                    },
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as exc:
            dropped = 0
            async with self._flush_lock:
                merged = batch + self._pending_1min
                if len(merged) > _PENDING_1MIN_MAX:
                    dropped = len(merged) - _PENDING_1MIN_MAX
                    merged = merged[:_PENDING_1MIN_MAX]
                self._pending_1min = merged
            if dropped:
                log.error(
                    "candle_batch_persist_buffer_capped",
                    dropped=dropped,
                    buffer_size=_PENDING_1MIN_MAX,
                    reason="DB unreachable long enough to exceed the retry buffer cap",
                )

            self._backoff_index = min(self._backoff_index + 1, len(_BACKOFF_SECONDS) - 1)
            base_delay = _BACKOFF_SECONDS[self._backoff_index]
            jitter = random.uniform(0, base_delay * 0.3)
            self._next_attempt_at = _time.monotonic() + base_delay + jitter

            log.error(
                "candle_batch_persist_failed",
                count=len(rows),
                error=str(exc),
                next_retry_in_seconds=round(base_delay + jitter, 1),
            )
            raise CandlePersistenceError(f"failed to persist {len(rows)} candles") from exc

        # Reset backoff only on an actual successful write, per spec —
        # never reset it on a timer alone.
        self._backoff_index = -1
        self._next_attempt_at = 0.0

        log.debug("candle_batch_persisted", count=len(rows))
        return len(rows)

    def pending_count(self) -> int:
        return len(self._pending_1min)

    # ------------------------------------------------------------------
    # Internal helpers — candle arithmetic ported from CandleBuilder
    # ------------------------------------------------------------------

    @staticmethod
    def _new_candle(boundary: datetime, ltp: float, volume: int) -> dict[str, Any]:
        return {
            "boundary": boundary.isoformat(),
            "open": str(ltp),
            "high": str(ltp),
            "low": str(ltp),
            "close": str(ltp),
            "volume": str(volume),
        }

    @staticmethod
    def _update(candle: dict[str, Any], ltp: float, volume: int) -> dict[str, Any]:
        price = Decimal(str(ltp))
        candle["close"] = str(price)
        if price > Decimal(candle["high"]):
            candle["high"] = str(price)
        if price < Decimal(candle["low"]):
            candle["low"] = str(price)
        candle["volume"] = str(int(candle["volume"]) + volume)
        return candle

    @staticmethod
    def _finalise(candle: dict[str, Any], symbol: str, tf: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "timeframe": tf,
            "ts": candle["boundary"],
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": int(candle["volume"]),
        }

    @staticmethod
    async def _get_current(key: str) -> dict[str, Any] | None:
        data = await hget_all(key)
        return data if data else None

    @staticmethod
    async def _save_current(key: str, candle: dict[str, Any]) -> None:
        await hset_dict(key, candle, ttl=TTL_CANDLE_CURRENT)

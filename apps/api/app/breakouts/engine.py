"""Breakout engine orchestration.

Runs as a periodic scan loop (30s cadence, matching `nse_poller.POLL_INTERVAL`)
reading `price:{symbol}` + `ind:{symbol}:1d` + candle history — deliberately
decoupled from which realtime feed (Upstox live tick or NSE fallback)
populated that data, so breakout detection survives feed failover instead of
going dark exactly when volatility (and false-breakout risk) is highest.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace
from datetime import datetime
from functools import lru_cache
from typing import Any

import structlog

from app.breakouts.dedupe import should_notify
from app.breakouts.detectors import bollinger_bandwidth, classify_event, is_bollinger_squeeze
from app.breakouts.levels import (
    donchian_levels,
    ema_cross_reference,
    fifty_two_week_levels,
    inside_bar_levels,
    macd_cross_reference,
    nr_levels,
    orb_levels,
    pdh_pdl_levels,
    volume_breakout_level,
    vwap_levels,
)
from app.breakouts.persistence import publish_alert_trigger, record_alert_history, record_breakout_event
from app.breakouts.scoring import compute_dna_score
from app.breakouts.state_machine import DEFAULT_CONFIGS, BreakoutStateStore
from app.breakouts.types import BreakoutSignal, BreakoutStatus, Direction, TriggerType
from app.market.candles import fetch_candle_history
from app.market.indicators import SymbolIndicatorState
from app.market.pipeline import get_candle_engine, get_market_state
from app.services.redis_cache import get_json, get_redis, hget_all
from app.utils.decimals import safe_decimal
from app.utils.redis_keys import indicator_key
from app.utils.time import IST, get_candle_boundary, market_open_today, now_ist

log = structlog.get_logger(__name__)

BREAKOUT_SCAN_INTERVAL = 30  # seconds — matches nse_poller.POLL_INTERVAL
# Lowered from 20 on a 498MB-RAM VM after live testing (2026-09-15): firing
# up to 20 concurrent symbol scans meant up to 20 concurrent DB checkouts
# whenever several symbols signalled in the same cycle, producing real
# QueuePool timeouts. 4 bounds both CPU burst and DB demand at the source
# instead of compensating with a larger connection pool.
_MAX_CONCURRENT_SYMBOL_SCANS = 4
# The universe is processed in chunks of this size, with a short pause
# between chunks, so 500 symbols don't get scheduled as one instantaneous
# burst — full coverage still completes well within BREAKOUT_SCAN_INTERVAL.
_SCAN_CHUNK_SIZE = 50
_SCAN_CHUNK_DELAY_SECONDS = 1.0
_LEVEL_TIMEFRAME = "15min"
_MIN_HISTORY_FOR_STRUCTURAL_TRIGGERS = 4  # NR4's minimum
_BANDWIDTH_HISTORY_LEN = 30


@lru_cache(maxsize=1)
def get_breakout_state_store() -> BreakoutStateStore:
    return BreakoutStateStore()


@lru_cache(maxsize=1)
def _indicator_states() -> dict[str, SymbolIndicatorState]:
    return {}


@lru_cache(maxsize=1)
def _last_indicator_snapshot() -> dict[str, dict[str, Any]]:
    return {}


@lru_cache(maxsize=1)
def _last_seen_candle_ts() -> dict[str, str]:
    return {}


@lru_cache(maxsize=1)
def _bandwidth_history() -> dict[str, deque]:
    return {}


async def _get_universe_symbols() -> list[str]:
    redis = await get_redis()
    symbols = await redis.smembers("universe:nifty500")
    return list(symbols)


async def _candles_for(symbol: str, timeframe: str) -> list[dict[str, Any]]:
    """`MarketState`'s in-memory ring buffer first (fed by `CandleEngine` on
    either feed); Postgres `fetch_candle_history()` as a cold-start fallback
    when the in-memory buffer doesn't have enough bars yet."""
    state = get_market_state().get(symbol)
    if state is not None:
        candles = state.candles(timeframe)
        if len(candles) >= _MIN_HISTORY_FOR_STRUCTURAL_TRIGGERS:
            return candles
    return await fetch_candle_history(symbol, timeframe)


def _advance_indicator_state(symbol: str, candles_15min: list[dict[str, Any]]) -> dict[str, Any]:
    """Feed only genuinely new completed 15min bars into this symbol's
    `SymbolIndicatorState`; return the latest emitted flat indicator dict
    (or the last-known snapshot if nothing new completed this cycle)."""
    if not candles_15min:
        return _last_indicator_snapshot().get(symbol, {})

    state = _indicator_states().setdefault(symbol, SymbolIndicatorState())
    last_seen = _last_seen_candle_ts().get(symbol)  # stored as a comparable UTC isoformat string

    def _sort_key(candle: dict[str, Any]) -> str:
        raw_ts = candle.get("ts")
        try:
            return datetime.fromisoformat(str(raw_ts)).astimezone(IST).isoformat()
        except (ValueError, TypeError):
            return ""

    new_bars = [c for c in candles_15min if _sort_key(c) > (last_seen or "")]

    result = _last_indicator_snapshot().get(symbol, {})
    for candle in new_bars:
        result = state.update(candle)
        _last_seen_candle_ts()[symbol] = _sort_key(candle)

    _last_indicator_snapshot()[symbol] = result
    return result


async def _scan_symbol(symbol: str) -> None:
    price_data = await get_json(f"price:{symbol}")
    if not price_data:
        return
    current_price = safe_decimal(price_data.get("ltp"))
    if current_price is None:
        return

    ind_1d = await hget_all(indicator_key(symbol, "1d"))
    # CandleEngine only appends a candle to MarketState/Postgres once it has
    # fully rolled over — the in-progress bar lives separately in Redis
    # (candle_current_key), so every candle returned here is already
    # complete; no "drop the last one" slicing needed.
    completed_15min = await _candles_for(symbol, _LEVEL_TIMEFRAME)
    ind_live = _advance_indicator_state(symbol, completed_15min)

    now = now_ist()
    store = get_breakout_state_store()

    # ---- level-vs-price triggers (share the generic classify_event path) ----
    level_batches: list[tuple[TriggerType, str, Any]] = []
    for level in pdh_pdl_levels(ind_1d):
        level_batches.append((level.trigger_type, "price", level))
    for level in fifty_two_week_levels(ind_1d):
        level_batches.append((level.trigger_type, "price", level))
    for level in donchian_levels(completed_15min):
        level_batches.append((level.trigger_type, "price", level))
    for level in nr_levels(completed_15min, 4):
        level_batches.append((level.trigger_type, "price", level))
    for level in nr_levels(completed_15min, 7):
        level_batches.append((level.trigger_type, "price", level))
    for level in inside_bar_levels(completed_15min):
        level_batches.append((level.trigger_type, "price", level))
    for level in vwap_levels(ind_live):
        level_batches.append((level.trigger_type, "price", level))

    # Seed the opening range from today's first 15-min bar (09:15-09:30 IST)
    # the first time it shows up in our candle history; on every other cycle
    # this just re-reads the already-stored range. Timestamps may arrive as
    # UTC-aware (Postgres) or IST-aware (CandleEngine's in-memory ring
    # buffer) — always normalize via astimezone() before comparing, never
    # compare raw ISO strings.
    opening_boundary = market_open_today()
    orb_candle = None
    for c in completed_15min:
        raw_ts = c.get("ts")
        if not raw_ts:
            continue
        try:
            candle_ts = datetime.fromisoformat(str(raw_ts)).astimezone(IST)
        except ValueError:
            continue
        if candle_ts == opening_boundary:
            orb_candle = c
            break
    for level in await orb_levels(symbol, orb_candle):
        level_batches.append((level.trigger_type, "price", level))

    volume_level = volume_breakout_level(ind_1d)
    current_volume = safe_decimal(price_data.get("volume"))
    if volume_level is not None and current_volume is not None:
        level_batches.append((volume_level.trigger_type, "volume", volume_level))

    signals: list[BreakoutSignal] = []

    for trigger_type, value_kind, level in level_batches:
        compare_value = current_price if value_kind == "price" else current_volume
        config = DEFAULT_CONFIGS[trigger_type]
        tracker = store.get_or_create(symbol, trigger_type, level.direction, config)
        event = classify_event(
            level.direction, level.level, tracker.last_price, compare_value,
            was_triggered=tracker.status in (BreakoutStatus.TRIGGERED, BreakoutStatus.CONFIRMED),
        )
        bar_ts = get_candle_boundary(now, config.confirmation_timeframe).isoformat()
        volume_ratio = (
            float(current_volume / level.level) if trigger_type is TriggerType.VOLUME_BREAKOUT and level.level else None
        )
        signal = tracker.evaluate(event, level.level, compare_value, now, bar_ts, volume_ratio, level.context)
        tracker.display_price = current_price
        if signal is not None:
            if value_kind == "volume":
                # A volume trigger compares volume, but persisted/alerted prices
                # must be real prices, not a traded-volume count.
                signal = replace(
                    signal,
                    trigger_price=current_price,
                    confirmation_price=current_price if signal.confirmation_price is not None else None,
                )
            signals.append(signal)

    # ---- zero-cross triggers (EMA9/EMA21, MACD/signal) ----
    for trigger_type, diff, reference in (
        (
            TriggerType.EMA_CROSS,
            _diff(ind_live.get("ema_9"), ind_live.get("ema_21")),
            ema_cross_reference(ind_live),
        ),
        (
            TriggerType.MACD_CROSS,
            _diff(ind_live.get("macd"), ind_live.get("macd_signal")),
            macd_cross_reference(ind_live),
        ),
    ):
        if diff is None or reference is None:
            continue
        direction = Direction.BULLISH  # tracked per-direction below via classify_event's own sign logic
        config = DEFAULT_CONFIGS[trigger_type]
        tracker = store.get_or_create(symbol, trigger_type, direction, config)
        event = classify_event(
            direction, safe_decimal(0), tracker.last_price, diff,
            was_triggered=tracker.status in (BreakoutStatus.TRIGGERED, BreakoutStatus.CONFIRMED),
        )
        bar_ts = get_candle_boundary(now, config.confirmation_timeframe).isoformat()
        signal = tracker.evaluate(event, reference, current_price, now, bar_ts, None, {})
        if signal is not None:
            signals.append(signal)

    # ---- Bollinger squeeze release ----
    bandwidth = bollinger_bandwidth(
        safe_decimal(ind_live.get("bollinger_upper")),
        safe_decimal(ind_live.get("bollinger_lower")),
        safe_decimal(ind_live.get("bollinger_mid")),
    )
    history = _bandwidth_history().setdefault(symbol, deque(maxlen=_BANDWIDTH_HISTORY_LEN))
    squeeze_active = is_bollinger_squeeze(list(history), bandwidth)
    if bandwidth is not None:
        history.append(bandwidth)
    if squeeze_active:
        upper = safe_decimal(ind_live.get("bollinger_upper"))
        lower = safe_decimal(ind_live.get("bollinger_lower"))
        config = DEFAULT_CONFIGS[TriggerType.BOLLINGER_SQUEEZE]
        for direction, level_value in ((Direction.BULLISH, upper), (Direction.BEARISH, lower)):
            if level_value is None:
                continue
            tracker = store.get_or_create(symbol, TriggerType.BOLLINGER_SQUEEZE, direction, config)
            event = classify_event(
                direction, level_value, tracker.last_price, current_price,
                was_triggered=tracker.status in (BreakoutStatus.TRIGGERED, BreakoutStatus.CONFIRMED),
            )
            bar_ts = get_candle_boundary(now, config.confirmation_timeframe).isoformat()
            signal = tracker.evaluate(event, level_value, current_price, now, bar_ts, None, {})
            if signal is not None:
                signals.append(signal)

    indicator_state = _indicator_states().get(symbol, SymbolIndicatorState())
    for signal in signals:
        await _handle_signal(signal, indicator_state)


def _diff(a: Any, b: Any) -> Any:
    a_dec, b_dec = safe_decimal(a), safe_decimal(b)
    if a_dec is None or b_dec is None:
        return None
    return a_dec - b_dec


async def _handle_signal(signal: BreakoutSignal, indicator_state: SymbolIndicatorState) -> None:
    if signal.status not in (BreakoutStatus.CONFIRMED, BreakoutStatus.FAILED):
        log.debug(
            "breakout_transition", symbol=signal.symbol, trigger_type=signal.trigger_type.value,
            status=signal.status.value,
        )
        return

    if signal.status is BreakoutStatus.CONFIRMED:
        dna = compute_dna_score(signal, indicator_state)
        signal = replace(signal, score=dna.overall)
    else:  # FAILED — a false breakout: confirmed, then reversed
        signal = replace(signal, extra={**signal.extra, "outcome": "failed_after_confirmation"})

    # One session/connection checkout for this signal's whole persistence
    # path (event + alert lookup + alert history), instead of 2-3 separate
    # ones — cuts real connection-pool pressure when several symbols signal
    # in the same cycle, without needing a bigger pool.
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        await record_breakout_event(signal, session=session)

        for alert in await _active_alerts_for_symbol(signal.symbol, session=session):
            if await should_notify(alert, signal, now_ist()):
                await publish_alert_trigger(alert.id, signal)
                await record_alert_history(alert.id, signal, session=session)


async def _active_alerts_for_symbol(symbol: str, session: Any | None = None) -> list[Any]:
    from sqlalchemy import select

    from app.db.models.alert import Alert

    async def _query(s: Any) -> list[Any]:
        rows = (
            await s.execute(select(Alert).where(Alert.symbol == symbol, Alert.is_active.is_(True)))
        ).scalars().all()
        return list(rows)

    if session is not None:
        return await _query(session)

    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        return await _query(session)


_last_scan_coverage: dict[str, int] = {"expected": 0, "processed": 0, "failed": 0}


def get_last_scan_coverage() -> dict[str, int]:
    """Snapshot of the most recently completed scan cycle's coverage —
    read by /health/data. A completed scan that silently examined fewer
    symbols than expected is not a successful full scan."""
    return dict(_last_scan_coverage)


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def breakout_engine_loop() -> None:
    """Forever loop — `main.py` wraps this in the same watchdog-with-backoff
    pattern already used for `nse_poller_loop` (`_poller_watchdog`).

    Processes the universe in small chunks with a short pause between them
    instead of scheduling all ~500 symbols in one `asyncio.gather` burst —
    that burst pattern was largely a startup-transient effect (many symbols'
    indicator state compared against thresholds in the same instant) but it
    produced real DB QueuePool timeouts under live testing. Chunking keeps
    the semaphore's concurrency cap meaningful instead of just queueing 500
    tasks that all wake at once the moment a slot frees up.
    """
    global _last_scan_coverage
    while True:
        try:
            symbols = await _get_universe_symbols()
            semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SYMBOL_SCANS)
            processed = 0
            failed = 0

            async def _bounded(sym: str) -> None:
                nonlocal processed, failed
                async with semaphore:
                    try:
                        await _scan_symbol(sym)
                        processed += 1
                    except Exception:
                        failed += 1
                        log.exception("breakout_scan_symbol_failed", symbol=sym)

            for chunk in _chunked(symbols, _SCAN_CHUNK_SIZE):
                await asyncio.gather(*(_bounded(s) for s in chunk))
                await asyncio.sleep(_SCAN_CHUNK_DELAY_SECONDS)

            _last_scan_coverage = {
                "expected": len(symbols), "processed": processed, "failed": failed,
            }
            get_breakout_state_store().purge_expired(now_ist())
        except Exception:
            log.exception("breakout_engine_cycle_failed")
        await asyncio.sleep(BREAKOUT_SCAN_INTERVAL)

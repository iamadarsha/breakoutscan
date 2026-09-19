"""`_scan_symbol()` end-to-end against `fake_redis` — reaching CONFIRMED
after the expected number of simulated scan cycles, and firing the
persistence/notification side effects on confirmation.

`now_ist` and `fetch_candle_history` are monkeypatched so the test controls
bar-boundary progression explicitly (real wall-clock time can't be relied
on to cross a 5-min boundary inside a fast unit test) and never touches a
real Postgres connection.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from app.breakouts import engine
from app.breakouts.types import BreakoutStatus, Direction, TriggerType
from app.services.redis_cache import get_redis, set_json
from app.utils.redis_keys import indicator_key
from app.utils.time import IST


@dataclass
class _FakeAlert:
    id: uuid.UUID
    frequency: str = "every_time"


@pytest.fixture(autouse=True)
def _clear_engine_caches():
    engine.get_breakout_state_store.cache_clear()
    engine._indicator_states.cache_clear()  # noqa: SLF001
    engine._last_indicator_snapshot.cache_clear()  # noqa: SLF001
    engine._last_seen_candle_ts.cache_clear()  # noqa: SLF001
    engine._bandwidth_history.cache_clear()  # noqa: SLF001
    yield
    engine.get_breakout_state_store.cache_clear()
    engine._indicator_states.cache_clear()  # noqa: SLF001
    engine._last_indicator_snapshot.cache_clear()  # noqa: SLF001
    engine._last_seen_candle_ts.cache_clear()  # noqa: SLF001
    engine._bandwidth_history.cache_clear()  # noqa: SLF001


@pytest.fixture(autouse=True)
def _no_postgres(monkeypatch):
    """Nothing in this test file should ever touch a real Postgres
    connection — MarketState is empty for an unseeded symbol, so
    `_candles_for` would otherwise fall through to `fetch_candle_history`."""

    async def _empty_history(symbol: str, timeframe: str):
        return []

    monkeypatch.setattr(engine, "fetch_candle_history", _empty_history)


@pytest.mark.usefixtures("fake_redis")
async def test_scan_symbol_confirms_pdh_breakout_after_second_cycle(monkeypatch):
    symbol = "RELIANCE"
    await set_json(f"price:{symbol}", {"ltp": 2510.0, "volume": 100000})

    from app.services.redis_cache import hset_dict

    await hset_dict(indicator_key(symbol, "1d"), {"prev_high": "2500.0", "prev_low": "2400.0"})

    recorded_events = []
    notified_alerts = []

    async def _fake_record_breakout_event(signal, **kwargs):
        recorded_events.append(signal)

    async def _fake_active_alerts(symbol_arg, **kwargs):
        return [_FakeAlert(id=uuid.uuid4())]

    async def _fake_publish_alert_trigger(alert_id, signal):
        notified_alerts.append((alert_id, signal))

    async def _fake_record_alert_history(alert_id, signal, **kwargs):
        pass

    monkeypatch.setattr(engine, "record_breakout_event", _fake_record_breakout_event)
    monkeypatch.setattr(engine, "_active_alerts_for_symbol", _fake_active_alerts)
    monkeypatch.setattr(engine, "publish_alert_trigger", _fake_publish_alert_trigger)
    monkeypatch.setattr(engine, "record_alert_history", _fake_record_alert_history)

    cycle1 = datetime(2026, 9, 15, 10, 0, tzinfo=IST)
    monkeypatch.setattr(engine, "now_ist", lambda: cycle1)

    await engine._scan_symbol(symbol)  # noqa: SLF001

    store = engine.get_breakout_state_store()
    bullish_tracker = store.get_or_create(
        symbol, TriggerType.PDH_PDL, Direction.BULLISH, engine.DEFAULT_CONFIGS[TriggerType.PDH_PDL],
    )
    assert bullish_tracker.status is BreakoutStatus.TRIGGERED
    assert recorded_events == []  # not confirmed yet — first cross only

    # Advance past a 5-min confirmation-timeframe boundary, price still holding above PDH.
    cycle2 = cycle1 + timedelta(minutes=5)
    monkeypatch.setattr(engine, "now_ist", lambda: cycle2)

    await engine._scan_symbol(symbol)  # noqa: SLF001

    assert bullish_tracker.status is BreakoutStatus.CONFIRMED
    assert len(recorded_events) == 1
    confirmed_signal = recorded_events[0]
    assert confirmed_signal.symbol == symbol
    assert confirmed_signal.trigger_type is TriggerType.PDH_PDL
    assert confirmed_signal.direction is Direction.BULLISH
    assert confirmed_signal.score is not None  # scoring applied before persistence
    assert len(notified_alerts) == 1


@pytest.mark.usefixtures("fake_redis")
async def test_scan_symbol_reverses_after_confirming_and_fires_failed_signal(monkeypatch):
    """A PDH breakout that confirms and then reverses back below the level
    must reach `_handle_signal` with `status=FAILED` and still fire the
    persistence/notification side effects, tagged with the false-breakout
    `extra["outcome"]` marker — the previously-missing 3.4a false-breakout
    guard path."""
    symbol = "RELIANCE"
    await set_json(f"price:{symbol}", {"ltp": 2510.0, "volume": 100000})

    from app.services.redis_cache import hset_dict

    await hset_dict(indicator_key(symbol, "1d"), {"prev_high": "2500.0", "prev_low": "2400.0"})

    recorded_events = []
    notified_alerts = []

    async def _fake_record_breakout_event(signal, **kwargs):
        recorded_events.append(signal)

    async def _fake_active_alerts(symbol_arg, **kwargs):
        return [_FakeAlert(id=uuid.uuid4())]

    async def _fake_publish_alert_trigger(alert_id, signal):
        notified_alerts.append((alert_id, signal))

    async def _fake_record_alert_history(alert_id, signal, **kwargs):
        pass

    monkeypatch.setattr(engine, "record_breakout_event", _fake_record_breakout_event)
    monkeypatch.setattr(engine, "_active_alerts_for_symbol", _fake_active_alerts)
    monkeypatch.setattr(engine, "publish_alert_trigger", _fake_publish_alert_trigger)
    monkeypatch.setattr(engine, "record_alert_history", _fake_record_alert_history)

    cycle1 = datetime(2026, 9, 15, 10, 0, tzinfo=IST)
    monkeypatch.setattr(engine, "now_ist", lambda: cycle1)
    await engine._scan_symbol(symbol)  # noqa: SLF001 — CROSS_UP, TRIGGERED

    cycle2 = cycle1 + timedelta(minutes=5)
    monkeypatch.setattr(engine, "now_ist", lambda: cycle2)
    await engine._scan_symbol(symbol)  # noqa: SLF001 — HOLD on a new bar, CONFIRMED

    store = engine.get_breakout_state_store()
    bullish_tracker = store.get_or_create(
        symbol, TriggerType.PDH_PDL, Direction.BULLISH, engine.DEFAULT_CONFIGS[TriggerType.PDH_PDL],
    )
    assert bullish_tracker.status is BreakoutStatus.CONFIRMED
    assert len(recorded_events) == 1  # the CONFIRMED signal only so far

    # Price falls back below the PDH level — reverses the CONFIRMED breakout.
    await set_json(f"price:{symbol}", {"ltp": 2495.0, "volume": 100000})
    cycle3 = cycle2 + timedelta(minutes=5)
    monkeypatch.setattr(engine, "now_ist", lambda: cycle3)
    await engine._scan_symbol(symbol)  # noqa: SLF001 — REVERSE, FAILED

    assert bullish_tracker.status is BreakoutStatus.ARMED  # re-armed exactly as before
    assert len(recorded_events) == 2
    failed_signal = recorded_events[-1]
    assert failed_signal.status is BreakoutStatus.FAILED
    assert failed_signal.symbol == symbol
    assert failed_signal.trigger_type is TriggerType.PDH_PDL
    assert failed_signal.direction is Direction.BULLISH
    assert failed_signal.extra.get("outcome") == "failed_after_confirmation"

    assert len(notified_alerts) == 2  # one for CONFIRMED, one for FAILED
    assert notified_alerts[-1][1] is failed_signal


@pytest.mark.usefixtures("fake_redis")
async def test_scan_symbol_no_op_when_no_price_data():
    # No price:{symbol} key seeded at all — must return cleanly, no crash.
    await engine._scan_symbol("NONEXISTENT")  # noqa: SLF001
    assert engine.get_breakout_state_store().all_active() == []


@pytest.mark.usefixtures("fake_redis")
async def test_scan_symbol_ignores_price_data_with_unparseable_ltp():
    await set_json("price:BADDATA", {"ltp": "not-a-number", "volume": 100})
    await engine._scan_symbol("BADDATA")  # noqa: SLF001
    assert engine.get_breakout_state_store().all_active() == []


def test_chunked_splits_into_expected_group_sizes():
    items = [str(i) for i in range(125)]
    chunks = engine._chunked(items, 50)  # noqa: SLF001
    assert [len(c) for c in chunks] == [50, 50, 25]
    assert [s for chunk in chunks for s in chunk] == items


def test_chunked_handles_empty_and_smaller_than_chunk_size():
    assert engine._chunked([], 50) == []  # noqa: SLF001
    assert engine._chunked(["A", "B"], 50) == [["A", "B"]]  # noqa: SLF001


@pytest.mark.usefixtures("fake_redis")
async def test_breakout_engine_loop_processes_in_chunks_and_records_coverage(monkeypatch):
    """The 500-symbol universe must not be scheduled as one instantaneous
    burst — caught live (2026-09-15): that pattern produced real DB
    QueuePool timeouts. This verifies symbols are processed in bounded
    chunks (not all at once) and that a completed cycle's coverage is
    recorded for /health/data, including a failed symbol."""
    redis = await get_redis()
    symbols = [f"SYM{i}" for i in range(7)]
    await redis.sadd("universe:nifty500", *symbols)

    monkeypatch.setattr(engine, "_SCAN_CHUNK_SIZE", 3)
    monkeypatch.setattr(engine, "_SCAN_CHUNK_DELAY_SECONDS", 0.0)

    seen: list[str] = []
    max_concurrent = 0
    current = 0

    async def _fake_scan_symbol(sym: str) -> None:
        nonlocal max_concurrent, current
        current += 1
        max_concurrent = max(max_concurrent, current)
        seen.append(sym)
        try:
            await asyncio.sleep(0)
            if sym == "SYM3":
                raise RuntimeError("simulated scan failure")
        finally:
            current -= 1

    monkeypatch.setattr(engine, "_scan_symbol", _fake_scan_symbol)

    task = asyncio.create_task(engine.breakout_engine_loop())
    try:
        await asyncio.sleep(0.2)  # let one full cycle (all chunks) complete
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert sorted(seen) == sorted(symbols)
    assert max_concurrent <= 3  # never exceeded one chunk's worth at a time

    coverage = engine.get_last_scan_coverage()
    assert coverage["expected"] == 7
    assert coverage["processed"] == 6  # all but the one that raised
    assert coverage["failed"] == 1


@pytest.mark.usefixtures("fake_redis")
async def test_volume_breakout_reports_real_price_not_traded_volume(monkeypatch):
    """Regression: a volume trigger compares volume against a volume level, but
    the price shown to users and stored/alerted with the signal must be the
    real traded price (the dashboard once showed a 'price' of 1,698,993)."""
    from app.api.routes.breakouts import _to_active_out
    from app.services.redis_cache import hset_dict

    symbol = "WELCORP"
    await hset_dict(indicator_key(symbol, "1d"), {"sma_20_volume": "100000"})

    recorded = []

    async def _record(signal, **kwargs):
        recorded.append(signal)

    async def _no_alerts(symbol_arg, **kwargs):
        return []

    monkeypatch.setattr(engine, "record_breakout_event", _record)
    monkeypatch.setattr(engine, "_active_alerts_for_symbol", _no_alerts)

    cycle = datetime(2026, 9, 15, 10, 0, tzinfo=IST)
    for step, volume in enumerate([50_000, 1_700_000, 1_800_000]):  # below, spike, still above
        await set_json(f"price:{symbol}", {"ltp": 2463.0, "volume": volume})
        monkeypatch.setattr(engine, "now_ist", lambda c=cycle + timedelta(minutes=5 * step): c)
        await engine._scan_symbol(symbol)  # noqa: SLF001

    tracker = engine.get_breakout_state_store().get_or_create(
        symbol, TriggerType.VOLUME_BREAKOUT, Direction.BULLISH,
        engine.DEFAULT_CONFIGS[TriggerType.VOLUME_BREAKOUT],
    )
    assert tracker.status in (BreakoutStatus.TRIGGERED, BreakoutStatus.CONFIRMED)
    assert _to_active_out(tracker).last_price == 2463.0

    volume_signals = [s for s in recorded if s.trigger_type is TriggerType.VOLUME_BREAKOUT]
    for signal in volume_signals:
        assert float(signal.trigger_price) == 2463.0
        if signal.confirmation_price is not None:
            assert float(signal.confirmation_price) == 2463.0


@pytest.mark.usefixtures("fake_redis")
async def test_engine_scans_once_then_idles_while_market_is_closed(monkeypatch):
    """A closed market cannot change, so after one final pass the loop must
    stop re-reading history for the whole universe (that loop drove Supabase
    egress to 247% of its free quota)."""
    redis = await get_redis()
    await redis.sadd("universe:nifty500", "AAA", "BBB", "CCC")
    monkeypatch.setattr(engine, "_SCAN_CHUNK_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(engine, "BREAKOUT_SCAN_INTERVAL", 0.01)
    monkeypatch.setattr(engine, "_CLOSED_POLL_SECONDS", 0.01)

    async def _closed() -> bool:
        return False

    scans: list[str] = []

    async def _fake_scan(sym: str) -> None:
        scans.append(sym)

    monkeypatch.setattr(engine, "_market_open_now", _closed)
    monkeypatch.setattr(engine, "_scan_symbol", _fake_scan)

    task = asyncio.create_task(engine.breakout_engine_loop())
    try:
        await asyncio.sleep(0.4)  # many idle polls would have elapsed
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert sorted(scans) == ["AAA", "BBB", "CCC"]  # exactly one pass


@pytest.mark.usefixtures("fake_redis")
async def test_engine_keeps_scanning_every_cycle_while_market_is_open(monkeypatch):
    redis = await get_redis()
    await redis.sadd("universe:nifty500", "AAA")
    monkeypatch.setattr(engine, "_SCAN_CHUNK_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(engine, "BREAKOUT_SCAN_INTERVAL", 0.01)

    async def _open() -> bool:
        return True

    scans: list[str] = []

    async def _fake_scan(sym: str) -> None:
        scans.append(sym)

    monkeypatch.setattr(engine, "_market_open_now", _open)
    monkeypatch.setattr(engine, "_scan_symbol", _fake_scan)

    task = asyncio.create_task(engine.breakout_engine_loop())
    try:
        await asyncio.sleep(0.3)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert len(scans) >= 3


@pytest.mark.usefixtures("fake_redis")
async def test_repeat_confirmations_are_suppressed_inside_the_cooldown():
    from app.breakouts.types import BreakoutSignal

    def _signal(trigger=TriggerType.PDH_PDL, direction=Direction.BULLISH, status=BreakoutStatus.CONFIRMED):
        from decimal import Decimal

        now = datetime(2026, 9, 15, 10, 0, tzinfo=IST)
        return BreakoutSignal(
            symbol="IGL", trigger_type=trigger, direction=direction, status=status,
            reference_level=Decimal("1"), trigger_price=Decimal("1"), confirmation_price=Decimal("1"),
            triggered_at=now, confirmed_at=now, bars_confirmed=1, score=None, volume_ratio=None, extra={},
        )

    assert await engine._should_persist(_signal()) is True
    assert await engine._should_persist(_signal()) is False  # same breakout oscillating
    assert await engine._should_persist(_signal(trigger=TriggerType.VWAP)) is True  # different trigger
    assert await engine._should_persist(_signal(direction=Direction.BEARISH)) is True
    assert await engine._should_persist(_signal(status=BreakoutStatus.FAILED)) is True  # a real failure

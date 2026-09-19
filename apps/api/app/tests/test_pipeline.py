"""Milestone 2.2 glue: app.market.pipeline.

Covers the wiring this round added — instrument-key derivation, the
failover-gate delegation nse_poller.py now calls into, and tick handling —
without needing a live Upstox connection (see test_provider.py for the
already-covered connection-layer logic).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.market import feed_metrics, pipeline
from app.market.normalize import DecodedMessage, MessageType, Tick


@pytest.fixture(autouse=True)
def _clear_pipeline_caches():
    """Every `@lru_cache` singleton in pipeline.py must reset between tests —
    otherwise state (subscriptions, failover status, candle buffers) leaks
    across unrelated test cases."""
    pipeline.get_failover_controller.cache_clear()
    pipeline.get_market_state.cache_clear()
    pipeline.get_candle_engine.cache_clear()
    pipeline._instrument_key_maps.cache_clear()  # noqa: SLF001
    feed_metrics.get_feed_metrics.cache_clear()
    yield
    pipeline.get_failover_controller.cache_clear()
    pipeline.get_market_state.cache_clear()
    pipeline.get_candle_engine.cache_clear()
    pipeline._instrument_key_maps.cache_clear()  # noqa: SLF001
    feed_metrics.get_feed_metrics.cache_clear()


def test_instrument_keys_use_nse_eq_isin_convention():
    symbol_to_key, key_to_symbol = pipeline._instrument_key_maps()  # noqa: SLF001

    assert symbol_to_key  # the real seed file has 500 entries
    reliance_key = symbol_to_key.get("RELIANCE")
    assert reliance_key is not None
    assert reliance_key.startswith("NSE_EQ|")
    assert key_to_symbol[reliance_key] == "RELIANCE"


def test_get_subscription_instrument_keys_matches_universe_size():
    keys = pipeline.get_subscription_instrument_keys()
    symbol_to_key, _ = pipeline._instrument_key_maps()  # noqa: SLF001
    assert len(keys) == len(symbol_to_key)


def test_should_use_fallback_prices_true_when_upstox_not_configured(monkeypatch):
    class _FakeSettings:
        upstox_analytics_token = ""

    monkeypatch.setattr(pipeline, "get_settings", lambda: _FakeSettings())

    assert pipeline.is_upstox_configured() is False
    assert pipeline.should_use_fallback_prices() is True


def test_should_use_fallback_prices_delegates_to_failover_controller(monkeypatch):
    class _FakeSettings:
        upstox_analytics_token = "some-token"

    monkeypatch.setattr(pipeline, "get_settings", lambda: _FakeSettings())
    assert pipeline.is_upstox_configured() is True

    # Fresh controller: no primary tick has EVER arrived. The controller's
    # own status stays PRIMARY_LIVE (see FailoverController.evaluate's
    # documented "fresh start, not stale" behaviour) — but the fallback
    # poller must still run here, since Upstox hasn't proven itself live
    # even once (e.g. still connecting, or markets closed for the day).
    assert pipeline.should_use_fallback_prices() is True

    # Once Upstox has ticked at least once and the controller reports
    # healthy, should_use_fallback_prices() must defer to it and stop.
    controller = pipeline.get_failover_controller()
    # has_ever_ticked is a read-only property — patch it on the class, not
    # the instance (setattr on the instance would hit the property's
    # descriptor and raise, since it has no setter).
    monkeypatch.setattr(type(controller), "has_ever_ticked", True)
    monkeypatch.setattr(controller, "should_run_fallback_poller", lambda: False)
    assert pipeline.should_use_fallback_prices() is False

    # And once the controller decides the primary has gone stale, the
    # fallback poller must run again.
    monkeypatch.setattr(controller, "should_run_fallback_poller", lambda: True)
    assert pipeline.should_use_fallback_prices() is True


@pytest.mark.usefixtures("fake_redis")
async def test_handle_decoded_message_writes_price_and_ignores_unknown_instrument(fake_redis):
    symbol_to_key, _ = pipeline._instrument_key_maps()  # noqa: SLF001
    reliance_key = symbol_to_key["RELIANCE"]

    known_tick = Tick(
        instrument_key=reliance_key,
        ltp=2500.5,
        ltt=1_700_000_000_000,
        ltq=10,
        close_price=2480.0,
        vtt=123456,
        received_at=datetime.now(timezone.utc),
    )
    unknown_tick = Tick(
        instrument_key="NSE_EQ|NOT_IN_UNIVERSE",
        ltp=1.0,
        ltt=1_700_000_000_000,
        ltq=1,
        close_price=1.0,
        vtt=1,
        received_at=datetime.now(timezone.utc),
    )
    decoded = DecodedMessage(
        type=MessageType.LIVE_FEED,
        current_ts=1_700_000_000_000,
        ticks=[known_tick, unknown_tick],
        market_info=None,
    )

    await pipeline._handle_decoded_message(decoded)  # noqa: SLF001

    stored = await fake_redis.get("price:RELIANCE")
    assert stored is not None
    assert "2500.5" in stored

    # Unknown instrument key must never produce a price:{symbol} write —
    # there's no symbol to key it under.
    assert await fake_redis.get("price:NOT_IN_UNIVERSE") is None

    market_state = pipeline.get_market_state()
    assert market_state.get("RELIANCE") is not None
    assert market_state.get("RELIANCE").latest_tick.ltp == 2500.5

    # Both known and unknown-instrument ticks must feed freshness tracking —
    # feed liveness is about whether *any* message arrived, not just ones
    # for symbols in our universe.
    snapshot = feed_metrics.get_feed_metrics().snapshot()
    assert snapshot["last_exchange_tick_age_ms"] is not None
    assert snapshot["last_received_age_ms"] is not None


@pytest.mark.usefixtures("fake_redis")
async def test_handle_decoded_message_uses_real_day_ohlc_when_available(fake_redis):
    """Regression test for the bug caught by comparing live prices against
    Google Finance: open/high/low were being fabricated as == ltp on every
    tick, discarding the feed's real day-range data entirely — useless for
    a breakout scanner (opening gap, % off high, range-based signals all
    silently broken)."""
    import json

    symbol_to_key, _ = pipeline._instrument_key_maps()  # noqa: SLF001
    reliance_key = symbol_to_key["RELIANCE"]

    tick = Tick(
        instrument_key=reliance_key,
        ltp=2500.5,
        ltt=1_700_000_000_000,
        ltq=10,
        close_price=2480.0,
        vtt=123456,
        received_at=datetime.now(timezone.utc),
        day_open=2470.0,
        day_high=2495.0,  # feed's high hasn't caught up to this tick yet
        day_low=2465.0,
    )
    decoded = DecodedMessage(
        type=MessageType.LIVE_FEED,
        current_ts=1_700_000_000_000,
        ticks=[tick],
        market_info=None,
    )

    await pipeline._handle_decoded_message(decoded)  # noqa: SLF001

    stored = json.loads(await fake_redis.get("price:RELIANCE"))
    assert stored["open"] == 2470.0
    # High must reflect this tick even though the feed's own "high" field
    # (2495.0) is stale relative to the current ltp (2500.5) — the max()
    # safety net in pipeline.py exists exactly for this lag.
    assert stored["high"] == 2500.5
    assert stored["low"] == 2465.0


@pytest.mark.usefixtures("fake_redis")
async def test_handle_decoded_message_falls_back_to_ltp_without_day_ohlc(fake_redis):
    """When the feed genuinely has no day OHLC (e.g. bare ltpc mode), the
    old ltp-for-everything behaviour is still the correct fallback — this
    must not regress into crashing or writing None."""
    import json

    symbol_to_key, _ = pipeline._instrument_key_maps()  # noqa: SLF001
    reliance_key = symbol_to_key["RELIANCE"]

    tick = Tick(
        instrument_key=reliance_key,
        ltp=2500.5,
        ltt=1_700_000_000_000,
        ltq=10,
        close_price=2480.0,
        vtt=123456,
        received_at=datetime.now(timezone.utc),
        # day_open/high/low default to None
    )
    decoded = DecodedMessage(
        type=MessageType.LIVE_FEED,
        current_ts=1_700_000_000_000,
        ticks=[tick],
        market_info=None,
    )

    await pipeline._handle_decoded_message(decoded)  # noqa: SLF001

    stored = json.loads(await fake_redis.get("price:RELIANCE"))
    assert stored["open"] == 2500.5
    assert stored["high"] == 2500.5
    assert stored["low"] == 2500.5

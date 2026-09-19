"""Protobuf decode correctness + ltq/vtt separation (Phase 2.1 acceptance gates)."""

from __future__ import annotations

from app.market.normalize import MessageType, decode_feed_response
from app.tests.fixtures.upstox_v3 import (
    build_full_feed_message,
    build_ltpc_only_message,
    build_market_info_message,
    build_multi_symbol_full_feed_message,
)


def test_market_info_decodes_segment_status():
    raw = build_market_info_message()
    decoded = decode_feed_response(raw)

    assert decoded.type == MessageType.MARKET_INFO
    assert decoded.market_info is not None
    assert decoded.market_info.segment_status["NSE_EQ"] == "NORMAL_OPEN"
    assert decoded.market_info.segment_status["NSE_FO"] == "PRE_OPEN_START"
    assert decoded.ticks == []


def test_ltpc_only_tick_has_no_cumulative_volume():
    raw = build_ltpc_only_message("NSE_EQ|INE002A01018", ltp=2500.5, ltq=10)
    decoded = decode_feed_response(raw)

    assert decoded.type == MessageType.LIVE_FEED
    assert len(decoded.ticks) == 1
    tick = decoded.ticks[0]
    assert tick.instrument_key == "NSE_EQ|INE002A01018"
    assert tick.ltp == 2500.5
    assert tick.ltq == 10
    # This is the exact distinction the Phase 1 audit flagged as a bug in
    # the old streamer: bare ltpc mode has no cumulative day volume at all.
    assert tick.vtt is None


def test_full_feed_tick_separates_ltq_from_vtt():
    raw = build_full_feed_message("NSE_EQ|INE002A01018", ltp=2500.5, ltq=10, vtt=125_000)
    decoded = decode_feed_response(raw)

    tick = decoded.ticks[0]
    # ltq: the per-trade delta quantity — safe to sum into candle volume.
    assert tick.ltq == 10
    # vtt: cumulative day volume — must NEVER be summed as a delta (this was
    # the old upstox_streamer.py's bug: it summed a cumulative field).
    assert tick.vtt == 125_000
    assert tick.ltq != tick.vtt


def test_multi_symbol_message_decodes_all_ticks():
    raw = build_multi_symbol_full_feed_message(
        {
            "NSE_EQ|A": (100.0, 5, 10_000),
            "NSE_EQ|B": (200.0, 8, 20_000),
        }
    )
    decoded = decode_feed_response(raw)

    assert len(decoded.ticks) == 2
    by_key = {t.instrument_key: t for t in decoded.ticks}
    assert by_key["NSE_EQ|A"].ltp == 100.0
    assert by_key["NSE_EQ|B"].vtt == 20_000


def test_full_feed_tick_extracts_real_day_ohlc():
    """The feed's own "1d" OHLC entry must be surfaced on the Tick — this
    is real open/running-high/running-low data, not something the caller
    should ever need to fabricate from the current ltp."""
    raw = build_full_feed_message(
        "NSE_EQ|INE002A01018",
        ltp=2500.5,
        ltq=10,
        vtt=125_000,
        day_ohlc=(2480.0, 2510.0, 2470.0, 2500.5),
    )
    decoded = decode_feed_response(raw)

    tick = decoded.ticks[0]
    assert tick.day_open == 2480.0
    assert tick.day_high == 2510.0
    assert tick.day_low == 2470.0


def test_full_feed_tick_picks_1d_interval_not_first_entry():
    """marketOHLC can carry multiple intervals (e.g. "I1" alongside "1d") —
    the normalizer must pick out "1d" specifically, not just the first
    entry in the repeated field."""
    raw = build_full_feed_message(
        "NSE_EQ|INE002A01018",
        ltp=2500.5,
        ltq=10,
        vtt=125_000,
        extra_ohlc_intervals=[("I1", 2499.0, 2501.0, 2498.0, 2500.5)],
        day_ohlc=(2480.0, 2510.0, 2470.0, 2500.5),
    )
    decoded = decode_feed_response(raw)

    tick = decoded.ticks[0]
    assert tick.day_open == 2480.0
    assert tick.day_high == 2510.0
    assert tick.day_low == 2470.0


def test_full_feed_tick_without_ohlc_leaves_day_fields_none():
    """No "1d" entry in the feed (e.g. an older payload shape) must leave
    day_open/high/low as None, never a fabricated value — the caller is
    responsible for falling back explicitly, not the normalizer silently
    inventing data."""
    raw = build_full_feed_message("NSE_EQ|INE002A01018", ltp=2500.5, ltq=10, vtt=125_000)
    decoded = decode_feed_response(raw)

    tick = decoded.ticks[0]
    assert tick.day_open is None
    assert tick.day_high is None
    assert tick.day_low is None


def test_ltpc_only_tick_has_no_day_ohlc():
    """Bare ltpc mode never carries OHLC at all — day fields must be None,
    not silently default to ltp."""
    raw = build_ltpc_only_message("NSE_EQ|INE002A01018", ltp=2500.5, ltq=10)
    decoded = decode_feed_response(raw)

    tick = decoded.ticks[0]
    assert tick.day_open is None
    assert tick.day_high is None
    assert tick.day_low is None

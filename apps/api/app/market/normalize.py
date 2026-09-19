"""Normalize decoded Upstox V3 protobuf messages into typed ticks.

Schema source: apps/api/app/market/proto/MarketDataFeed.proto (downloaded
verbatim from https://assets.upstox.com/feed/market-data-feed/v3/MarketDataFeed.proto,
2026-09-13 — re-run scripts/compile_proto.sh if Upstox revises it).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.market import MarketDataFeed_pb2 as pb


class MessageType(str, Enum):
    INITIAL_FEED = "initial_feed"
    LIVE_FEED = "live_feed"
    MARKET_INFO = "market_info"


_TYPE_MAP = {
    pb.initial_feed: MessageType.INITIAL_FEED,
    pb.live_feed: MessageType.LIVE_FEED,
    pb.market_info: MessageType.MARKET_INFO,
}

_MARKET_STATUS_NAMES = {
    pb.PRE_OPEN_START: "PRE_OPEN_START",
    pb.PRE_OPEN_END: "PRE_OPEN_END",
    pb.NORMAL_OPEN: "NORMAL_OPEN",
    pb.NORMAL_CLOSE: "NORMAL_CLOSE",
    pb.CLOSING_START: "CLOSING_START",
    pb.CLOSING_END: "CLOSING_END",
}


@dataclass(frozen=True, slots=True)
class Tick:
    """A single normalized market update for one instrument.

    ``ltq`` is the last-traded (per-trade) quantity — a real per-tick
    delta, safe to sum into candle volume. ``vtt`` is cumulative day
    volume (only present in ``full_d5``/``option_greeks`` payloads, not
    bare ``ltpc`` mode) — use this for RVOL/breadth baselines, never sum
    it as if it were a delta. This distinction is the fix for the
    volume-double-counting bug found in the Phase 1 audit of the old
    (unused) upstox_streamer.py, which summed a cumulative field as a delta.

    ``day_open``/``day_high``/``day_low`` come from the feed's own
    ``marketOHLC`` (the "1d" interval entry) — only present on
    ``marketFF``/``indexFF`` (full-feed) payloads, never on bare ``ltpc``
    or ``firstLevelWithGreeks`` modes. None when unavailable; callers must
    not assume these are always populated.
    """

    instrument_key: str
    ltp: float
    ltt: int  # last trade time, epoch millis
    ltq: int
    close_price: float  # previous day's close ("cp" in the proto)
    vtt: int | None
    received_at: datetime
    day_open: float | None = None
    day_high: float | None = None
    day_low: float | None = None


@dataclass(frozen=True, slots=True)
class MarketInfoUpdate:
    segment_status: dict[str, str]
    current_ts: int


@dataclass(frozen=True, slots=True)
class DecodedMessage:
    type: MessageType
    current_ts: int
    ticks: list[Tick]
    market_info: MarketInfoUpdate | None


def decode_feed_response(raw: bytes) -> DecodedMessage:
    """Parse a raw V3 WebSocket binary frame into a :class:`DecodedMessage`."""
    fr = pb.FeedResponse()
    fr.ParseFromString(raw)

    msg_type = _TYPE_MAP.get(fr.type, MessageType.LIVE_FEED)
    received_at = datetime.now(timezone.utc)

    ticks: list[Tick] = []
    for instrument_key, feed in fr.feeds.items():
        tick = _extract_tick(instrument_key, feed, received_at)
        if tick is not None:
            ticks.append(tick)

    market_info = None
    if fr.HasField("marketInfo"):
        market_info = MarketInfoUpdate(
            segment_status={
                segment: _MARKET_STATUS_NAMES.get(status, "UNKNOWN")
                for segment, status in fr.marketInfo.segmentStatus.items()
            },
            current_ts=fr.currentTs,
        )

    return DecodedMessage(
        type=msg_type,
        current_ts=fr.currentTs,
        ticks=ticks,
        market_info=market_info,
    )


def _extract_day_ohlc(market_ohlc: "pb.MarketOHLC") -> tuple[float, float, float] | None:
    """Pull the day-level (interval "1d") open/high/low out of a feed's
    ``marketOHLC`` list. Returns None if the feed didn't include one —
    callers must fall back gracefully, never fabricate a value."""
    for entry in market_ohlc.ohlc:
        if entry.interval == "1d":
            return entry.open, entry.high, entry.low
    return None


def _extract_tick(instrument_key: str, feed: "pb.Feed", received_at: datetime) -> Tick | None:
    which = feed.WhichOneof("FeedUnion")
    day_ohlc: tuple[float, float, float] | None = None

    if which == "ltpc":
        ltpc = feed.ltpc
        vtt = None
    elif which == "fullFeed":
        full = feed.fullFeed
        which_full = full.WhichOneof("FullFeedUnion")
        if which_full == "marketFF":
            ltpc = full.marketFF.ltpc
            vtt = full.marketFF.vtt
            day_ohlc = _extract_day_ohlc(full.marketFF.marketOHLC)
        elif which_full == "indexFF":
            ltpc = full.indexFF.ltpc
            vtt = None
            day_ohlc = _extract_day_ohlc(full.indexFF.marketOHLC)
        else:
            return None
    elif which == "firstLevelWithGreeks":
        flw = feed.firstLevelWithGreeks
        ltpc = flw.ltpc
        vtt = flw.vtt
    else:
        return None

    day_open, day_high, day_low = day_ohlc if day_ohlc else (None, None, None)

    return Tick(
        instrument_key=instrument_key,
        ltp=ltpc.ltp,
        ltt=ltpc.ltt,
        ltq=ltpc.ltq,
        close_price=ltpc.cp,
        vtt=vtt,
        received_at=received_at,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
    )

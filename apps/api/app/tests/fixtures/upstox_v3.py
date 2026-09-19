"""Synthetic Upstox V3 protobuf message builders for tests.

There is no live Upstox connection to record real traffic from yet (see
docs/DATA_PROVIDER_MATRIX.md), so these builders construct messages
directly from the compiled schema (app.market.MarketDataFeed_pb2),
matching the shapes documented at
https://upstox.com/developer/api-documentation/v3/get-market-data-feed/.
"""

from __future__ import annotations

from app.market import MarketDataFeed_pb2 as pb


def build_market_info_message(current_ts: int = 1_700_000_000_000) -> bytes:
    fr = pb.FeedResponse()
    fr.type = pb.market_info
    fr.currentTs = current_ts
    fr.marketInfo.segmentStatus["NSE_EQ"] = pb.NORMAL_OPEN
    fr.marketInfo.segmentStatus["NSE_FO"] = pb.PRE_OPEN_START
    return fr.SerializeToString()


def build_ltpc_only_message(
    instrument_key: str,
    ltp: float,
    ltq: int,
    ltt: int = 1_700_000_000_000,
    cp: float = 0.0,
    current_ts: int = 1_700_000_000_500,
) -> bytes:
    """A bare `ltpc` mode tick — no cumulative day volume (`vtt`)."""
    fr = pb.FeedResponse()
    fr.type = pb.live_feed
    fr.currentTs = current_ts

    feed = pb.Feed()
    feed.ltpc.ltp = ltp
    feed.ltpc.ltt = ltt
    feed.ltpc.ltq = ltq
    feed.ltpc.cp = cp
    feed.requestMode = pb.ltpc

    fr.feeds[instrument_key].CopyFrom(feed)
    return fr.SerializeToString()


def build_full_feed_message(
    instrument_key: str,
    ltp: float,
    ltq: int,
    vtt: int,
    ltt: int = 1_700_000_000_000,
    cp: float = 0.0,
    current_ts: int = 1_700_000_000_500,
    day_ohlc: tuple[float, float, float, float] | None = None,
    extra_ohlc_intervals: list[tuple[str, float, float, float, float]] | None = None,
) -> bytes:
    """A `full_d5` mode tick — includes `vtt` (cumulative day volume).

    ``day_ohlc``, if given, is ``(open, high, low, close)`` added as the
    "1d" interval entry in ``marketOHLC`` — the real day-range data the
    feed provides that the normalizer must not discard.
    ``extra_ohlc_intervals`` lets a test add other-interval entries (e.g.
    "I1") to confirm the normalizer picks out "1d" specifically rather
    than just taking the first entry in the list.
    """
    fr = pb.FeedResponse()
    fr.type = pb.live_feed
    fr.currentTs = current_ts

    feed = pb.Feed()
    feed.fullFeed.marketFF.ltpc.ltp = ltp
    feed.fullFeed.marketFF.ltpc.ltt = ltt
    feed.fullFeed.marketFF.ltpc.ltq = ltq
    feed.fullFeed.marketFF.ltpc.cp = cp
    feed.fullFeed.marketFF.vtt = vtt
    feed.requestMode = pb.full_d5

    for interval, o, h, l, c in extra_ohlc_intervals or []:
        entry = feed.fullFeed.marketFF.marketOHLC.ohlc.add()
        entry.interval = interval
        entry.open = o
        entry.high = h
        entry.low = l
        entry.close = c

    if day_ohlc is not None:
        o, h, l, c = day_ohlc
        entry = feed.fullFeed.marketFF.marketOHLC.ohlc.add()
        entry.interval = "1d"
        entry.open = o
        entry.high = h
        entry.low = l
        entry.close = c

    fr.feeds[instrument_key].CopyFrom(feed)
    return fr.SerializeToString()


def build_multi_symbol_full_feed_message(
    ticks: dict[str, tuple[float, int, int]],
    current_ts: int = 1_700_000_000_500,
) -> bytes:
    """`ticks` maps instrument_key -> (ltp, ltq, vtt)."""
    fr = pb.FeedResponse()
    fr.type = pb.live_feed
    fr.currentTs = current_ts

    for instrument_key, (ltp, ltq, vtt) in ticks.items():
        feed = pb.Feed()
        feed.fullFeed.marketFF.ltpc.ltp = ltp
        feed.fullFeed.marketFF.ltpc.ltt = current_ts
        feed.fullFeed.marketFF.ltpc.ltq = ltq
        feed.fullFeed.marketFF.vtt = vtt
        feed.requestMode = pb.full_d5
        fr.feeds[instrument_key].CopyFrom(feed)

    return fr.SerializeToString()

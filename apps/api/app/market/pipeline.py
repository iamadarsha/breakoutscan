"""Wires UpstoxV3Provider into the app: ticks -> Redis prices -> candles.

This is Milestone 2.2's live-feed glue. It intentionally does **not** touch
the `ind:{symbol}:1d` indicator hashes — those are computed from daily
OHLCV via `YFinanceProvider.bulk_compute` (still triggered from
`nse_poller.py`, unrelated to realtime ticks) and reseeding them from a
few in-memory intraday bars would produce wrong SMA-200/etc. values.
Feeding live ticks into multi-timeframe indicators belongs to Phase 3.2
(breakout engine), once proper historical candle seeding exists.

`nse_poller.py`'s NSE-scrape price polling (section 2 of its loop) is
gated behind `should_use_fallback_prices()` so it only runs when Upstox's
`FailoverController` has moved off `PRIMARY_LIVE`; the poller's unrelated
concerns (indices/breadth, trending, daily bulk-compute) are untouched and
keep running every cycle regardless of feed status.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from functools import lru_cache

import structlog

from app.core.config import get_settings
from app.market.candles import CandleEngine
from app.market.event_bus import (
    CandleUpdateEvent,
    MarketStatusEvent,
    publish_candle_update,
    publish_market_status,
)
from app.market.failover import FailoverController
from app.market.feed_metrics import get_feed_metrics
from app.market.normalize import DecodedMessage
from app.market.provider import UpstoxV3Provider
from app.market.state import MarketState
from app.services.redis_cache import publish, set_json

log = structlog.get_logger(__name__)

PRICE_TTL = 300  # matches nse_poller.PRICE_TTL — same key, same freshness contract


@lru_cache(maxsize=1)
def get_failover_controller() -> FailoverController:
    """Process-wide singleton shared between the Upstox provider and nse_poller."""
    return FailoverController()


@lru_cache(maxsize=1)
def get_market_state() -> MarketState:
    return MarketState()


@lru_cache(maxsize=1)
def get_candle_engine() -> CandleEngine:
    return CandleEngine()


def is_upstox_configured() -> bool:
    return bool(get_settings().upstox_analytics_token)


def should_use_fallback_prices() -> bool:
    """True when nse_poller's NSE-scrape price fetch should run this cycle.

    Calling `evaluate()` here (rather than just reading `.status`) means
    nse_poller's existing 30s cycle doubles as the failover heartbeat —
    no separate timer needed.

    `FailoverController` starts optimistically at `PRIMARY_LIVE` and only
    moves to `DEGRADED`/`FALLBACK` once a primary tick has arrived and then
    gone stale (see `evaluate()`) — it never treats "no primary tick has
    *ever* arrived" as stale (deliberately — see
    `test_starts_primary_live_with_no_ticks_yet`). That's the right call
    for the controller's own transition semantics, but wrong as the sole
    signal here: without also checking `has_ever_ticked`, a cold start
    with Upstox still connecting (or markets closed, so no tick will
    arrive for hours) would leave *both* feeds silent — Upstox because it
    genuinely has nothing yet, nse_poller because the controller looks
    "healthy" by never having failed. So the fallback poller runs
    whenever Upstox hasn't been configured, hasn't proven itself live
    even once yet, or has gone degraded/stale after having done so.
    """
    if not is_upstox_configured():
        return True
    controller = get_failover_controller()
    controller.evaluate()
    if not controller.has_ever_ticked:
        return True
    return controller.should_run_fallback_poller()


@lru_cache(maxsize=1)
def _instrument_key_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Build symbol<->instrument_key maps from the NIFTY 500 seed's ISINs.

    Upstox's NSE-equity instrument key convention is `NSE_EQ|<ISIN>`
    (confirmed against the V3 docs' worked examples) — no separate
    instrument-master download needed since the seed already carries ISIN.
    """
    seed_path = pathlib.Path(__file__).resolve().parents[2] / "data" / "nifty500_seed.json"
    symbol_to_key: dict[str, str] = {}
    key_to_symbol: dict[str, str] = {}
    try:
        entries = json.loads(seed_path.read_text())
    except Exception as exc:
        log.error("nifty500_seed_load_failed_for_instrument_keys", error=str(exc))
        return symbol_to_key, key_to_symbol

    for entry in entries:
        symbol = (entry.get("symbol") or "").strip()
        isin = (entry.get("isin") or "").strip()
        if not symbol or not isin:
            continue
        instrument_key = f"NSE_EQ|{isin}"
        symbol_to_key[symbol] = instrument_key
        key_to_symbol[instrument_key] = symbol
    return symbol_to_key, key_to_symbol


def get_subscription_instrument_keys() -> list[str]:
    symbol_to_key, _ = _instrument_key_maps()
    return list(symbol_to_key.values())


def symbol_for_instrument_key(instrument_key: str) -> str | None:
    _, key_to_symbol = _instrument_key_maps()
    return key_to_symbol.get(instrument_key)


async def _get_upstox_token() -> str | None:
    settings = get_settings()
    return settings.upstox_analytics_token or None


async def _handle_decoded_message(decoded: DecodedMessage) -> None:
    if decoded.market_info is not None:
        for segment, status in decoded.market_info.segment_status.items():
            await publish_market_status(
                MarketStatusEvent(
                    segment=segment,
                    status=status,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

    if not decoded.ticks:
        return

    candle_engine = get_candle_engine()
    market_state = get_market_state()

    for tick in decoded.ticks:
        get_feed_metrics().record_tick(tick.ltt, tick.received_at)

        symbol = symbol_for_instrument_key(tick.instrument_key)
        if symbol is None:
            continue  # subscribed to something outside our seeded universe

        change = tick.ltp - tick.close_price if tick.close_price else 0.0
        change_pct = (change / tick.close_price * 100) if tick.close_price else 0.0
        # Prefer the feed's own day-level OHLC (real open, running high/low)
        # over fabricating them from the current tick — that previously made
        # open/high/low always equal ltp, useless for anything range-based
        # (opening gap, % off high, breakout levels). Still guard high/low
        # against this exact tick in case the feed's own figures lag by one
        # update.
        if tick.day_open is not None:
            day_high = max(tick.day_high, tick.ltp) if tick.day_high is not None else tick.ltp
            day_low = min(tick.day_low, tick.ltp) if tick.day_low is not None else tick.ltp
            open_price = tick.day_open
        else:
            open_price = day_high = day_low = tick.ltp
        price_data = {
            "symbol": symbol,
            "ltp": tick.ltp,
            "open": open_price,
            "high": day_high,
            "low": day_low,
            "close": tick.ltp,
            "prev_close": tick.close_price,
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "volume": tick.vtt if tick.vtt is not None else 0,
            "timestamp": tick.received_at.isoformat(),
        }
        await set_json(f"price:{symbol}", price_data, ttl=PRICE_TTL)
        await publish("price_updates", json.dumps(price_data))

        market_state.get_or_create(symbol).record_tick(tick)

        try:
            completed = await candle_engine.on_tick(
                symbol=symbol,
                ltp=tick.ltp,
                volume_delta=tick.ltq,
                ts=tick.received_at,
            )
        except Exception as exc:  # candle persistence issues must never kill the tick loop
            log.error("candle_engine_on_tick_failed", symbol=symbol, error=str(exc))
            continue

        for candle in completed:
            await publish_candle_update(
                CandleUpdateEvent(
                    symbol=candle["symbol"],
                    timeframe=candle["timeframe"],
                    ts=candle["ts"],
                    open=float(candle["open"]),
                    high=float(candle["high"]),
                    low=float(candle["low"]),
                    close=float(candle["close"]),
                    volume=candle["volume"],
                )
            )


async def start_upstox_pipeline() -> UpstoxV3Provider:
    """Create and start the primary Upstox V3 feed. Caller owns shutdown via `.stop()`."""
    provider = UpstoxV3Provider(
        get_token=_get_upstox_token,
        on_message=_handle_decoded_message,
        failover=get_failover_controller(),
    )
    instrument_keys = get_subscription_instrument_keys()
    log.info("upstox_pipeline_starting", instrument_count=len(instrument_keys))
    await provider.start(instrument_keys)
    return provider

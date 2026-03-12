"""
Upstox WebSocket V3 Market Data Streamer.
Connects to Upstox's market data feed, decodes Protobuf messages,
and feeds ticks into the CandleBuilder + broadcasts via Redis pub/sub.
"""
from __future__ import annotations
import asyncio
import json
import ssl
from typing import Optional, Callable
import redis.asyncio as aioredis
import structlog

from config import settings
from data.upstox_auth import UpstoxAuthManager
from data.candle_builder import CandleBuilder, get_candle_builder
from data.indicator_engine import IndicatorEngine

log = structlog.get_logger(__name__)

# Redis pub/sub channel for broadcasting raw ticks to WebSocket handlers
TICKS_CHANNEL = "ticks"


class MarketDataStreamer:
    """
    Wraps Upstox WebSocket V3 market data streaming.
    Falls back to NSE mock data if Upstox is unavailable.
    """

    def __init__(
        self,
        auth_manager: UpstoxAuthManager,
        redis: aioredis.Redis,
        candle_builder: CandleBuilder,
        indicator_engine: Optional[IndicatorEngine] = None,
    ):
        self.auth = auth_manager
        self.redis = redis
        self.candle_builder = candle_builder
        self.indicator_engine = indicator_engine
        self._running = False
        self._ws = None
        self._on_tick_callbacks: list[Callable] = []

        # Register indicator recompute as candle close callback
        if indicator_engine:
            candle_builder.register_on_candle_close(indicator_engine.recompute)

    def register_on_tick(self, callback: Callable):
        self._on_tick_callbacks.append(callback)

    # ── Connection lifecycle ────────────────────────────────────────────────

    async def start(self, instruments: list[str]):
        """Connect to Upstox WebSocket and start streaming."""
        token = await self.auth.get_token_or_mock()

        if token and settings.upstox_configured:
            await self._connect_upstox(token, instruments)
        else:
            log.warning("upstox_unavailable", message="Starting mock data streamer")
            await self._start_mock_streamer(instruments)

    async def stop(self):
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    # ── Upstox WebSocket connection ─────────────────────────────────────────

    async def _connect_upstox(self, token: str, instruments: list[str]):
        """Connect to Upstox WebSocket V3 with Protobuf encoding."""
        try:
            import websockets

            ws_url = f"{settings.upstox_ws_url}?token={token}"
            ssl_context = ssl.create_default_context()

            self._running = True
            log.info("upstox_ws_connecting", url=settings.upstox_ws_url)

            async with websockets.connect(ws_url, ssl=ssl_context, ping_interval=30) as ws:
                self._ws = ws
                log.info("upstox_ws_connected")

                # Subscribe to instruments in batches
                await self._subscribe(ws, instruments[:500], "full")
                if len(instruments) > 500:
                    await self._subscribe(ws, instruments[500:3000], "ltpc")

                async for message in ws:
                    if not self._running:
                        break
                    await self._handle_message(message)

        except Exception as e:
            log.error("upstox_ws_error", error=str(e))
            log.info("falling_back_to_mock_streamer")
            await self._start_mock_streamer(instruments[:50])

    async def _subscribe(self, ws, instruments: list[str], mode: str):
        """Send subscription message to Upstox WebSocket."""
        msg = {
            "guid": "breakoutscan-sub",
            "method": "sub",
            "data": {
                "mode": mode,
                "instrumentKeys": instruments,
            },
        }
        await ws.send(json.dumps(msg))
        log.info("upstox_subscribed", count=len(instruments), mode=mode)

    async def _handle_message(self, raw_message: bytes):
        """Decode Protobuf message and process tick."""
        try:
            # Try to import and use Upstox SDK protobuf decoder
            from upstox_python_client.feeder import MarketDataFeedV3

            # Decode protobuf message
            decoded = MarketDataFeedV3.decode(raw_message)
            if not decoded or not decoded.feeds:
                return

            for instrument_key, feed_data in decoded.feeds.items():
                # Extract symbol from instrument_key (e.g. "NSE_EQ|INE009A01021" → stock data)
                ltpc = getattr(feed_data, "ltpc", None)
                if ltpc:
                    ltp = ltpc.ltp
                    volume = 0
                    # Extract symbol from our Redis map
                    symbol = instrument_key.split("|")[-1] if "|" in instrument_key else instrument_key
                    await self._process_tick(symbol, instrument_key, ltp, volume)

        except ImportError:
            # If upstox SDK not available, try parsing as JSON
            try:
                data = json.loads(raw_message)
                await self._process_json_tick(data)
            except Exception:
                pass
        except Exception as e:
            log.warning("tick_decode_error", error=str(e))

    async def _process_json_tick(self, data: dict):
        """Process a JSON-formatted tick (fallback)."""
        feeds = data.get("feeds", {})
        for instrument_key, feed in feeds.items():
            ltpc = feed.get("ltpc", {})
            ltp = ltpc.get("ltp")
            if ltp:
                await self._process_tick("UNKNOWN", instrument_key, float(ltp), 0)

    async def _process_tick(self, symbol: str, instrument_key: str, ltp: float, volume: int):
        """Process a decoded tick — update candles, cache price, broadcast."""
        # Update candles
        await self.candle_builder.on_tick(symbol, ltp, volume)

        # Cache LTP in Redis
        price_data = {"ltp": ltp, "volume": volume, "instrument_key": instrument_key}
        await self.redis.setex(f"ltp:{symbol}", 3600, json.dumps(price_data))

        # Publish to Redis pub/sub for WebSocket broadcast
        tick_msg = json.dumps({"symbol": symbol, "ltp": ltp, "volume": volume})
        await self.redis.publish(TICKS_CHANNEL, tick_msg)

        # Notify registered callbacks
        for cb in self._on_tick_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(symbol, ltp, volume))
                else:
                    cb(symbol, ltp, volume)
            except Exception:
                pass

    # ── Mock Streamer (development fallback) ──────────────────────────────

    async def _start_mock_streamer(self, symbols: list[str]):
        """
        Mock streamer is disabled when real yfinance data is available.
        Real data is loaded by data_initializer and refreshed periodically.
        """
        self._running = True
        log.info("mock_streamer_disabled", reason="yfinance_data_active")

        # Just keep alive without generating fake ticks
        while self._running:
            await asyncio.sleep(60)


# ── Global instance management ─────────────────────────────────────────────

_streamer: Optional[MarketDataStreamer] = None


def get_streamer() -> Optional[MarketDataStreamer]:
    return _streamer


def init_streamer(
    auth: UpstoxAuthManager,
    redis: aioredis.Redis,
    candle_builder: CandleBuilder,
    indicator_engine: Optional[IndicatorEngine] = None,
) -> MarketDataStreamer:
    global _streamer
    _streamer = MarketDataStreamer(auth, redis, candle_builder, indicator_engine)
    return _streamer

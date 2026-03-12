"""
BreakoutScan Backend — FastAPI Application Entry Point.
"""
from __future__ import annotations
import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings

log = structlog.get_logger(__name__)

# ── Global Redis client ────────────────────────────────────────────────────
_redis: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    return _redis


# ── Application lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown logic."""
    log.info("breakoutscan_starting", environment=settings.environment)

    # 1. Init Redis
    redis = get_redis_client()

    # 2. Init CandleBuilder
    from data.candle_builder import get_candle_builder
    candle_builder = get_candle_builder()

    # 3. Init IndicatorEngine
    from data.indicator_engine import init_indicator_engine, get_indicator_engine
    indicator_engine = init_indicator_engine(redis, candle_builder)

    # 4. Init WebSocket manager
    from websocket.manager import get_ws_manager
    ws_manager = get_ws_manager()

    # 5. Register candle-close callback to broadcast scan hits via WebSocket
    async def on_candle_close(symbol, timeframe, candle):
        indicators = await indicator_engine.get_indicators(symbol, timeframe)
        if indicators and timeframe == "15min":
            # Quick check: EMA crossover for live scan hit broadcast
            ema9 = (indicators.get("ema_9") or [None])[0]
            ema21 = (indicators.get("ema_21") or indicators.get("ema_20") or [None])[0]
            if ema9 and ema21 and ema9 > ema21:
                prev_ema9 = (indicators.get("ema_9") or [None, None])[1]
                if prev_ema9 and prev_ema9 <= ema21:
                    await ws_manager.broadcast_scan_hit(
                        scan_id="ema_921_crossover",
                        scan_name="EMA 9/21 Crossover",
                        symbol=symbol,
                        ltp=candle.close,
                        matched=["EMA9 crossed above EMA21"],
                        ts=time.time(),
                    )

    candle_builder.register_on_candle_close(on_candle_close)

    # 6. Init tick → WebSocket bridge (Redis pub/sub listener)
    async def redis_tick_listener():
        pubsub = redis.pubsub()
        await pubsub.subscribe("ticks")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    tick = json.loads(message["data"])
                    symbol = tick.get("symbol", "")
                    ltp = tick.get("ltp", 0)
                    volume = tick.get("volume", 0)
                    # Get change_pct from LTP cache
                    await ws_manager.broadcast_price(
                        symbol=symbol,
                        ltp=ltp,
                        change_pct=0.0,  # Computed from daily data
                        volume=volume,
                        ts=time.time(),
                    )
                except Exception:
                    pass

    tick_task = asyncio.create_task(redis_tick_listener())

    # 7. Start market data streamer
    from data.upstox_auth import get_auth_manager
    from data.upstox_streamer import init_streamer

    auth = await get_auth_manager()
    streamer = init_streamer(auth, redis, candle_builder, indicator_engine)

    # Get initial instrument list for subscription
    from screener.engine import _DEMO_STOCK_DATA
    symbols = list(_DEMO_STOCK_DATA.keys())

    # Start streamer in background
    stream_task = asyncio.create_task(streamer.start(symbols))

    # 8. Start instruments setup (daily, non-blocking)
    async def daily_setup():
        await asyncio.sleep(2)  # Let server start first
        try:
            from data.upstox_instruments import run_daily_instrument_setup
            await run_daily_instrument_setup()
        except Exception as e:
            log.warning("daily_setup_failed", error=str(e))

    asyncio.create_task(daily_setup())

    # 9. Initialize real market data from Yahoo Finance
    from data.data_initializer import initialize_market_data, fetch_intraday_data, periodic_refresh

    async def init_real_data():
        await asyncio.sleep(1)  # Let server start first
        try:
            log.info("fetching_real_market_data_from_yfinance")
            await initialize_market_data(redis)
            await fetch_intraday_data(redis)
            log.info("real_market_data_loaded")
        except Exception as e:
            log.error("real_data_init_failed", error=str(e))

    data_init_task = asyncio.create_task(init_real_data())

    # 10. Start periodic data refresh (every 5 minutes)
    refresh_task = asyncio.create_task(periodic_refresh(redis, interval_seconds=300))

    log.info("breakoutscan_started", mode="live" if settings.upstox_configured else "yfinance")

    yield  # ── Server is running ──

    # Shutdown
    log.info("breakoutscan_shutting_down")
    tick_task.cancel()
    stream_task.cancel()
    refresh_task.cancel()
    data_init_task.cancel()
    await streamer.stop()
    if _redis:
        await _redis.aclose()


# ── Create FastAPI app ─────────────────────────────────────────────────────

app = FastAPI(
    title="BreakoutScan API",
    description="India's most powerful real-time stock screener API",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ───────────────────────────────────────────────────────

from routes.auth import router as auth_router
from routes.screener import router as screener_router
from routes.live import router as live_router
from routes.stocks import router as stocks_router
from routes.watchlist import router as watchlist_router
from routes.alerts import router as alerts_router

app.include_router(auth_router)
app.include_router(screener_router)
app.include_router(live_router)
app.include_router(stocks_router)
app.include_router(watchlist_router)
app.include_router(alerts_router)


# ── REST Endpoints ─────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "mode": "live" if settings.upstox_configured else "mock",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    redis = get_redis_client()
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": "ok" if redis_ok else "unavailable",
        "upstox": "configured" if settings.upstox_configured else "not_configured",
        "mode": "live" if (settings.upstox_configured and redis_ok) else "mock",
    }


# ── WebSocket Endpoints ────────────────────────────────────────────────────

@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    """Stream all live prices."""
    from websocket.manager import get_ws_manager
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket, "prices")
    try:
        while True:
            # Send heartbeat every 30s
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "heartbeat", "ts": time.time()}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "prices")


@app.websocket("/ws/prices/{symbol}")
async def ws_price_symbol(websocket: WebSocket, symbol: str):
    """Stream live price for a specific symbol."""
    from websocket.manager import get_ws_manager
    ws_manager = get_ws_manager()
    symbol = symbol.upper()
    await ws_manager.connect(websocket, "prices")
    await ws_manager.subscribe_to_symbol(websocket, symbol)

    # Send initial LTP snapshot
    try:
        redis = get_redis_client()
        data = await redis.get(f"ltp:{symbol}")
        if data:
            tick = json.loads(data)
            await websocket.send_text(json.dumps({
                "type": "price_update",
                "symbol": symbol,
                **tick,
                "ts": time.time(),
            }))
    except Exception:
        pass

    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "heartbeat", "ts": time.time()}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "prices")


@app.websocket("/ws/scans")
async def ws_scans(websocket: WebSocket):
    """Stream live scan hits as they happen."""
    from websocket.manager import get_ws_manager
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket, "scans")
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "heartbeat", "ts": time.time()}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "scans")


@app.websocket("/ws/alerts/{user_id}")
async def ws_alerts(websocket: WebSocket, user_id: str):
    """Stream personal alert triggers for a specific user."""
    from websocket.manager import get_ws_manager
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket, "alerts")
    await ws_manager.subscribe_to_user_alerts(websocket, user_id)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "heartbeat", "ts": time.time()}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "alerts")

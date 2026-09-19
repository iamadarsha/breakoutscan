from __future__ import annotations

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager

print("BreakoutScan: loading main module...", file=sys.stderr, flush=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.ws import ws_router

logger = logging.getLogger(__name__)
print("BreakoutScan: all imports OK", file=sys.stderr, flush=True)


_poller_running = False
_breakout_running = False
_universe_size = 0
_startup_time: float = 0.0
_db_ready = False

# Bounded startup DB connectivity retry schedule (seconds between attempts).
# A transient network blip degrades gracefully (see below); a genuinely
# invalid config (e.g. localhost in production) never reaches this point —
# it's rejected earlier by Settings' own validator, at import time.
_DB_STARTUP_RETRY_DELAYS = (0, 2, 5, 15, 30)


async def _poller_watchdog() -> None:
    """Run nse_poller_loop forever, restarting it if it ever raises.

    Uses exponential back-off (5 s → 10 s → 20 s … capped at 5 min) so a
    persistent crash doesn't spin-loop and exhaust CPU/memory.
    """
    global _poller_running

    from app.services.nse_poller import nse_poller_loop

    delay = 5
    while True:
        _poller_running = True
        try:
            logger.info("NSE poller (re)starting…")
            await nse_poller_loop()
        except asyncio.CancelledError:
            _poller_running = False
            raise
        except Exception as exc:
            _poller_running = False
            logger.error(
                "NSE poller crashed: %s — restarting in %ds", exc, delay
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 300)  # cap at 5 minutes
        else:
            # nse_poller_loop returned normally (shouldn't happen); restart after 5 s
            _poller_running = False
            logger.warning("NSE poller exited unexpectedly — restarting in 5s")
            await asyncio.sleep(5)
            delay = 5  # reset backoff


async def _run_morning_ai_suggestions() -> None:
    """Scheduled job body: read news + market data and generate AI picks.

    Runs on the schedule set up in `lifespan()` below (trading days only,
    IST). A failure here must never take down the scheduler itself —
    APScheduler already isolates job exceptions, but this still logs with
    the same shape as the rest of the app's background tasks.
    """
    from app.services.ai_suggestions import generate_suggestions

    logger.info("morning_ai_suggestions: starting scheduled generation")
    try:
        result = await asyncio.wait_for(generate_suggestions(), timeout=120)
        total = sum(len(result.get(k, [])) for k in ("intraday", "weekly", "monthly"))
        logger.info(
            "morning_ai_suggestions: done source=%s picks=%d",
            result.get("source", "?"), total,
        )
    except asyncio.TimeoutError:
        logger.error("morning_ai_suggestions: 120s timeout exceeded")
    except Exception as exc:
        logger.error("morning_ai_suggestions_failed: %s", exc, exc_info=True)


async def _breakout_watchdog() -> None:
    """Run breakout_engine_loop forever, restarting it if it ever raises.

    Same crash-restart-with-backoff pattern as `_poller_watchdog` above.
    """
    global _breakout_running

    from app.breakouts.engine import breakout_engine_loop

    delay = 5
    while True:
        _breakout_running = True
        try:
            logger.info("Breakout engine (re)starting…")
            await breakout_engine_loop()
        except asyncio.CancelledError:
            _breakout_running = False
            raise
        except Exception as exc:
            _breakout_running = False
            logger.error("Breakout engine crashed: %s — restarting in %ds", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 300)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _poller_running, _universe_size, _startup_time, _db_ready
    _startup_time = time.monotonic()

    from app.db.session import check_db_connectivity
    from app.services.nse_poller import populate_universe_fallback

    configure_logging()
    logger.info("BreakoutScan API starting up...")

    settings = get_settings()
    logger.info(
        "Config: GEMINI_API_KEY=%s, GROQ_API_KEY=%s, INDIAN_API_KEY=%s, REDIS=%s",
        "***set***" if settings.gemini_api_key else "MISSING",
        "***set***" if settings.groq_api_key else "MISSING",
        "***set***" if settings.indian_api_key else "MISSING",
        "configured" if settings.redis_url else "MISSING",
    )

    # Bounded DB connectivity check. Settings' own validator already
    # refuses to start with an invalid production config (localhost DB,
    # empty DATABASE_URL) — what's left here is a *reachability* problem
    # (network blip, provider outage), which should degrade gracefully
    # rather than crash the whole process. /health/ready reports this.
    for i, wait_s in enumerate(_DB_STARTUP_RETRY_DELAYS):
        if wait_s:
            await asyncio.sleep(wait_s)
        _db_ready = await check_db_connectivity()
        if _db_ready:
            logger.info("Database connectivity confirmed (attempt %d)", i + 1)
            break
        logger.warning(
            "Database not reachable yet (attempt %d/%d)", i + 1, len(_DB_STARTUP_RETRY_DELAYS)
        )
    if not _db_ready:
        logger.error(
            "Database unreachable after %d attempts — starting anyway in DEGRADED mode; "
            "candle persistence will fail until this recovers",
            len(_DB_STARTUP_RETRY_DELAYS),
        )

    upstox_provider = None
    if settings.upstox_analytics_token:
        try:
            from app.market.pipeline import start_upstox_pipeline

            upstox_provider = await start_upstox_pipeline()
            logger.info("Upstox V3 primary feed started")
        except Exception as exc:
            logger.warning(
                "Upstox V3 primary feed failed to start (%s) — nse_poller fallback will carry prices",
                exc,
            )
    else:
        logger.info("UPSTOX_ANALYTICS_TOKEN not set — nse_poller is the only price feed")

    from app.core.loop_monitor import get_event_loop_monitor

    event_loop_monitor_task = asyncio.create_task(
        get_event_loop_monitor().run(), name="event_loop_monitor"
    )
    logger.info("Event-loop lag monitor started")

    watchdog_task = None
    breakout_watchdog_task = None
    fundamentals_task = None
    try:
        from app.services.redis_cache import get_redis

        redis = await asyncio.wait_for(get_redis(), timeout=10.0)
        pong = await asyncio.wait_for(redis.ping(), timeout=5.0)
        logger.info("Redis connected: %s", pong)

        # Pre-populate universe so the screener works from the very first request
        try:
            symbols = await populate_universe_fallback()
            _universe_size = len(symbols)
            logger.info("Universe pre-populated with %d symbols", _universe_size)
        except Exception as e:
            logger.warning("Failed to pre-populate universe: %s", e)
            symbols = []

        # NOTE: Startup bulk compute intentionally removed.
        # The NSE poller fires _run_bulk_compute on its first successful poll cycle
        # (within ~30 s of startup) with the concurrency guard preventing overlapping
        # runs.  Firing it here too caused two concurrent computes at boot, doubling
        # peak RAM and OOM-killing the container.

        # Start self-healing watchdog (replaces the bare create_task)
        watchdog_task = asyncio.create_task(_poller_watchdog(), name="poller_watchdog")
        logger.info("NSE poller watchdog started")

        breakout_watchdog_task = asyncio.create_task(_breakout_watchdog(), name="breakout_watchdog")
        logger.info("Breakout engine watchdog started")

        from app.services.fundamentals_refresh import fundamentals_refresh_loop

        fundamentals_task = asyncio.create_task(
            fundamentals_refresh_loop(), name="fundamentals_refresh"
        )
        logger.info("Fundamentals refresh scheduled")
    except asyncio.TimeoutError:
        logger.warning("Redis connection timed out – starting without Redis")
    except Exception as exc:
        logger.warning(
            "Redis not available at startup (%s) – features relying on it will degrade gracefully",
            exc,
        )

    # Scheduled morning AI-picks generation: reads RSS/news + live market
    # data and produces fresh picks once daily, trading days only, rather
    # than only ever generating lazily on whoever's first request happens
    # to land after the previous day's cache expires.
    ai_scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        ai_scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        ai_scheduler.add_job(
            _run_morning_ai_suggestions,
            trigger=CronTrigger(day_of_week="mon-fri", hour=9, minute=15, timezone="Asia/Kolkata"),
            id="morning_ai_suggestions",
            misfire_grace_time=3600,
            coalesce=True,
        )
        ai_scheduler.start()
        logger.info("Morning AI-suggestions scheduler started (09:15 IST, Mon-Fri)")
    except Exception as exc:
        logger.warning("Failed to start AI-suggestions scheduler: %s", exc)

    logger.info("BreakoutScan API ready")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    if ai_scheduler is not None:
        ai_scheduler.shutdown(wait=False)
        logger.info("Morning AI-suggestions scheduler stopped")

    event_loop_monitor_task.cancel()
    try:
        await event_loop_monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("Event-loop lag monitor stopped")

    _poller_running = False
    if watchdog_task is not None:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass
        logger.info("NSE poller watchdog stopped")

    if breakout_watchdog_task is not None:
        breakout_watchdog_task.cancel()
        try:
            await breakout_watchdog_task
        except asyncio.CancelledError:
            pass
        logger.info("Breakout engine watchdog stopped")

    if fundamentals_task is not None:
        fundamentals_task.cancel()
        try:
            await fundamentals_task
        except asyncio.CancelledError:
            pass
        logger.info("Fundamentals refresh stopped")

    if upstox_provider is not None:
        await upstox_provider.stop()
        logger.info("Upstox V3 primary feed stopped")


settings = get_settings()

app = FastAPI(
    title="BreakoutScan API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://breakoutscan-web.vercel.app",
    "https://breakoutscan.in",
    "https://www.breakoutscan.in",
]
_extra = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
_allowed_origins = list(dict.fromkeys(_DEFAULT_ORIGINS + _extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"message": "BreakoutScan API"}


@app.get("/ping", tags=["system"])
async def ping() -> dict[str, str]:
    """Lightweight liveness probe used by Railway / load balancers."""
    return {"pong": "ok"}


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Deep health check — reports Redis liveness, poller state, uptime.

    Kept as-is: the deployed frontend's backend-health proxy calls this
    exact path/shape today. New, more granular checks are additive below.
    """
    from app.services.redis_cache import redis_ping

    redis_ok = await redis_ping()
    uptime_s = int(time.monotonic() - _startup_time) if _startup_time else 0

    overall = "ok" if redis_ok and _poller_running else "degraded"

    return {
        "status": overall,
        "redis": "ok" if redis_ok else "unavailable",
        "poller": "running" if _poller_running else "stopped",
        "universe_size": _universe_size,
        "uptime_seconds": uptime_s,
    }


@app.get("/health/live", tags=["system"])
async def health_live() -> dict:
    """Liveness only: the process is alive and can respond. Never checks
    a downstream dependency — a slow/down Postgres or Redis must not make
    an orchestrator think the process itself needs restarting."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["system"])
async def health_ready() -> JSONResponse:
    """Readiness: safe to receive production traffic right now.

    Checks the dependencies a request actually needs — Redis and
    Postgres — live, each call. Returns HTTP 503 when not ready so an
    external monitor or load balancer can act on it without parsing the body.
    """
    from app.db.session import check_db_connectivity
    from app.services.redis_cache import redis_ping

    redis_ok = await redis_ping()
    db_ok = await check_db_connectivity()
    ready = redis_ok and db_ok

    body = {
        "status": "ready" if ready else "not_ready",
        "redis": "ok" if redis_ok else "unavailable",
        "database": "ok" if db_ok else "unavailable",
    }
    return JSONResponse(content=body, status_code=200 if ready else 503)


@app.get("/health/data", tags=["system"])
async def health_data() -> dict:
    """Market-data health: feed provider, session state, coverage.

    This is a v1, honestly-scoped snapshot of currently-available signals
    (which feed is primary/fallback, whether the market is open, how many
    symbols are tracked) — NOT the full LIVE/DEGRADED/STALE/NO_DATA
    per-symbol freshness contract, which is a larger, separate piece of
    work. Never claims freshness it can't currently verify.
    """
    from app.api.routes.market import _market_status_now
    from app.breakouts.engine import get_last_scan_coverage
    from app.core.loop_monitor import get_event_loop_monitor
    from app.market.feed_metrics import get_feed_metrics
    from app.market.pipeline import get_failover_controller, is_upstox_configured

    market_status = await _market_status_now()

    provider = "upstox_v3" if is_upstox_configured() else "nse_fallback_only"
    failover_status = None
    if is_upstox_configured():
        try:
            failover_status = get_failover_controller().status.value
        except Exception:
            failover_status = "unknown"

    return {
        "provider": provider,
        "failover_status": failover_status,
        "market_is_open": market_status.is_open,
        "market_status": market_status.status,
        "universe_size": _universe_size,
        "poller_running": _poller_running,
        "breakout_engine_running": _breakout_running,
        # Coverage from the most recently *completed* breakout-scan cycle —
        # a scan that silently examined fewer symbols than expected is not
        # a successful full scan, so this is surfaced explicitly rather
        # than assumed from universe_size alone.
        "last_scan_coverage": get_last_scan_coverage(),
        # Feed freshness (Phase 1 observability) — exchange-tick age and
        # transport-arrival age are kept separate so "market is quiet" is
        # never confused with "our feed is stale/disconnected".
        "feed_health": get_feed_metrics().snapshot(),
        # Direct event-loop scheduling-delay measurement, not inferred from
        # reconnects — see app/core/loop_monitor.py.
        "event_loop_lag": get_event_loop_monitor().snapshot(),
    }

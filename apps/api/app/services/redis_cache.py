"""Redis async singleton with convenience helpers.

All public helpers are wrapped with try/except so a Redis outage
(connection refused, timeout, READONLY replica, etc.) degrades gracefully
instead of propagating exceptions to callers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings

log = structlog.get_logger(__name__)
_logger = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the global :class:`aioredis.Redis` instance."""
    global _pool  # noqa: PLW0603
    if _pool is None:
        settings = get_settings()
        # BlockingConnectionPool makes callers wait for a free connection
        # instead of raising "Too many connections" the instant a burst
        # (bulk indicator compute + scans + engine) exceeds the cap.
        connection_pool = aioredis.BlockingConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=settings.redis_max_connections,
            timeout=10,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        _pool = aioredis.Redis(connection_pool=connection_pool)
        log.info("redis_connected", url=settings.redis_url)
    return _pool


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        await _pool.aclose(close_connection_pool=True)
        _pool = None
        log.info("redis_closed")


async def redis_ping() -> bool:
    """Return True if Redis is reachable, False otherwise."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Convenience wrappers — all silently return defaults on failure
# ---------------------------------------------------------------------------


async def set_with_ttl(key: str, value: str, ttl: int) -> None:
    """SET *key* to *value* with an expiry of *ttl* seconds."""
    try:
        r = await get_redis()
        await r.set(key, value, ex=ttl)
    except Exception as exc:
        _logger.warning("redis set_with_ttl failed key=%s: %s", key, exc)


async def get_value(key: str) -> str | None:
    """GET a plain string value. Returns None on miss or error."""
    try:
        r = await get_redis()
        return await r.get(key)
    except Exception as exc:
        _logger.warning("redis get_value failed key=%s: %s", key, exc)
        return None


async def set_json(key: str, obj: Any, ttl: int | None = None) -> None:
    """Serialize *obj* as JSON and store under *key*."""
    try:
        r = await get_redis()
        payload = json.dumps(obj, default=str)
        if ttl is not None:
            await r.set(key, payload, ex=ttl)
        else:
            await r.set(key, payload)
    except Exception as exc:
        _logger.warning("redis set_json failed key=%s: %s", key, exc)


async def get_json(key: str) -> Any | None:
    """Retrieve and deserialize a JSON value. Returns None on miss or error."""
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        _logger.warning("redis get_json failed key=%s: %s", key, exc)
        return None


async def hset_dict(key: str, mapping: dict[str, Any], ttl: int | None = None) -> None:
    """Write a full dict into a Redis hash, optionally setting a TTL."""
    try:
        r = await get_redis()
        str_mapping = {k: str(v) for k, v in mapping.items()}
        await r.hset(key, mapping=str_mapping)
        if ttl is not None:
            await r.expire(key, ttl)
    except Exception as exc:
        _logger.warning("redis hset_dict failed key=%s: %s", key, exc)


async def hget_all(key: str) -> dict[str, str]:
    """Return all fields of a Redis hash. Returns empty dict on error."""
    try:
        r = await get_redis()
        return await r.hgetall(key)
    except Exception as exc:
        _logger.warning("redis hget_all failed key=%s: %s", key, exc)
        return {}


async def publish(channel: str, message: str) -> int:
    """Publish *message* to a Redis Pub/Sub *channel*.

    Returns the number of subscribers that received the message, or 0 on error.
    """
    try:
        r = await get_redis()
        return await r.publish(channel, message)
    except Exception as exc:
        _logger.warning("redis publish failed channel=%s: %s", channel, exc)
        return 0


async def subscribe(channel: str) -> aioredis.client.PubSub:
    """Return an :class:`aioredis.client.PubSub` subscribed to *channel*.

    Caller is responsible for iterating and closing the subscription.
    """
    r = await get_redis()
    ps = r.pubsub()
    await ps.subscribe(channel)
    return ps

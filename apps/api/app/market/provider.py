"""Upstox V3 realtime market-data WebSocket client.

Binary protobuf feed per
https://upstox.com/developer/api-documentation/v3/get-market-data-feed/.
V3 requires a REST "authorize" call (bearer token in) that returns a
single-use, per-session WebSocket URL with an embedded auth code — verified
against https://upstox.com/developer/api-documentation/get-market-data-feed-authorize-v3/
(response shape: `{"data": {"authorized_redirect_uri": "wss://..."}}`).

NOT YET EXERCISED AGAINST A LIVE CONNECTION: the repo owner has no Upstox
Developer App / Analytics Token as of this Phase 2 round (see
docs/DATA_PROVIDER_MATRIX.md). This class is written and unit-tested
against synthetic protobuf fixtures (see
apps/api/app/tests/test_provider.py) but its actual network behavior
(auth success, subscription ack, reconnect against a real server) is
unverified until Milestone 2.2.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx
import structlog
import websockets

from app.market.failover import FailoverController
from app.market.feed_metrics import get_feed_metrics
from app.market.normalize import DecodedMessage, MessageType, decode_feed_response

log = structlog.get_logger(__name__)

_AUTHORIZE_URL = "https://api.upstox.com/v3/feed/market-data-feed/authorize"

_RECONNECT_MIN_WAIT = 1.0
_RECONNECT_MAX_WAIT = 60.0
_JITTER_FRACTION = 0.25  # unlike the old (unused) upstox_streamer.py's unjittered backoff


@dataclass
class SubscriptionRequest:
    """Mode values per the live V3 docs (verified 2026-09-14 against
    https://upstox.com/developer/api-documentation/v3/get-market-data-feed/):
    `ltpc`, `option_greeks`, `full` (LTPC + 5 market-depth levels + option
    greeks), `full_d30` (30 levels, Upstox Plus only, 50-key cap). The
    previous value here, `full_d5`, is not a valid mode string in the
    current API at all — it silently produced a connection that received
    only the unconditional initial `market_info` heartbeat and no actual
    ticks, discovered via live verification on 2026-09-14."""

    instrument_keys: list[str]
    mode: str = "full"

    def to_json(self, guid: str, method: str = "sub") -> str:
        return json.dumps(
            {
                "guid": guid,
                "method": method,
                "data": {"mode": self.mode, "instrumentKeys": self.instrument_keys},
            }
        )


GetTokenFn = Callable[[], Awaitable[str | None]]
OnMessageFn = Callable[[DecodedMessage], Awaitable[None]]


class UpstoxV3Provider:
    """Manages one authenticated V3 WebSocket connection.

    `get_token` and `on_message` are injected so the connection logic can
    be unit-tested without hitting a real Upstox server (see
    apps/api/app/tests/test_provider.py, which fakes both).
    """

    def __init__(
        self,
        get_token: GetTokenFn,
        on_message: OnMessageFn,
        failover: FailoverController | None = None,
        max_subscription_keys: int = 2000,  # full_d5 mode cap per Upstox V3 docs
    ) -> None:
        self._get_token = get_token
        self._on_message = on_message
        self.failover = failover or FailoverController()
        self._max_subscription_keys = max_subscription_keys
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._subscribed_keys: list[str] = []
        self._ws: Any | None = None
        self._messages_received = 0

    def _apply_subscription_cap(self, instrument_keys: list[str]) -> list[str]:
        if len(instrument_keys) > self._max_subscription_keys:
            log.warning(
                "upstox_v3_subscription_truncated",
                requested=len(instrument_keys),
                cap=self._max_subscription_keys,
            )
            return instrument_keys[: self._max_subscription_keys]
        return list(instrument_keys)

    async def start(self, instrument_keys: list[str]) -> None:
        self._subscribed_keys = self._apply_subscription_cap(instrument_keys)
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="upstox_v3_provider")

    async def stop(self) -> None:
        self._running = False
        if self._ws is not None:
            await self._ws.close()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _authorize(self) -> str:
        token = await self._get_token()
        if not token:
            raise RuntimeError("no Upstox bearer token available")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                _AUTHORIZE_URL,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()
        return body["data"]["authorized_redirect_uri"]

    async def _run_loop(self) -> None:
        attempt = 0
        while self._running:
            try:
                ws_url = await self._authorize()
                log.info("upstox_v3_authorized", subscribed_count=len(self._subscribed_keys))
                # ping_interval=None: disables the `websockets` library's own
                # protocol-level ping/pong keepalive. Confirmed live on
                # 2026-09-15 that Upstox's server doesn't answer it —
                # connections were dropping with "sent 1011 (internal error)
                # keepalive ping timeout; no close frame received" on a
                # regular ~50-60s cadence, measured to be *unrelated* to our
                # own event-loop health (event-loop lag was independently
                # confirmed under 1s throughout the same window). Upstox's
                # own MARKET_INFO messages and continuous tick flow already
                # prove liveness at the application level; a genuinely dead
                # TCP connection still surfaces as a read error in the
                # `async for raw in ws` loop below and is handled by the
                # existing reconnect-with-backoff logic either way.
                async with websockets.connect(ws_url, max_size=None, ping_interval=None) as ws:
                    self._ws = ws
                    if attempt > 0:
                        get_feed_metrics().record_reconnect()
                    attempt = 0
                    log.info("upstox_v3_ws_connected")
                    await self._subscribe(ws)
                    log.info("upstox_v3_subscribed", instrument_count=len(self._subscribed_keys))
                    async for raw in ws:
                        if isinstance(raw, str):
                            continue  # V3 sends binary frames only
                        await self._handle_raw(raw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("upstox_v3_connection_error", error=str(exc), attempt=attempt)
            finally:
                self._ws = None

            if not self._running:
                break
            attempt += 1
            delay = min(_RECONNECT_MIN_WAIT * (2**attempt), _RECONNECT_MAX_WAIT)
            delay += random.uniform(0, delay * _JITTER_FRACTION)
            await asyncio.sleep(delay)

    async def _handle_raw(self, raw: bytes) -> None:
        self._messages_received += 1
        decoded = decode_feed_response(raw)
        if self._messages_received <= 3 or self._messages_received % 100 == 0:
            log.info(
                "upstox_v3_message_received",
                count=self._messages_received,
                raw_bytes=len(raw),
                decoded_type=str(decoded.type),
                tick_count=len(decoded.ticks) if decoded.ticks else 0,
            )
        if decoded.type in (MessageType.LIVE_FEED, MessageType.INITIAL_FEED) and decoded.ticks:
            self.failover.record_primary_tick()
        await self._on_message(decoded)

    async def _subscribe(self, ws: Any) -> None:
        """Per the V3 docs' "Binary message format" note, the subscription
        request must be sent as a binary frame, not a text frame — the
        `websockets` library sends `str` as text and `bytes` as binary, so
        the JSON payload is UTF-8-encoded before sending. Sending it as
        text produced an accepted connection that silently never received
        real tick data, discovered via live verification on 2026-09-14."""
        req = SubscriptionRequest(instrument_keys=self._subscribed_keys)
        guid = f"bos-{int(time.time())}"
        await ws.send(req.to_json(guid).encode("utf-8"))

    def is_feed_alive(self) -> bool:
        """True unless the failover controller has moved off the primary feed."""
        from app.market.failover import FeedStatus

        return self.failover.evaluate() in (FeedStatus.PRIMARY_LIVE, FeedStatus.RECOVERING)

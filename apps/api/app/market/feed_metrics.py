"""Feed-freshness and reconnect tracking for the primary Upstox V3 feed.

Phase 1 observability (see BreakoutScan_Final_Fix_Plan_Sanity_Check.md):
before changing anything about *how* ticks are processed, first measure
whether the feed is actually falling behind. Two ages are tracked
separately and must never be conflated:

- ``last_exchange_tick_age_ms`` — how long ago the exchange itself last
  traded this instrument (derived from Upstox's own ``ltt``). A large
  value here can mean genuine market quiet, not a broken feed.
- ``last_received_age_ms`` — how long ago *our* process last received any
  message from the WebSocket, regardless of which instrument. A large
  value here means the feed itself is stale/disconnected.

Recording a tick is O(1) attribute writes only — safe to call from the
hot per-tick path with zero measurable overhead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache


@dataclass
class FeedMetrics:
    last_exchange_tick_ms: int | None = field(default=None, init=False)
    last_received_at: datetime | None = field(default=None, init=False)
    reconnect_count: int = field(default=0, init=False)

    def record_tick(self, ltt_epoch_ms: int, received_at: datetime) -> None:
        # A tick without a valid ltt (0/None from a degraded payload) must
        # never regress the freshness reading backed by a real prior value.
        if ltt_epoch_ms:
            if self.last_exchange_tick_ms is None or ltt_epoch_ms >= self.last_exchange_tick_ms:
                self.last_exchange_tick_ms = ltt_epoch_ms
        if self.last_received_at is None or received_at >= self.last_received_at:
            self.last_received_at = received_at

    def record_reconnect(self) -> None:
        self.reconnect_count += 1

    def snapshot(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1000)

        exchange_age_ms = (
            now_ms - self.last_exchange_tick_ms if self.last_exchange_tick_ms is not None else None
        )
        received_age_ms = (
            int((now - self.last_received_at).total_seconds() * 1000)
            if self.last_received_at is not None
            else None
        )
        return {
            "last_exchange_tick_age_ms": exchange_age_ms,
            "last_received_age_ms": received_age_ms,
            "reconnect_count": self.reconnect_count,
        }


@lru_cache(maxsize=1)
def get_feed_metrics() -> FeedMetrics:
    return FeedMetrics()

"""Direct measurement of asyncio event-loop scheduling delay.

Phase 1 observability (see BreakoutScan_Final_Fix_Plan_Sanity_Check.md):
the hypothesis is that CPU-bound breakout-scan work starves the event
loop long enough that Upstox's WebSocket keepalive pings can't be
answered in time, causing the reconnect storms behind the price
staleness. This module measures that directly instead of inferring it
from reconnect counts — schedule a short sleep on a fixed cadence and
record how much longer than requested it actually took to wake up; any
excess is time the loop spent blocked on something else.

Deliberately dependency-free (stdlib only) so it can run before Redis/DB
are confirmed reachable and never itself becomes a failure point.
"""

from __future__ import annotations

import asyncio
from collections import deque
from functools import lru_cache

_INTERVAL_SECONDS = 0.2
_WINDOW_SIZE = 300  # ~60s of samples at the default interval


class EventLoopMonitor:
    def __init__(self, interval: float = _INTERVAL_SECONDS, window: int = _WINDOW_SIZE) -> None:
        self._interval = interval
        self._samples: deque[float] = deque(maxlen=window)

    async def run(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            start = loop.time()
            await asyncio.sleep(self._interval)
            elapsed = loop.time() - start
            lag_seconds = max(0.0, elapsed - self._interval)
            self._samples.append(lag_seconds)

    def snapshot(self) -> dict:
        if not self._samples:
            return {"p50_ms": None, "p95_ms": None, "p99_ms": None, "max_ms": None, "samples": 0}

        ordered = sorted(self._samples)
        n = len(ordered)

        def _percentile_ms(p: float) -> float:
            idx = min(n - 1, int(p * n))
            return round(ordered[idx] * 1000, 1)

        return {
            "p50_ms": _percentile_ms(0.50),
            "p95_ms": _percentile_ms(0.95),
            "p99_ms": _percentile_ms(0.99),
            "max_ms": round(ordered[-1] * 1000, 1),
            "samples": n,
        }


@lru_cache(maxsize=1)
def get_event_loop_monitor() -> EventLoopMonitor:
    return EventLoopMonitor()

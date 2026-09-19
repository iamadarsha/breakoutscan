"""Event-loop lag monitor — percentile math on injected samples (fast,
deterministic) plus one short real-run smoke test proving `run()` actually
accumulates samples on a live event loop."""

from __future__ import annotations

import asyncio

from app.core.loop_monitor import EventLoopMonitor


def test_snapshot_with_no_samples_is_all_none():
    monitor = EventLoopMonitor()
    assert monitor.snapshot() == {
        "p50_ms": None,
        "p95_ms": None,
        "p99_ms": None,
        "max_ms": None,
        "samples": 0,
    }


def test_snapshot_percentiles_over_injected_samples():
    monitor = EventLoopMonitor()
    # 0..99 ms of lag, evenly distributed — easy-to-reason-about percentiles.
    for ms in range(100):
        monitor._samples.append(ms / 1000)  # noqa: SLF001 — direct injection for deterministic math

    snapshot = monitor.snapshot()
    assert snapshot["samples"] == 100
    assert snapshot["p50_ms"] == 50.0
    assert snapshot["p95_ms"] == 95.0
    assert snapshot["p99_ms"] == 99.0
    assert snapshot["max_ms"] == 99.0


def test_window_is_bounded_and_drops_oldest_samples():
    monitor = EventLoopMonitor(window=5)
    for ms in range(10):
        monitor._samples.append(ms / 1000)  # noqa: SLF001
    assert monitor.snapshot()["samples"] == 5
    # Only the last 5 (5..9 ms) should remain — the max must reflect that.
    assert monitor.snapshot()["max_ms"] == 9.0


async def test_run_accumulates_real_samples_on_a_live_loop():
    monitor = EventLoopMonitor(interval=0.01, window=50)
    task = asyncio.create_task(monitor.run())
    try:
        await asyncio.sleep(0.1)  # a handful of 10ms ticks
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    snapshot = monitor.snapshot()
    assert snapshot["samples"] > 0
    # An idle loop should show near-zero lag — this is a sanity bound, not
    # a strict performance assertion (CI machines vary).
    assert snapshot["max_ms"] < 500

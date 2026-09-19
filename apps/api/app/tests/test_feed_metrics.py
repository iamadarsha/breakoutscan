"""Feed freshness tracking — exchange-tick age vs. transport-arrival age
must stay independently correct, and a missing/zero `ltt` must never
regress an already-known-good exchange-tick timestamp."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.market import feed_metrics


@pytest.fixture(autouse=True)
def _clear_feed_metrics_cache():
    feed_metrics.get_feed_metrics.cache_clear()
    yield
    feed_metrics.get_feed_metrics.cache_clear()


def test_snapshot_before_any_tick_is_all_none():
    metrics = feed_metrics.get_feed_metrics()
    snapshot = metrics.snapshot()
    assert snapshot == {
        "last_exchange_tick_age_ms": None,
        "last_received_age_ms": None,
        "reconnect_count": 0,
    }


def test_record_tick_computes_both_ages_independently():
    metrics = feed_metrics.get_feed_metrics()
    now = datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc)
    tick_received_at = now - timedelta(seconds=3)
    exchange_tick_ms = int((now - timedelta(seconds=20)).timestamp() * 1000)

    metrics.record_tick(exchange_tick_ms, tick_received_at)
    snapshot = metrics.snapshot(now=now)

    # Exchange went quiet 20s ago, but we only just (3s ago) received a
    # message — these must never be conflated into a single number.
    assert snapshot["last_exchange_tick_age_ms"] == pytest.approx(20_000, abs=5)
    assert snapshot["last_received_age_ms"] == pytest.approx(3_000, abs=5)


def test_record_tick_with_missing_ltt_does_not_regress_exchange_age():
    metrics = feed_metrics.get_feed_metrics()
    now = datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc)
    good_ltt = int((now - timedelta(seconds=5)).timestamp() * 1000)

    metrics.record_tick(good_ltt, now - timedelta(seconds=5))
    metrics.record_tick(0, now)  # degraded payload with no real ltt

    snapshot = metrics.snapshot(now=now)
    assert snapshot["last_exchange_tick_age_ms"] == pytest.approx(5_000, abs=5)
    # received_at still advances — the feed genuinely got a message just now.
    assert snapshot["last_received_age_ms"] == pytest.approx(0, abs=5)


def test_record_reconnect_increments_counter():
    metrics = feed_metrics.get_feed_metrics()
    metrics.record_reconnect()
    metrics.record_reconnect()
    assert metrics.snapshot()["reconnect_count"] == 2


def test_get_feed_metrics_is_a_process_wide_singleton():
    assert feed_metrics.get_feed_metrics() is feed_metrics.get_feed_metrics()

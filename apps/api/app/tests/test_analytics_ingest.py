"""Ingestion side of the analytics: validation, user-agent parsing, limits, buffering, the collector route."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.main import app
from app.services import analytics as svc

CHROME_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"
NOW = datetime(2026, 9, 21, 4, 0, tzinfo=timezone.utc)  # 09:30 IST


@pytest.fixture(autouse=True)
def _clean_state():
    svc.reset_state_for_tests()
    yield
    svc.reset_state_for_tests()


def _batch(**over):
    base = {"visitor_id": "v_aaaaaaaa", "session_id": "s_aaaaaaaa", "events": [{"name": "page_view", "path": "/dashboard"}]}
    base.update(over)
    return svc.BatchIn(**base)


CTX = svc.RequestContext(user_agent=CHROME_MAC, country="in", user_id=None)


# ------------------------------------------------------------------ validation


@pytest.mark.parametrize("name", ["PageView", "1click", "has space", "a" * 41, "drop;table", ""])
def test_bad_event_names_are_rejected(name):
    with pytest.raises(ValidationError):
        svc.EventIn(name=name)


def test_query_string_and_fragment_are_stripped_from_paths():
    ev = svc.EventIn(name="page_view", path="/chart/TCS?token=secret&x=1#top")
    assert ev.path == "/chart/TCS"


def test_props_are_limited_and_truncated():
    assert len(svc.EventIn(name="click", props={"label": "x" * 500}).props["label"]) == svc.MAX_PROP_STRING
    with pytest.raises(ValidationError):
        svc.EventIn(name="click", props={f"k{i}": 1 for i in range(svc.MAX_PROP_KEYS + 1)})
    with pytest.raises(ValidationError):
        svc.EventIn(name="click", props={"Bad-Key": 1})
    with pytest.raises(ValidationError):
        svc.EventIn(name="click", props={"nested": {"a": 1}})  # type: ignore[dict-item]


def test_batch_rules():
    with pytest.raises(ValidationError):
        _batch(visitor_id="short")
    with pytest.raises(ValidationError):
        _batch(events=[])
    with pytest.raises(ValidationError):
        _batch(events=[{"name": "page_view"}] * (svc.MAX_EVENTS_PER_BATCH + 1))
    with pytest.raises(ValidationError):
        _batch(unknown_field="x")


# ------------------------------------------------------------------ user agent


def test_user_agent_parsing():
    assert svc.parse_user_agent(CHROME_MAC) == ("desktop", "Chrome", "macOS", False)
    assert svc.parse_user_agent(IPHONE) == ("mobile", "Safari", "iOS", False)
    assert svc.parse_user_agent("Googlebot/2.1")[3] is True
    assert svc.parse_user_agent("HeadlessChrome/120")[3] is True
    assert svc.parse_user_agent(None)[3] is True  # no UA at all is treated as a bot


# ------------------------------------------------------------------ enqueue


def test_enqueue_records_enriched_rows_without_ip_or_raw_ua():
    n = svc.enqueue(_batch(referrer="https://google.com/", utm_source="x", viewport_w=1440), CTX, now=NOW)
    assert n == 1
    row = svc._buffer[0]
    assert row["ts"] == NOW and row["country"] == "IN"
    assert (row["device"], row["browser"], row["os"], row["is_bot"]) == ("desktop", "Chrome", "macOS", False)
    assert row["path"] == "/dashboard" and row["referrer"] == "https://google.com/" and row["viewport_w"] == 1440
    assert "ip" not in row and "user_agent" not in row and "ua" not in row


def test_disabled_flag_stops_collection(monkeypatch):
    monkeypatch.setattr(get_settings(), "analytics_enabled", False)
    assert svc.enqueue(_batch(), CTX, now=NOW) == 0 and not svc._buffer


def test_per_visitor_rate_limit(monkeypatch):
    monkeypatch.setattr(get_settings(), "analytics_visitor_rate_per_min", 3)
    events = [{"name": "click"}] * 5
    assert svc.enqueue(_batch(events=events), CTX, now=NOW) == 3
    assert svc.enqueue(_batch(events=events), CTX, now=NOW) == 0
    assert svc.stats()["dropped_rate"] == 7
    # a different visitor is unaffected
    assert svc.enqueue(_batch(visitor_id="v_bbbbbbbb", events=events), CTX, now=NOW) == 3


def test_daily_cap_protects_the_database(monkeypatch):
    monkeypatch.setattr(get_settings(), "analytics_max_events_per_day", 2)
    assert svc.enqueue(_batch(events=[{"name": "click"}] * 5), CTX, now=NOW) == 2
    assert svc.stats()["dropped_daily_cap"] == 3
    # the cap resets on the next IST day
    from datetime import timedelta

    assert svc.enqueue(_batch(visitor_id="v_cccccccc"), CTX, now=NOW + timedelta(days=1)) == 1


# ------------------------------------------------------------------ flushing


class _FakeSession:
    def __init__(self, fail: bool, sink: list):
        self.fail, self.sink = fail, sink

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt, params=None):
        if self.fail:
            raise RuntimeError("db down")
        self.sink.append((str(stmt)[:40], params))

    async def commit(self):
        pass


async def test_flush_writes_one_batch_and_upserts_users(monkeypatch):
    sink: list = []
    monkeypatch.setattr(svc, "SessionLocal", lambda: _FakeSession(False, sink))
    uid = "11111111-1111-1111-1111-111111111111"
    svc.enqueue(_batch(events=[{"name": "sign_in"}, {"name": "page_view"}]), svc.RequestContext(CHROME_MAC, "IN", uid), now=NOW)
    assert await svc.flush_once() == 2
    assert len(sink) == 2  # one bulk insert + one user upsert (not one statement per event)
    assert sink[1][1]["user_id"] == uid and sink[1][1]["n"] == 2
    assert svc.stats()["buffered"] == 0 and svc.stats()["flushed"] == 2


async def test_flush_failure_requeues_events_in_order(monkeypatch):
    monkeypatch.setattr(svc, "SessionLocal", lambda: _FakeSession(True, []))
    svc.enqueue(_batch(events=[{"name": "a_first"}, {"name": "b_second"}]), CTX, now=NOW)
    assert await svc.flush_once() == 0
    assert [r["event"] for r in svc._buffer] == ["a_first", "b_second"]
    assert svc.stats()["flush_errors"] == 1


async def test_bots_do_not_create_user_rows(monkeypatch):
    sink: list = []
    monkeypatch.setattr(svc, "SessionLocal", lambda: _FakeSession(False, sink))
    svc.enqueue(_batch(), svc.RequestContext("Googlebot/2.1", None, "22222222-2222-2222-2222-222222222222"), now=NOW)
    await svc.flush_once()
    assert len(sink) == 1  # events only, no analytics_users upsert


# ------------------------------------------------------------------ collector route


async def test_collect_route_accepts_and_queues():
    transport = httpx.ASGITransport(app=app)
    body = {"visitor_id": "v_routeaaa", "session_id": "s_routeaaa", "events": [{"name": "page_view", "path": "/screener?x=1"}]}
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post("/api/analytics/collect", json=body, headers={"user-agent": CHROME_MAC, "x-vercel-ip-country": "IN"})
    assert r.status_code == 202 and r.json() == {"accepted": 1}
    assert svc._buffer[0]["path"] == "/screener" and svc._buffer[0]["country"] == "IN"


async def test_collect_route_rejects_malformed_payloads():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post("/api/analytics/collect", json={"visitor_id": "x", "session_id": "y", "events": []})
    assert r.status_code == 422 and not svc._buffer

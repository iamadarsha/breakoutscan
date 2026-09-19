"""`/api/breakouts/*` route tests — monkeypatched `BreakoutStateStore` for
the in-memory active list, and a `dependency_overrides`-based fake DB
session (no route in this codebase has an established DB-override test
pattern yet — this is the first) for the confirmed-events history."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest

from app.api.deps import get_db
from app.breakouts.state_machine import BreakoutStateStore, DEFAULT_CONFIGS
from app.breakouts.types import Direction, RawEvent, TriggerType
from app.db.models.breakout_event import BreakoutEvent
from app.main import app


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)

    def all(self):
        return self._rows


class _FakeDbSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, stmt):
        return _FakeResult(self._rows)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_db, None)


def _seeded_store() -> BreakoutStateStore:
    store = BreakoutStateStore()
    tracker = store.get_or_create(
        "RELIANCE", TriggerType.ORB, Direction.BULLISH, DEFAULT_CONFIGS[TriggerType.ORB],
    )
    tracker.evaluate(RawEvent.CROSS_UP, Decimal("2500"), Decimal("2510"), datetime.now(timezone.utc), "bar1")
    return store


async def test_list_active_breakouts_returns_seeded_tracker(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.breakouts.get_breakout_state_store", _seeded_store,
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/breakouts/active")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "RELIANCE"
    assert body[0]["trigger_type"] == "orb"
    assert body[0]["status"] == "triggered"


async def test_list_active_breakouts_filters_by_trigger_type(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.breakouts.get_breakout_state_store", _seeded_store,
    )

    async def _override_get_db():
        yield _FakeDbSession([])

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/breakouts/active", params={"trigger_type": "pdh_pdl"})

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_active_breakouts_falls_back_to_last_session_when_store_empty(monkeypatch):
    """Market closed / fresh restart with no live signal yet — the endpoint
    must surface the last CONFIRMED breakout from the durable table instead
    of a misleading empty list."""
    monkeypatch.setattr(
        "app.api.routes.breakouts.get_breakout_state_store", lambda: BreakoutStateStore(),
    )

    event_row = BreakoutEvent(
        id=uuid.uuid4(),
        symbol="TCS",
        trigger_type="52w",
        direction="bullish",
        reference_level=Decimal("4000.0"),
        trigger_price=Decimal("4050.0"),
        confirmation_price=Decimal("4060.0"),
        score=Decimal("81.0"),
        extra={},
        triggered_at=datetime.now(timezone.utc),
        confirmed_at=datetime.now(timezone.utc),
    )

    async def _override_get_db():
        yield _FakeDbSession([(event_row, "Tata Consultancy Services")])

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/breakouts/active")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["symbol"] == "TCS"
    assert body[0]["company_name"] == "Tata Consultancy Services"
    assert body[0]["is_live"] is False
    assert body[0]["status"] == "CONFIRMED"
    assert body[0]["last_price"] == 4060.0


async def test_list_active_breakouts_stays_empty_when_store_and_db_both_empty(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.breakouts.get_breakout_state_store", lambda: BreakoutStateStore(),
    )

    async def _override_get_db():
        yield _FakeDbSession([])

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/breakouts/active")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_symbol_breakouts_combines_active_and_history(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.breakouts.get_breakout_state_store", _seeded_store,
    )

    event_row = BreakoutEvent(
        id=uuid.uuid4(),
        symbol="RELIANCE",
        trigger_type="pdh_pdl",
        direction="bullish",
        reference_level=Decimal("2500.0"),
        trigger_price=Decimal("2510.0"),
        confirmation_price=Decimal("2510.0"),
        score=Decimal("72.5"),
        extra={},
        triggered_at=datetime.now(timezone.utc),
        confirmed_at=datetime.now(timezone.utc),
    )

    async def _override_get_db():
        yield _FakeDbSession([event_row])

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/breakouts/RELIANCE")

    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "RELIANCE"
    assert len(body["active"]) == 1
    assert len(body["recent_events"]) == 1
    assert body["recent_events"][0]["trigger_type"] == "pdh_pdl"


async def test_get_symbol_breakouts_uppercases_symbol(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.breakouts.get_breakout_state_store", lambda: BreakoutStateStore(),
    )

    async def _override_get_db():
        yield _FakeDbSession([])

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/breakouts/reliance")

    assert resp.status_code == 200
    assert resp.json()["symbol"] == "RELIANCE"

"""The metric SQL, verified against a REAL Postgres with a scripted scenario.

Every expected number below is worked out by hand from the events in `_seed`, so a wrong join,
window or definition fails loudly. Runs only against a LOCAL database (it clears the analytics_*
tables first) and skips itself when none is reachable or the migration has not been applied.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

import app.db.session as db_session
from app.core.config import get_settings
from app.services import analytics as svc
from app.services import analytics_report as report

D0 = date(2026, 9, 21)  # "today" for the scenario (IST)
U1 = "aaaaaaaa-0000-0000-0000-000000000001"
CHROME = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
PHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"


def at(day_offset: int, hh: int, mm: int, ss: int = 0) -> datetime:
    """An IST wall-clock time on D0+offset, as an aware UTC datetime."""
    ist = svc.IST
    return datetime(D0.year, D0.month, D0.day, hh, mm, ss, tzinfo=ist).astimezone(timezone.utc) + timedelta(days=day_offset)


@pytest.fixture
async def db():
    url = get_settings().database_url
    if "localhost" not in url and "127.0.0.1" not in url:
        pytest.skip("analytics DB tests only run against a local database")
    db_session._engine = None
    db_session._session_factory = None
    svc.reset_state_for_tests()
    try:
        async with db_session.SessionLocal() as s:
            await s.execute(text("DELETE FROM analytics_events"))
            await s.execute(text("DELETE FROM analytics_users"))
            await s.execute(text("DELETE FROM analytics_daily"))
            await s.commit()
    except Exception as exc:  # no server, or migration 0006 not applied
        pytest.skip(f"local analytics tables unavailable: {exc}")
    yield
    async with db_session.SessionLocal() as s:
        await s.execute(text("DELETE FROM analytics_events"))
        await s.execute(text("DELETE FROM analytics_users"))
        await s.execute(text("DELETE FROM analytics_daily"))
        await s.commit()
    await db_session._engine.dispose()
    db_session._engine = None
    db_session._session_factory = None
    svc.reset_state_for_tests()


def _send(visitor, session, when, events, ua=CHROME, user=None, country="IN", **batch):
    body = svc.BatchIn(visitor_id=visitor, session_id=session, events=events, **batch)
    assert svc.enqueue(body, svc.RequestContext(ua, country, user), now=when) == len(events)


def _ev(name, path=None, **props):
    return {"name": name, "path": path, "props": props}


async def _seed():
    # Day D-2 (2026-09-19)
    _send("v_visitorA", "s_session01", at(-2, 10, 0), [_ev("page_view", "/dashboard")], referrer="https://www.google.com/x")
    _send("v_visitorA", "s_session01", at(-2, 10, 0, 40), [_ev("click", "/dashboard", label="Run")])
    _send("v_visitorA", "s_session01", at(-2, 10, 1), [_ev("scan_run", "/dashboard", scan_id="volume_spike", results=112)])
    _send("v_visitorA", "s_session01", at(-2, 10, 2), [_ev("page_leave", "/dashboard", seconds=120)])
    _send("v_visitorD", "s_session04", at(-2, 11, 0), [_ev("page_view", "/ai-picks")], ua=PHONE)
    # Day D-1 (2026-09-20): A comes back and bounces
    _send("v_visitorA", "s_session02", at(-1, 9, 30), [_ev("page_view", "/screener")])
    _send("v_visitorA", "s_session02", at(-1, 9, 30, 5), [_ev("page_leave", "/screener", seconds=5)])
    # Day D0 (2026-09-21): B signs in; D returns and bounces; a bot is ignored
    _send("v_visitorB", "s_session03", at(0, 9, 20), [_ev("page_view", "/dashboard")], user=U1)
    _send("v_visitorB", "s_session03", at(0, 9, 21), [_ev("click", "/dashboard", label="Add Stock")], user=U1)
    _send("v_visitorB", "s_session03", at(0, 9, 22), [_ev("sign_in", "/login")], user=U1)
    _send("v_visitorB", "s_session03", at(0, 9, 25), [_ev("page_view", "/watchlist")], user=U1)
    _send("v_visitorD", "s_session05", at(0, 12, 0), [_ev("page_view", "/dashboard")], ua=PHONE)
    _send("v_visitorC", "s_session06", at(0, 12, 30), [_ev("page_view", "/dashboard")], ua="Googlebot/2.1")
    while svc._buffer:
        assert await svc.flush_once() > 0


async def test_daily_figures_match_hand_computed_values(db):
    await _seed()
    async with db_session.SessionLocal() as s:
        d2 = await svc.compute_day(s, D0 - timedelta(days=2))
        d1 = await svc.compute_day(s, D0 - timedelta(days=1))
        d0 = await svc.compute_day(s, D0)

    assert (d2["visitors"], d2["new_visitors"], d2["returning_visitors"], d2["sessions"]) == (2, 2, 0, 2)
    assert (d2["pageviews"], d2["clicks"], d2["events"], d2["scans_run"]) == (2, 1, 5, 1)
    assert (d2["bounced_sessions"], d2["avg_session_seconds"]) == (1, 60.0)  # (120s + 0s) / 2

    assert (d1["visitors"], d1["new_visitors"], d1["returning_visitors"], d1["sessions"]) == (1, 0, 1, 1)
    assert (d1["pageviews"], d1["events"], d1["bounced_sessions"], d1["avg_session_seconds"]) == (1, 2, 1, 5.0)

    assert (d0["visitors"], d0["new_visitors"], d0["returning_visitors"], d0["sessions"]) == (2, 1, 1, 2)
    assert (d0["pageviews"], d0["clicks"], d0["events"]) == (3, 1, 5)  # the bot's event is excluded
    assert (d0["signed_in_users"], d0["new_users"], d0["bounced_sessions"]) == (1, 1, 1)
    assert d0["avg_session_seconds"] == 150.0  # (300s + 0s) / 2


async def test_summary_windows_lists_retention_and_quality(db):
    await _seed()
    now = at(0, 15, 0)
    async with db_session.SessionLocal() as s:
        await svc.rollup_days(days_back=2, today=D0)
        out = await report.summary(s, days=30, now=now)

    w7 = out["windows"]["last_7_days"]
    assert (w7["visitors"], w7["sessions"], w7["pageviews"], w7["clicks"]) == (3, 5, 6, 2)
    assert w7["bounce_rate"] == 0.6 and w7["pages_per_session"] == 1.2

    assert out["top_pages"][0] == {"path": "/dashboard", "pageviews": 3, "visitors": 3}
    assert {(c["label"], c["clicks"]) for c in out["top_clicks"]} == {("Run", 1), ("Add Stock", 1)}
    assert {f["event"] for f in out["features"]} == {"scan_run", "sign_in"}
    assert out["scan_runs"] == [{"scan": "volume_spike", "runs": 1}]
    assert out["referrers"][0]["source"] in {"(direct)", "www.google.com"}
    assert {d["name"]: d["visitors"] for d in out["devices"]} == {"desktop": 2, "mobile": 1}
    assert out["users"]["registered_total"] == 1 and out["users"]["new_today"] == 1
    assert out["retention"]["day_1_cohort"] == 2 and out["retention"]["day_1"] == 0.5  # A returned next day, D did not
    assert out["retention"]["day_7"] is None  # nobody is old enough yet
    assert out["data_quality"]["bot_events_excluded_in_range"] == 1
    assert [d["day"] for d in out["daily"]][-3:] == ["2026-09-19", "2026-09-20", "2026-09-21"]
    assert out["all_time"]["tracking_since"] == "2026-09-19"
    hours = {h["hour_ist"]: h["pageviews"] for h in out["pageviews_by_hour_ist"]}
    assert hours[10] == 1 and hours[9] == 3 and hours[12] == 1  # bucketed in IST, bot excluded


async def test_exports_are_valid_csv_that_reconcile_with_the_raw_log(db):
    await _seed()
    async with db_session.SessionLocal() as s:
        await svc.rollup_days(days_back=2, today=D0)
        daily = list(csv.DictReader(io.StringIO(await report.daily_csv(s, now=at(0, 15, 0)))))
        users = list(csv.DictReader(io.StringIO(await report.users_csv(s))))
        events = list(csv.DictReader(io.StringIO(await report.events_csv(s, D0 - timedelta(days=2), D0))))
        stored_events = (await s.execute(text("SELECT COUNT(*) FROM analytics_events"))).scalar_one()

    assert [r["day"] for r in daily] == ["2026-09-19", "2026-09-20", "2026-09-21"]
    assert [r["pageviews"] for r in daily] == ["2", "1", "3"]
    assert users == [{"user_id": U1, "first_seen_utc": users[0]["first_seen_utc"], "last_seen_utc": users[0]["last_seen_utc"], "event_count": "4"}]
    # the raw export contains every stored event (including the flagged bot), so totals can be audited
    assert len(events) == stored_events == 13
    assert sum(1 for e in events if e["is_bot"] == "True") == 1
    assert "email" not in events[0] and "ip" not in events[0]


async def test_rollup_is_idempotent(db):
    await _seed()
    await svc.rollup_days(days_back=2, today=D0)
    await svc.rollup_days(days_back=2, today=D0)
    async with db_session.SessionLocal() as s:
        n = (await s.execute(text("SELECT COUNT(*) FROM analytics_daily"))).scalar_one()
    assert n == 3


async def test_pm_report_matches_hand_computed_values(db):
    """DAU/WAU, funnel, retention and channels, worked out by hand from `_seed`."""
    await _seed()
    async with db_session.SessionLocal() as s:
        raw = await report.pm_report_csv(s, now=at(0, 15, 0))
    rows = {(r["section"], r["metric"]): r for r in csv.DictReader(io.StringIO(raw))}

    def v(section: str, metric: str, col: str = "value") -> str:
        return rows[(section, metric)][col]

    assert v("growth", "Active visitors today (DAU, so far)") == "2"  # B and D
    assert v("growth", "Active visitors today (DAU, so far)", "compare") == "1"  # A yesterday
    assert v("growth", "Weekly active visitors (WAU)") == "3"  # A, B, D; the bot is excluded
    assert v("growth", "Monthly active visitors (MAU, 30d)") == "3"
    assert v("activation_funnel", "1. Visited") == "3"
    assert v("activation_funnel", "2. Opened the screener") == "1"  # A on D-1
    assert v("activation_funnel", "3. Ran a scan") == "1"
    assert v("activation_funnel", "6. Signed in") == "1"
    assert v("activation_funnel", "7. Created a price alert") == "0"
    assert v("retention", "Day-1 retention") == "0.5"  # cohort A, D; only A returned exactly next day
    assert v("acquisition_channels", "Search") == "1"  # the google-referred session
    assert v("acquisition_channels", "Direct") == "4"
    assert ("definitions", "Visitor") in rows

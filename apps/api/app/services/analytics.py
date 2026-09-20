"""First-party usage analytics: ingestion, validation, buffered writes, daily rollups.

Design goals
- Auditable: every metric is derivable from the append-only `analytics_events` table.
- Cheap: events are validated, queued in memory and written in one batch every few
  seconds, so tracking can never starve the (small) database connection pool.
- Private: no IP address and no raw user-agent are stored; users are opaque ids, never emails.
- Bounded: per-visitor rate limit, buffer cap and a daily row cap protect the free-tier database.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import insert, text

from app.core.config import get_settings
from app.db.models.analytics_event import AnalyticsEvent
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

MAX_BUFFER = 20_000
FLUSH_INTERVAL_SECONDS = 5
FLUSH_BATCH = 2_000
ROLLUP_INTERVAL_SECONDS = 30 * 60
MAX_PROP_KEYS = 20
MAX_PROP_STRING = 200
MAX_EVENTS_PER_BATCH = 50

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,40}$")
_PROP_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,29}$")

PropValue = str | int | float | bool | None


# --------------------------------------------------------------------------- input models


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ts: int | None = None  # client clock, epoch milliseconds (reference only)
    path: str | None = Field(default=None, max_length=300)
    props: dict[str, PropValue] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError("event name must be snake_case, max 40 chars")
        return v

    @field_validator("path")
    @classmethod
    def _path(cls, v: str | None) -> str | None:
        if v is None:
            return None
        # Paths only: never store query strings or fragments (they can carry tokens).
        return v.split("?", 1)[0].split("#", 1)[0][:300] or None

    @field_validator("props")
    @classmethod
    def _props(cls, v: dict[str, PropValue]) -> dict[str, PropValue]:
        if len(v) > MAX_PROP_KEYS:
            raise ValueError("too many props")
        clean: dict[str, PropValue] = {}
        for key, val in v.items():
            if not _PROP_KEY_RE.match(key):
                raise ValueError(f"bad prop key: {key!r}")
            clean[key] = val[:MAX_PROP_STRING] if isinstance(val, str) else val
        return clean


class BatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visitor_id: str
    session_id: str
    events: list[EventIn] = Field(min_length=1, max_length=MAX_EVENTS_PER_BATCH)
    referrer: str | None = Field(default=None, max_length=300)
    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=100)
    viewport_w: int | None = Field(default=None, ge=0, le=20_000)
    app_version: str | None = Field(default=None, max_length=40)

    @field_validator("visitor_id", "session_id")
    @classmethod
    def _ids(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("bad id")
        return v


# --------------------------------------------------------------------------- user-agent


_BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|headless|lighthouse|pingdom|uptime|monitor|curl|wget|python-requests|httpx|axios|facebookexternalhit|preview",
    re.I,
)


def parse_user_agent(ua: str | None) -> tuple[str, str, str, bool]:
    """Return (device, browser, os, is_bot) from a UA string. The raw UA is never stored."""
    ua = ua or ""
    is_bot = bool(_BOT_RE.search(ua)) or not ua
    if re.search(r"ipad|tablet", ua, re.I):
        device = "tablet"
    elif re.search(r"mobi|iphone|android.+mobile", ua, re.I):
        device = "mobile"
    elif re.search(r"android", ua, re.I):
        device = "tablet"
    else:
        device = "desktop"
    if re.search(r"edg/", ua, re.I):
        browser = "Edge"
    elif re.search(r"opr/|opera", ua, re.I):
        browser = "Opera"
    elif re.search(r"samsungbrowser", ua, re.I):
        browser = "Samsung"
    elif re.search(r"firefox|fxios", ua, re.I):
        browser = "Firefox"
    elif re.search(r"chrome|crios", ua, re.I):
        browser = "Chrome"
    elif re.search(r"safari", ua, re.I):
        browser = "Safari"
    else:
        browser = "Other"
    if re.search(r"windows", ua, re.I):
        os_name = "Windows"
    elif re.search(r"iphone|ipad|ipod|ios", ua, re.I):
        os_name = "iOS"
    elif re.search(r"android", ua, re.I):
        os_name = "Android"
    elif re.search(r"mac os|macintosh", ua, re.I):
        os_name = "macOS"
    elif re.search(r"linux|x11", ua, re.I):
        os_name = "Linux"
    else:
        os_name = "Other"
    return device, browser, os_name, is_bot


# --------------------------------------------------------------------------- in-memory buffer

_buffer: deque[dict[str, Any]] = deque()
_visitor_windows: dict[str, tuple[float, int]] = {}
_day_key: date | None = None
_day_count = 0
_stats = {"accepted": 0, "dropped_buffer": 0, "dropped_rate": 0, "dropped_daily_cap": 0, "flushed": 0, "flush_errors": 0}


def stats() -> dict[str, int]:
    return {**_stats, "buffered": len(_buffer), "events_today_ist": _day_count}


def reset_state_for_tests() -> None:
    global _day_key, _day_count
    _buffer.clear()
    _visitor_windows.clear()
    _day_key, _day_count = None, 0
    for k in _stats:
        _stats[k] = 0


@dataclass(frozen=True)
class RequestContext:
    user_agent: str | None
    country: str | None
    user_id: str | None


def _country(value: str | None) -> str | None:
    if value and re.fullmatch(r"[A-Za-z]{2}", value):
        return value.upper()
    return None


def _client_ts(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def enqueue(batch: BatchIn, ctx: RequestContext, now: datetime | None = None) -> int:
    """Validate-and-queue a batch. Returns how many events were accepted."""
    global _day_key, _day_count
    settings = get_settings()
    if not settings.analytics_enabled:
        return 0
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(IST).date()
    if _day_key != today:
        _day_key, _day_count = today, 0

    # Per-visitor rate limit (events per minute): stops one client flooding the table.
    mono = time.monotonic()
    start, count = _visitor_windows.get(batch.visitor_id, (mono, 0))
    if mono - start >= 60:
        start, count = mono, 0
    room = max(0, settings.analytics_visitor_rate_per_min - count)
    events = batch.events[:room]
    _stats["dropped_rate"] += len(batch.events) - len(events)
    _visitor_windows[batch.visitor_id] = (start, count + len(events))
    if len(_visitor_windows) > 10_000:  # bound memory
        _visitor_windows.clear()

    device, browser, os_name, is_bot = parse_user_agent(ctx.user_agent)
    accepted = 0
    for ev in events:
        if _day_count >= settings.analytics_max_events_per_day:
            _stats["dropped_daily_cap"] += 1
            continue
        if len(_buffer) >= MAX_BUFFER:
            _stats["dropped_buffer"] += 1
            continue
        _buffer.append(
            {
                "ts": now,
                "client_ts": _client_ts(ev.ts),
                "visitor_id": batch.visitor_id,
                "session_id": batch.session_id,
                "user_id": ctx.user_id,
                "event": ev.name,
                "path": ev.path,
                "props": ev.props,
                "referrer": batch.referrer,
                "utm_source": batch.utm_source,
                "utm_medium": batch.utm_medium,
                "utm_campaign": batch.utm_campaign,
                "device": device,
                "browser": browser,
                "os": os_name,
                "country": _country(ctx.country),
                "viewport_w": batch.viewport_w,
                "is_bot": is_bot,
                "app_version": batch.app_version,
            }
        )
        _day_count += 1
        accepted += 1
    _stats["accepted"] += accepted
    return accepted


# --------------------------------------------------------------------------- flushing

_UPSERT_USERS = text(
    """
    INSERT INTO analytics_users (user_id, first_seen, last_seen, event_count)
    VALUES (:user_id, :first_seen, :last_seen, :n)
    ON CONFLICT (user_id) DO UPDATE SET
        last_seen = GREATEST(analytics_users.last_seen, EXCLUDED.last_seen),
        first_seen = LEAST(analytics_users.first_seen, EXCLUDED.first_seen),
        event_count = analytics_users.event_count + EXCLUDED.event_count
    """
)


async def flush_once() -> int:
    """Write up to FLUSH_BATCH buffered events in one transaction. Returns rows written."""
    if not _buffer:
        return 0
    rows: list[dict[str, Any]] = []
    while _buffer and len(rows) < FLUSH_BATCH:
        rows.append(_buffer.popleft())
    users: dict[str, dict[str, Any]] = {}
    for r in rows:
        uid = r["user_id"]
        if uid and not r["is_bot"]:
            u = users.setdefault(uid, {"user_id": uid, "first_seen": r["ts"], "last_seen": r["ts"], "n": 0})
            u["first_seen"] = min(u["first_seen"], r["ts"])
            u["last_seen"] = max(u["last_seen"], r["ts"])
            u["n"] += 1
    try:
        async with SessionLocal() as session:
            await session.execute(insert(AnalyticsEvent), rows)
            for u in users.values():
                await session.execute(_UPSERT_USERS, u)
            await session.commit()
    except Exception:
        _stats["flush_errors"] += 1
        logger.exception("analytics flush failed; re-queueing %d events", len(rows))
        for r in reversed(rows):  # keep original order at the front of the queue
            if len(_buffer) < MAX_BUFFER:
                _buffer.appendleft(r)
            else:
                _stats["dropped_buffer"] += 1
        return 0
    _stats["flushed"] += len(rows)
    return len(rows)


async def flush_all() -> int:
    total = 0
    while _buffer:
        written = await flush_once()
        if written == 0:
            break
        total += written
    return total


async def analytics_flush_loop() -> None:
    while True:
        try:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
            await flush_once()
        except asyncio.CancelledError:
            await flush_all()  # don't lose buffered events on shutdown
            raise
        except Exception:
            logger.exception("analytics flush loop error")


# --------------------------------------------------------------------------- daily rollup

_ROLLUP_SQL = text(
    """
    WITH ev AS (
        SELECT * FROM analytics_events
        WHERE ts >= :d0 AND ts < :d1 AND NOT is_bot
    ),
    sess AS (
        SELECT session_id, MIN(ts) AS s0, MAX(ts) AS s1,
               COUNT(*) FILTER (WHERE event = 'page_view') AS pvs,
               COUNT(*) FILTER (WHERE event NOT IN ('page_view','page_leave','web_vital','js_error')) AS interactions
        FROM ev GROUP BY session_id
    ),
    prior AS (
        SELECT DISTINCT visitor_id FROM analytics_events
        WHERE ts < :d0 AND NOT is_bot AND visitor_id IN (SELECT visitor_id FROM ev)
    )
    SELECT
      (SELECT COUNT(DISTINCT visitor_id) FROM ev)                                       AS visitors,
      (SELECT COUNT(DISTINCT visitor_id) FROM ev
         WHERE visitor_id NOT IN (SELECT visitor_id FROM prior))                        AS new_visitors,
      (SELECT COUNT(*) FROM prior)                                                      AS returning_visitors,
      (SELECT COUNT(*) FROM sess)                                                       AS sessions,
      (SELECT COUNT(*) FROM ev WHERE event = 'page_view')                               AS pageviews,
      (SELECT COUNT(*) FROM ev WHERE event = 'click')                                   AS clicks,
      (SELECT COUNT(*) FROM ev)                                                         AS events,
      (SELECT COUNT(DISTINCT user_id) FROM ev WHERE user_id IS NOT NULL)                AS signed_in_users,
      (SELECT COUNT(*) FROM analytics_users WHERE first_seen >= :d0 AND first_seen < :d1) AS new_users,
      (SELECT COUNT(*) FROM sess WHERE pvs = 1 AND interactions = 0)                    AS bounced_sessions,
      COALESCE((SELECT ROUND(AVG(EXTRACT(EPOCH FROM (s1 - s0)))::numeric, 1) FROM sess WHERE pvs >= 1), 0) AS avg_session_seconds,
      (SELECT COUNT(*) FROM ev WHERE event = 'scan_run')                                AS scans_run,
      (SELECT COUNT(*) FROM ev WHERE event = 'js_error')                                AS errors
    """
)

_UPSERT_DAILY = text(
    """
    INSERT INTO analytics_daily (day, visitors, new_visitors, returning_visitors, sessions, pageviews, clicks,
        events, signed_in_users, new_users, bounced_sessions, avg_session_seconds, scans_run, errors, computed_at)
    VALUES (:day, :visitors, :new_visitors, :returning_visitors, :sessions, :pageviews, :clicks,
        :events, :signed_in_users, :new_users, :bounced_sessions, :avg_session_seconds, :scans_run, :errors, now())
    ON CONFLICT (day) DO UPDATE SET
        visitors = EXCLUDED.visitors, new_visitors = EXCLUDED.new_visitors,
        returning_visitors = EXCLUDED.returning_visitors, sessions = EXCLUDED.sessions,
        pageviews = EXCLUDED.pageviews, clicks = EXCLUDED.clicks, events = EXCLUDED.events,
        signed_in_users = EXCLUDED.signed_in_users, new_users = EXCLUDED.new_users,
        bounced_sessions = EXCLUDED.bounced_sessions, avg_session_seconds = EXCLUDED.avg_session_seconds,
        scans_run = EXCLUDED.scans_run, errors = EXCLUDED.errors, computed_at = now()
    """
)


def ist_day_bounds(day: date) -> tuple[datetime, datetime]:
    """UTC bounds of an IST calendar day. All daily figures are IST days."""
    start = datetime(day.year, day.month, day.day, tzinfo=IST)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


async def compute_range(session: Any, d0: datetime, d1: datetime) -> dict[str, Any]:
    """Headline figures for any [d0, d1) window (bots excluded)."""
    row = (await session.execute(_ROLLUP_SQL, {"d0": d0, "d1": d1})).mappings().one()
    return {k: (float(v) if k == "avg_session_seconds" else int(v)) for k, v in row.items()}


async def compute_day(session: Any, day: date) -> dict[str, Any]:
    d0, d1 = ist_day_bounds(day)
    return {"day": day, **await compute_range(session, d0, d1)}


async def rollup_days(days_back: int = 2, today: date | None = None) -> list[date]:
    """Recompute today and the previous `days_back` IST days into analytics_daily."""
    today = today or datetime.now(timezone.utc).astimezone(IST).date()
    done: list[date] = []
    async with SessionLocal() as session:
        for offset in range(days_back, -1, -1):
            day = today - timedelta(days=offset)
            await session.execute(_UPSERT_DAILY, await compute_day(session, day))
            done.append(day)
        await session.commit()
    return done


async def analytics_rollup_loop() -> None:
    await asyncio.sleep(60)
    while True:
        try:
            await rollup_days()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("analytics rollup failed")
        await asyncio.sleep(ROLLUP_INTERVAL_SECONDS)

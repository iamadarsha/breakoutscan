"""Read side of the analytics: the metrics summary and CSV exports.

Every figure is computed by SQL over `analytics_events` (raw, auditable) or read from the permanent
`analytics_daily` rollup. Bots are excluded from all metrics and reported separately.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.services import analytics as svc

IST = svc.IST

_GENERIC_EVENTS = "('page_view','page_leave','click','web_vital','js_error')"


def _ratio(num: float, den: float) -> float | None:
    return round(num / den, 4) if den else None


def _window_view(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "visitors": raw["visitors"],
        "new_visitors": raw["new_visitors"],
        "returning_visitors": raw["returning_visitors"],
        "sessions": raw["sessions"],
        "pageviews": raw["pageviews"],
        "clicks": raw["clicks"],
        "events": raw["events"],
        "signed_in_users": raw["signed_in_users"],
        "new_users": raw["new_users"],
        "avg_session_seconds": raw["avg_session_seconds"],
        "bounce_rate": _ratio(raw["bounced_sessions"], raw["sessions"]),
        "pages_per_session": _ratio(raw["pageviews"], raw["sessions"]),
        "scans_run": raw["scans_run"],
        "errors": raw["errors"],
    }


async def _rows(session: Any, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(r) for r in (await session.execute(text(sql), params)).mappings().all()]


async def summary(session: Any, days: int = 30, now: datetime | None = None) -> dict[str, Any]:
    days = max(1, min(days, 90))
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(IST).date()
    t0, t1 = svc.ist_day_bounds(today)
    w7 = svc.ist_day_bounds(today - timedelta(days=6))[0]
    wN = svc.ist_day_bounds(today - timedelta(days=days - 1))[0]
    p = {"a": wN, "b": t1}

    windows = {
        "today": _window_view(await svc.compute_range(session, t0, t1)),
        "last_7_days": _window_view(await svc.compute_range(session, w7, t1)),
        f"last_{days}_days": _window_view(await svc.compute_range(session, wN, t1)),
    }

    base = "FROM analytics_events WHERE ts >= :a AND ts < :b AND NOT is_bot"
    top_pages = await _rows(session, f"""
        SELECT COALESCE(path,'(none)') AS path, COUNT(*) AS pageviews, COUNT(DISTINCT visitor_id) AS visitors
        {base} AND event='page_view' GROUP BY 1 ORDER BY 2 DESC LIMIT 15""", p)
    top_clicks = await _rows(session, f"""
        SELECT COALESCE(props->>'label','(unlabelled)') AS label, COALESCE(path,'(none)') AS path, COUNT(*) AS clicks
        {base} AND event='click' GROUP BY 1,2 ORDER BY 3 DESC LIMIT 25""", p)
    features = await _rows(session, f"""
        SELECT event, COUNT(*) AS uses, COUNT(DISTINCT visitor_id) AS visitors
        {base} AND event NOT IN {_GENERIC_EVENTS} GROUP BY 1 ORDER BY 2 DESC LIMIT 25""", p)
    scan_runs = await _rows(session, f"""
        SELECT COALESCE(props->>'scan_id','custom') AS scan, COUNT(*) AS runs
        {base} AND event='scan_run' GROUP BY 1 ORDER BY 2 DESC LIMIT 15""", p)
    referrers = await _rows(session, f"""
        SELECT COALESCE(NULLIF(regexp_replace(referrer,'^https?://([^/]+).*$','\\1'),''),'(direct)') AS source,
               COUNT(DISTINCT session_id) AS sessions
        {base} AND event='page_view' GROUP BY 1 ORDER BY 2 DESC LIMIT 15""", p)
    utm = await _rows(session, f"""
        SELECT utm_source, COALESCE(utm_medium,'') AS utm_medium, COALESCE(utm_campaign,'') AS utm_campaign,
               COUNT(DISTINCT session_id) AS sessions
        {base} AND utm_source IS NOT NULL GROUP BY 1,2,3 ORDER BY 4 DESC LIMIT 15""", p)

    def dim(col: str) -> str:
        return f"""SELECT COALESCE({col},'(unknown)') AS name, COUNT(DISTINCT visitor_id) AS visitors
                   {base} GROUP BY 1 ORDER BY 2 DESC LIMIT 12"""

    countries, devices, browsers, systems = (
        await _rows(session, dim("country"), p),
        await _rows(session, dim("device"), p),
        await _rows(session, dim("browser"), p),
        await _rows(session, dim("os"), p),
    )
    hours = await _rows(session, f"""
        SELECT EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Kolkata')::int AS hour_ist, COUNT(*) AS pageviews
        {base} AND event='page_view' GROUP BY 1 ORDER BY 1""", p)
    errors = await _rows(session, f"""
        SELECT COALESCE(props->>'message','(no message)') AS message, COALESCE(path,'(none)') AS path, COUNT(*) AS count
        {base} AND event='js_error' GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10""", p)
    vitals = await _rows(session, f"""
        SELECT props->>'name' AS metric, COUNT(*) AS samples,
               ROUND(percentile_cont(0.75) WITHIN GROUP (ORDER BY (props->>'value')::float)::numeric, 1) AS p75
        {base} AND event='web_vital' AND (props->>'value') ~ '^-?[0-9.]+$' GROUP BY 1 ORDER BY 1""", p)

    retention_row = (await session.execute(text("""
        WITH first AS (
            SELECT visitor_id, MIN((ts AT TIME ZONE 'Asia/Kolkata')::date) AS d0
            FROM analytics_events WHERE NOT is_bot GROUP BY visitor_id),
        act AS (SELECT DISTINCT visitor_id, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d
                FROM analytics_events WHERE NOT is_bot)
        SELECT
          COUNT(*) FILTER (WHERE first.d0 <= CAST(:today AS date) - 1) AS cohort_d1,
          COUNT(*) FILTER (WHERE first.d0 <= CAST(:today AS date) - 1 AND EXISTS
              (SELECT 1 FROM act WHERE act.visitor_id = first.visitor_id AND act.d = first.d0 + 1)) AS back_d1,
          COUNT(*) FILTER (WHERE first.d0 <= CAST(:today AS date) - 7) AS cohort_d7,
          COUNT(*) FILTER (WHERE first.d0 <= CAST(:today AS date) - 7 AND EXISTS
              (SELECT 1 FROM act WHERE act.visitor_id = first.visitor_id AND act.d BETWEEN first.d0 + 1 AND first.d0 + 7)) AS back_d7
        FROM first"""), {"today": today})).mappings().one()

    daily_rows = await _rows(session, "SELECT * FROM analytics_daily WHERE day >= :d ORDER BY day",
                             {"d": today - timedelta(days=days - 1)})
    daily = [{**r, "day": r["day"].isoformat(), "avg_session_seconds": float(r["avg_session_seconds"]),
              "computed_at": r["computed_at"].isoformat()} for r in daily_rows if r["day"] != today]
    daily.append({"day": today.isoformat(), **{k: v for k, v in windows["today"].items()}, "live": True})

    user_row = (await session.execute(text("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE first_seen >= :t0) AS new_today,
               COUNT(*) FILTER (WHERE first_seen >= :w7) AS new_7d,
               COUNT(*) FILTER (WHERE last_seen >= :w7) AS active_7d,
               MIN(first_seen) AS first_signup FROM analytics_users"""), {"t0": t0, "w7": w7})).mappings().one()
    alltime = (await session.execute(text("""
        SELECT COALESCE(SUM(pageviews),0) AS pageviews, COALESCE(SUM(sessions),0) AS sessions,
               COALESCE(SUM(clicks),0) AS clicks, COALESCE(SUM(events),0) AS events, MIN(day) AS since
        FROM analytics_daily"""))).mappings().one()
    bots = (await session.execute(text(
        "SELECT COUNT(*) FROM analytics_events WHERE ts >= :a AND ts < :b AND is_bot"), p)).scalar_one()
    raw_rows = (await session.execute(text("SELECT COUNT(*) FROM analytics_events"))).scalar_one()

    settings = get_settings()
    return {
        "generated_at": now.isoformat(),
        "timezone": "Asia/Kolkata (all days are IST calendar days)",
        "range_days": days,
        "windows": windows,
        "users": {
            "registered_total": user_row["total"], "new_today": user_row["new_today"],
            "new_last_7_days": user_row["new_7d"], "active_last_7_days": user_row["active_7d"],
            "first_signup_seen": user_row["first_signup"].isoformat() if user_row["first_signup"] else None,
        },
        "all_time": {
            "pageviews": int(alltime["pageviews"]), "sessions": int(alltime["sessions"]),
            "clicks": int(alltime["clicks"]), "events": int(alltime["events"]),
            "tracking_since": alltime["since"].isoformat() if alltime["since"] else None,
        },
        "retention": {
            "day_1": _ratio(retention_row["back_d1"], retention_row["cohort_d1"]), "day_1_cohort": retention_row["cohort_d1"],
            "day_7": _ratio(retention_row["back_d7"], retention_row["cohort_d7"]), "day_7_cohort": retention_row["cohort_d7"],
        },
        "daily": daily,
        "top_pages": top_pages, "top_clicks": top_clicks, "features": features, "scan_runs": scan_runs,
        "referrers": referrers, "utm": utm, "countries": countries, "devices": devices,
        "browsers": browsers, "operating_systems": systems, "pageviews_by_hour_ist": hours,
        "errors": errors, "web_vitals_p75": vitals,
        "data_quality": {
            "bot_events_excluded_in_range": bots,
            "raw_rows_stored": raw_rows,
            "raw_retention_days": settings.analytics_raw_keep_days,
            "daily_event_cap": settings.analytics_max_events_per_day,
            "ingest": svc.stats(),
            "notes": [
                "Unique visitors are anonymous browser ids; one person on two browsers counts twice.",
                "Visitors who clear browser storage count as new visitors.",
                "Do Not Track / Global Privacy Control and opted-out browsers are not counted.",
                "New vs returning visitors look back only as far as raw retention.",
            ],
        },
    }


# --------------------------------------------------------------------------- CSV exports


def _csv(headers: list[str], rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue()


async def daily_csv(session: Any, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(IST).date()
    stored = {r["day"]: r for r in await _rows(session, "SELECT * FROM analytics_daily ORDER BY day", {})}
    live = await svc.compute_day(session, today)
    stored[today] = live
    cols = ["day", "visitors", "new_visitors", "returning_visitors", "sessions", "pageviews", "clicks", "events",
            "signed_in_users", "new_users", "bounced_sessions", "avg_session_seconds", "scans_run", "errors"]
    return _csv(cols, [[(d.isoformat() if c == "day" else stored[d][c]) for c in cols] for d in sorted(stored)])


async def summary_csv(session: Any, days: int = 30, now: datetime | None = None) -> str:
    """Every headline metric as `section,name,metric,value` rows: one sheet tab a PM can read as is."""
    d = await summary(session, days=days, now=now)
    rows: list[list[Any]] = []
    for window, vals in d["windows"].items():
        rows += [["overview", window, k, v] for k, v in vals.items()]
    for k, v in {**d["users"], **{f"all_time_{a}": b for a, b in d["all_time"].items()}, **d["retention"]}.items():
        rows.append(["users_and_retention", "", k, v])
    for section in ("top_pages", "top_clicks", "features", "scan_runs", "referrers", "utm", "countries",
                    "devices", "browsers", "operating_systems", "pageviews_by_hour_ist", "errors", "web_vitals_p75"):
        for r in d[section]:
            vals = list(r.values())
            rows.append([section, vals[0], "|".join(str(k) for k in list(r)[1:]), "|".join(str(v) for v in vals[1:])])
    rows.append(["data_quality", "", "bot_events_excluded", d["data_quality"]["bot_events_excluded_in_range"]])
    rows.append(["data_quality", "", "raw_rows_stored", d["data_quality"]["raw_rows_stored"]])
    return _csv(["section", "name", "metric", "value"], rows)


# --------------------------------------------------------------------------- PM report

_FEATURES = [
    ("Ran a scan", "scan_run"), ("Added a stock to watchlist", "watchlist_add"),
    ("Created a price alert", "alert_create"), ("Refreshed AI picks", "ai_picks_refresh"),
    ("Switched theme", "theme_toggle"), ("Signed in", "sign_in"),
]

_CHANNEL_SQL = """
    CASE
      WHEN utm_source IS NOT NULL THEN 'Campaign (UTM)'
      WHEN referrer IS NULL OR referrer = '' THEN 'Direct'
      WHEN referrer ~* '(google|bing|duckduckgo|yahoo|ecosia)\\.' THEN 'Search'
      WHEN referrer ~* '(twitter|x\\.com|t\\.co|facebook|instagram|linkedin|reddit|youtube|whatsapp|telegram)' THEN 'Social'
      ELSE 'Referral'
    END"""


def _chg(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev in (None, 0):
        return None
    return round((cur - prev) / prev, 4)


async def pm_report_csv(session: Any, now: datetime | None = None) -> str:
    """One readable sheet for a product/business manager: growth, engagement, funnel, retention,
    channels, reliability. Columns: section, metric, value, compare, change, note."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(IST).date()
    b = svc.ist_day_bounds
    t1 = b(today)[1]
    cur0, prev0 = b(today - timedelta(days=6))[0], b(today - timedelta(days=13))[0]
    m0 = b(today - timedelta(days=29))[0]
    rows: list[list[Any]] = []

    def add(section: str, metric: str, value: Any, compare: Any = "", change: Any = "", note: str = "") -> None:
        rows.append([section, metric, value, compare, change, note])

    async def scalar(sql: str, **p: Any) -> Any:
        return (await session.execute(text(sql), p)).scalar_one()

    async def active(a: datetime, z: datetime) -> int:
        return await scalar("SELECT COUNT(DISTINCT visitor_id) FROM analytics_events WHERE NOT is_bot AND ts >= :a AND ts < :z", a=a, z=z)

    # 1. Growth: audience size and stickiness
    wau, wau_prev = await active(cur0, t1), await active(prev0, cur0)
    mau = await active(m0, t1)
    per_day = [await active(*b(today - timedelta(days=i))) for i in range(7)]
    avg_dau = round(sum(per_day) / 7, 2)
    add("growth", "Active visitors today (DAU, so far)", per_day[0], per_day[1], _chg(per_day[0], per_day[1]), "compare = yesterday (full day)")
    add("growth", "Average DAU, last 7 days", avg_dau, "", "", "")
    add("growth", "Weekly active visitors (WAU)", wau, wau_prev, _chg(wau, wau_prev), "compare = previous 7 days")
    add("growth", "Monthly active visitors (MAU, 30d)", mau, "", "", "")
    add("growth", "Stickiness DAU/MAU", _ratio(avg_dau, mau), "", "", "share of monthly visitors who show up on a given day; 20%+ is strong for a utility app")
    add("growth", "Stickiness WAU/MAU", _ratio(wau, mau), "", "", "")
    cur, prev = await svc.compute_range(session, cur0, t1), await svc.compute_range(session, prev0, cur0)
    for label, key in [("New visitors", "new_visitors"), ("Returning visitors", "returning_visitors"), ("Sessions", "sessions"),
                       ("Page views", "pageviews"), ("Clicks", "clicks"), ("Signed-in users", "signed_in_users")]:
        add("growth", f"{label}, last 7 days", cur[key], prev[key], _chg(cur[key], prev[key]), "compare = previous 7 days")
    add("growth", "Returning-visitor share", _ratio(cur["returning_visitors"], cur["visitors"]), _ratio(prev["returning_visitors"], prev["visitors"]), "", "")

    # 2. Engagement
    med = await scalar("""SELECT COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY d),0) FROM (
        SELECT EXTRACT(EPOCH FROM MAX(ts)-MIN(ts)) d FROM analytics_events
        WHERE NOT is_bot AND ts >= :a AND ts < :z GROUP BY session_id) x""", a=cur0, z=t1)
    for label, c, p_, note in [
        ("Engaged-session rate", _ratio(cur["sessions"] - cur["bounced_sessions"], cur["sessions"]), _ratio(prev["sessions"] - prev["bounced_sessions"], prev["sessions"]), "sessions with 2+ page views or any interaction"),
        ("Bounce rate", _ratio(cur["bounced_sessions"], cur["sessions"]), _ratio(prev["bounced_sessions"], prev["sessions"]), "one page view, no interaction"),
        ("Pages per session", _ratio(cur["pageviews"], cur["sessions"]), _ratio(prev["pageviews"], prev["sessions"]), ""),
        ("Clicks per session", _ratio(cur["clicks"], cur["sessions"]), _ratio(prev["clicks"], prev["sessions"]), ""),
        ("Sessions per visitor", _ratio(cur["sessions"], cur["visitors"]), _ratio(prev["sessions"], prev["visitors"]), "visit frequency"),
        ("Average session seconds", round(float(cur["avg_session_seconds"]), 1), round(float(prev["avg_session_seconds"]), 1), ""),
    ]:
        add("engagement", label, c, p_, _chg(c, p_), note)
    add("engagement", "Median session seconds", round(float(med), 1), "", "", "less skewed than the average")

    # 3. Activation funnel (visitors who reached each step at any point in the 7-day window)
    p7 = {"a": cur0, "z": t1}
    steps = [
        ("1. Visited", "event='page_view'"),
        ("2. Opened the screener", "event='page_view' AND path='/screener'"),
        ("3. Ran a scan", "event='scan_run'"),
        ("4. Viewed a stock chart", "event='page_view' AND path LIKE '/chart/%'"),
        ("5. Added a stock to watchlist", "event='watchlist_add'"),
        ("6. Signed in", "event='sign_in'"),
        ("7. Created a price alert", "event='alert_create'"),
    ]
    first = prior = None
    for name, cond in steps:
        n = await scalar(f"SELECT COUNT(DISTINCT visitor_id) FROM analytics_events WHERE NOT is_bot AND ts >= :a AND ts < :z AND {cond}", **p7)
        first = n if first is None else first
        add("activation_funnel", name, n, _ratio(n, first), _ratio(n, prior) if prior is not None else "",
            "compare = share of all visitors; change = conversion from previous step (reached at any point, not strictly ordered)" if prior is None else "")
        prior = n

    # 4. Feature adoption
    for label, ev in _FEATURES:
        r = (await session.execute(text("""SELECT COUNT(DISTINCT visitor_id) v, COUNT(*) n FROM analytics_events
            WHERE NOT is_bot AND ts >= :a AND ts < :z AND event=:e"""), {**p7, "e": ev})).mappings().one()
        add("feature_adoption", label, r["v"], _ratio(r["v"], cur["visitors"]), "", f"{r['n']} uses" + ("; compare = adoption among all visitors, last 7 days" if label == _FEATURES[0][0] else ""))

    # 5. Retention (cohorts by first-seen IST day)
    ret = (await session.execute(text("""
        WITH first AS (SELECT visitor_id, MIN((ts AT TIME ZONE 'Asia/Kolkata')::date) d0 FROM analytics_events WHERE NOT is_bot GROUP BY 1),
        act AS (SELECT DISTINCT visitor_id, (ts AT TIME ZONE 'Asia/Kolkata')::date d FROM analytics_events WHERE NOT is_bot)
        SELECT f.d0 AS cohort, COUNT(*) AS size,
          COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM act a WHERE a.visitor_id=f.visitor_id AND a.d=f.d0+1)) AS d1,
          COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM act a WHERE a.visitor_id=f.visitor_id AND a.d=f.d0+7)) AS d7,
          COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM act a WHERE a.visitor_id=f.visitor_id AND a.d=f.d0+30)) AS d30
        FROM first f WHERE f.d0 >= CAST(:s AS date) AND f.d0 < CAST(:t AS date) GROUP BY 1 ORDER BY 1"""),
        {"s": today - timedelta(days=30), "t": today})).mappings().all()
    for label, key, lag in [("Day-1 retention", "d1", 1), ("Day-7 retention", "d7", 7), ("Day-30 retention", "d30", 30)]:
        elig = [r for r in ret if r["cohort"] <= today - timedelta(days=lag)]
        size = sum(r["size"] for r in elig)
        add("retention", label, _ratio(sum(r[key] for r in elig), size), "", "", f"cohort of {size} first-time visitors old enough to measure; exact-day return")
    for r in ret[-14:]:
        add("retention_by_cohort", str(r["cohort"]), r["size"], _ratio(r["d1"], r["size"]), _ratio(r["d7"], r["size"]) if r["cohort"] <= today - timedelta(days=7) else "",
            "value = new visitors that day; compare = returned next day; change = returned exactly 7 days later")

    # 6. Acquisition channels
    for r in await _rows(session, f"""
        WITH s AS (SELECT session_id, MIN(visitor_id) v,
                          (ARRAY_AGG({_CHANNEL_SQL.strip()} ORDER BY ts))[1] AS channel,
                          COUNT(*) FILTER (WHERE event='page_view') pv,
                          COUNT(*) FILTER (WHERE event NOT IN {_GENERIC_EVENTS} OR event='click') act,
                          BOOL_OR(event='scan_run') scanned
                   FROM analytics_events WHERE NOT is_bot AND ts >= :a AND ts < :z GROUP BY session_id)
        SELECT channel, COUNT(*) sessions, COUNT(DISTINCT v) visitors, AVG((pv>=2 OR act>0)::int) engaged, AVG(scanned::int) scan_rate
        FROM s GROUP BY channel ORDER BY sessions DESC""", p7):
        add("acquisition_channels", r["channel"], r["sessions"], round(float(r["engaged"]), 4), round(float(r["scan_rate"]), 4),
            "value = sessions; compare = engaged-session rate; change = share of sessions that ran a scan")

    # 7. Reliability and performance
    errs = cur["errors"]
    add("reliability", "JS errors per 1,000 sessions", round(1000 * errs / cur["sessions"], 2) if cur["sessions"] else "", "", "", f"{errs} errors in {cur['sessions']} sessions")
    good = {"LCP": (2500, 4000), "INP": (200, 500), "CLS": (0.1, 0.25), "FCP": (1800, 3000), "TTFB": (800, 1800)}
    for r in await _rows(session, """SELECT props->>'name' m, COUNT(*) n,
            ROUND(percentile_cont(0.75) WITHIN GROUP (ORDER BY (props->>'value')::float)::numeric, 3) p75
            FROM analytics_events WHERE NOT is_bot AND event='web_vital' AND ts >= :a AND ts < :z
              AND (props->>'value') ~ '^-?[0-9.]+$' GROUP BY 1 ORDER BY 1""", p7):
        g, ni = good.get(r["m"], (None, None))
        v = float(r["p75"])
        verdict = "" if g is None else ("good" if v <= g else "needs improvement" if v <= ni else "poor")
        add("reliability", f"{r['m']} p75", v, "", verdict, f"{r['n']} samples (ms, CLS unitless); Google thresholds")
    for r in await _rows(session, """SELECT COALESCE(path,'(none)') p, COUNT(*) n,
            ROUND(percentile_cont(0.75) WITHIN GROUP (ORDER BY (props->>'value')::float)::numeric, 0) p75
            FROM analytics_events WHERE NOT is_bot AND event='web_vital' AND props->>'name'='LCP' AND ts >= :a AND ts < :z
              AND (props->>'value') ~ '^-?[0-9.]+$' GROUP BY 1 HAVING COUNT(*) >= 3 ORDER BY 3 DESC LIMIT 5""", p7):
        add("reliability_slowest_pages", r["p"], float(r["p75"]), "", "", f"LCP p75 ms over {r['n']} samples")

    # 8. Usage depth (30 days)
    for r in await _rows(session, """WITH d AS (SELECT visitor_id, COUNT(DISTINCT (ts AT TIME ZONE 'Asia/Kolkata')::date) days
            FROM analytics_events WHERE NOT is_bot AND ts >= :a AND ts < :z GROUP BY 1)
            SELECT CASE WHEN days=1 THEN '1 day' WHEN days<=3 THEN '2-3 days' WHEN days<=7 THEN '4-7 days' ELSE '8+ days' END b,
                   COUNT(*) n FROM d GROUP BY 1 ORDER BY MIN(days)""", {"a": m0, "z": t1}):
        add("usage_depth_30d", f"Visitors active on {r['b']}", r["n"], _ratio(r["n"], mau), "", "compare = share of 30-day visitors")

    # 9. When people use it
    for r in await _rows(session, """SELECT EXTRACT(ISODOW FROM ts AT TIME ZONE 'Asia/Kolkata')::int dow, COUNT(DISTINCT visitor_id) v
            FROM analytics_events WHERE NOT is_bot AND event='page_view' AND ts >= :a AND ts < :z GROUP BY 1 ORDER BY 1""", {"a": m0, "z": t1}):
        add("usage_by_weekday_30d", ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][r["dow"]], r["v"])
    for r in await _rows(session, """SELECT EXTRACT(HOUR FROM ts AT TIME ZONE 'Asia/Kolkata')::int h, COUNT(DISTINCT visitor_id) v
            FROM analytics_events WHERE NOT is_bot AND event='page_view' AND ts >= :a AND ts < :z GROUP BY 1 ORDER BY 1""", {"a": m0, "z": t1}):
        add("usage_by_hour_ist_30d", f"{r['h']:02d}:00", r["v"])

    # 10. Definitions
    for m, d in [
        ("Visitor", "an anonymous browser id; one person on two browsers counts twice, cleared storage counts as new"),
        ("Session", "activity from one visitor with no gap over 30 minutes"),
        ("Engaged session", "2+ page views, or at least one click or product action"),
        ("Bots", "excluded from every figure above"),
        ("Days and hours", "IST calendar days"),
        ("Windows", "last 7 days = today plus the 6 days before; previous 7 days = the 7 days before that"),
        ("Data source", "raw event log kept 45 days (analytics_events); the daily rollup is kept forever"),
        ("Small samples", "percentages on fewer than ~100 visitors are noise, not signal"),
    ]:
        add("definitions", m, d)
    return _csv(["section", "metric", "value", "compare", "change", "note"], rows)


async def users_csv(session: Any) -> str:
    rows = await _rows(session, "SELECT user_id, first_seen, last_seen, event_count FROM analytics_users ORDER BY first_seen", {})
    return _csv(["user_id", "first_seen_utc", "last_seen_utc", "event_count"],
                [[str(r["user_id"]), r["first_seen"].isoformat(), r["last_seen"].isoformat(), r["event_count"]] for r in rows])


async def events_csv(session: Any, start: date, end: date, limit: int = 50_000) -> str:
    d0, _ = svc.ist_day_bounds(start)
    _, d1 = svc.ist_day_bounds(end)
    limit = max(1, min(limit, 100_000))
    rows = await _rows(session, """
        SELECT id, ts, visitor_id, session_id, user_id, event, path, props::text AS props, referrer, utm_source,
               utm_medium, utm_campaign, device, browser, os, country, viewport_w, is_bot, app_version
        FROM analytics_events WHERE ts >= :a AND ts < :b ORDER BY id LIMIT :n""", {"a": d0, "b": d1, "n": limit})
    cols = ["id", "ts", "visitor_id", "session_id", "user_id", "event", "path", "props", "referrer", "utm_source",
            "utm_medium", "utm_campaign", "device", "browser", "os", "country", "viewport_w", "is_bot", "app_version"]
    return _csv(cols, [[(r[c].isoformat() if isinstance(r[c], datetime) else r[c]) for c in cols] for r in rows])

# Usage analytics

First-party tracking of visits, clicks and product usage. Stored in your own Postgres; nothing goes to a third party.

## What is recorded
| Event | When | Notable props |
|---|---|---|
| `page_view` | every route change | signed_in, theme |
| `page_leave` | leaving a page or closing the tab | seconds visible |
| `click` | any button, link or tab | label (visible text, max 60 chars), tag, href |
| `scan_run` | a screener run succeeds | scan_id, kind, matches |
| `watchlist_add` / `watchlist_remove` | success | symbol |
| `alert_create` / `alert_delete` | success | |
| `ai_picks_refresh`, `theme_toggle`, `sign_in_started`, `sign_in` | | |
| `js_error` | uncaught error / rejection (max 5 per page) | message, file, line |
| `web_vital` | LCP, CLS, INP, FCP, TTFB | value, rating |

Also stored per event: anonymous visitor id, session id (30 min idle), path (no query string), device/browser/OS class, country (from the Vercel header), referrer origin+path, UTM tags, viewport width. Signed-in events carry an opaque user id.
**Never stored:** typed text, form values, IP address, raw user agent, email.

## Rules that keep numbers honest
- Bots are excluded from every metric and counted separately.
- All days are IST calendar days.
- Bounce = a session with one page view and no interaction. Session duration = last event minus first.
- Raw events are kept 45 days (`ANALYTICS_RAW_KEEP_DAYS`); the daily rollup (`analytics_daily`) is kept forever. Rollups are computed before raw rows are pruned.
- Free-tier guard: at most 15,000 events per day (`ANALYTICS_MAX_EVENTS_PER_DAY`), 240 per visitor per minute. Anything over is dropped and shown in the data-quality panel.
- Not tracked: Do Not Track, Global Privacy Control, browsers opted out in Settings, and non-production builds (set `NEXT_PUBLIC_ANALYTICS=on` to force on locally).
- Exclude yourself: open the site once with `?bs_optout=1` (undo with `?bs_optout=0`).
- Limits: a visitor is a browser, not a person; cleared storage looks like a new visitor.

## Viewing and proving the numbers
There is no dashboard page. Everything is a CSV you open in Google Sheets or Excel.

1. CSV endpoints (append `?token=<ANALYTICS_EXPORT_TOKEN>`):
   - `/api/admin/analytics/export/pm-report.csv` **the one to share with a PM or business manager**: growth (DAU/WAU/MAU, stickiness, week-over-week), engagement, activation funnel, feature adoption, D1/D7/D30 retention and daily cohorts, acquisition channels, reliability and Core Web Vitals, usage depth, weekday/hour patterns, plus a definitions section
   - `/api/admin/analytics/export/summary.csv?days=30` all headline metrics: visitors, sessions, page views, clicks, bounce, retention, top pages/clicks, features, sources, countries, devices, errors, web vitals
   - `/api/admin/analytics/export/daily.csv` one row per day (chart this)
   - `/api/admin/analytics/export/users.csv` signed-in users (opaque ids)
   - `/api/admin/analytics/export/events.csv?from=YYYY-MM-DD&to=YYYY-MM-DD&limit=` the raw log, i.e. the proof
2. Google Sheets: in a cell, `=IMPORTDATA("https://<railway-api-host>/api/admin/analytics/export/daily.csv?token=<TOKEN>")`. Use the direct Railway API URL, not the Vercel one (bot protection blocks Sheets). Treat the sheet as private since it contains the token.

## Server settings (Railway)
`ANALYTICS_EXPORT_TOKEN` (long random string), `ADMIN_EMAILS` (comma-separated), optional `ANALYTICS_ENABLED=false` kill switch. Run `alembic upgrade head` once to create the tables.

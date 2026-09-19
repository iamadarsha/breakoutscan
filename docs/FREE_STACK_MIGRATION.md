# Running BreakoutScan on a free stack

Written 2026-09-19 after Supabase flagged the project for **egress** (12.3 GB used of the 5 GB free
allowance; restrictions from 18 Oct 2026). Free-tier limits change: re-check each provider's pricing
page before committing to a move.

## What caused the Supabase overage (and what was done)

| Cause | Fix |
|---|---|
| The breakout engine re-read up to 210 raw 1-minute rows per symbol every ~40 s, all night and all weekend. | Engine does one final pass after the close, then idles until the next open. |
| Fallback 15-minute history returned raw 1-minute rows (wrong timeframe *and* ~10x the data). | 5/15-minute bars are aggregated inside Postgres (~60 compact bars per symbol). |
| The same breakout was re-confirmed and stored repeatedly (66k rows for ~20k real events; 8k on a Saturday). | 2-hour cooldown per symbol+trigger+direction+status; one-off cleanup done. |
| `ohlcv_1min` grew ~46 MB/day. | Daily retention job: 1-minute candles kept 3 days, breakout events 14 days. |

Result: database 257 MB -> 79 MB; egress expected to fall by roughly an order of magnitude. Check
`Supabase -> Organization -> Usage` a day after the change. If egress stays under ~150 MB/day the
free plan is sustainable and no migration is required.

## Component map

| Part | Today | Free option | Notes |
|---|---|---|---|
| Web | Vercel Hobby (git-connected, root `apps/web`) | same | Already free. |
| Auth | **Firebase Auth** (Google) - Spark plan | same | Free, no OAuth client to configure. Supabase Auth is no longer used at runtime. |
| Database | Supabase Postgres (free) | Supabase free (if egress is fixed) / self-host Postgres / another free Postgres | See "Database" below. |
| Redis | Railway Redis | Redis Cloud free (30 MB) or a Redis container | Set `REDIS_MAX_CONNECTIONS`. |
| API | Railway Hobby (paid credit) | Oracle Cloud Always Free (Ampere A1) | The only free always-on host with enough RAM; see "API host". |
| AI | Gemini + Groq free tiers | same | Groq free: 1,000 req/day, 8,000 tokens/min per model. |
| Market data | Upstox (free API) + Yahoo | same | Yahoo is unofficial; expect occasional breakage. |

## Database

The schema is managed by Alembic and the app only needs a normal Postgres 14+ (it uses
`date_bin`). Moving is one command:

```bash
cd apps/api
python scripts/migrate_database.py \
  --source "postgresql://USER:PASS@OLD_HOST:5432/DB" \
  --target "postgresql://USER:PASS@NEW_HOST/DB" \
  --create-schema --skip ohlcv_1min
```

`--create-schema` runs `alembic upgrade head` on the target; tables copy in dependency order and
row counts are verified; a non-empty target aborts unless you pass `--truncate`.
`ohlcv_1min` is disposable (refills within a session) - skipping it makes the move take seconds.
Then set `DATABASE_URL` on the API service. Tested against a real Postgres.

Free Postgres options and their catches (verify current limits):

- **Supabase free** - 500 MB and 5 GB egress. Works now that egress is fixed.
- **Neon free** - 0.5 GB storage, but compute is metered in CU-hours. This app writes candles
  continuously, so the database never idles and the monthly compute allowance is likely to run out
  before the month does. Use the `-pooler` host (the app then disables prepared statements
  automatically), or set `DB_DISABLE_STATEMENT_CACHE=true`.
- **Aiven free Postgres** - small but always on; check its current storage cap and inactivity rules.
- **Self-hosted on Oracle Always Free** (recommended if you want zero quotas) - run Postgres on the
  same machine as the API. No egress charges, no size cap beyond the disk (200 GB free tier).

Free tiers cap connections. Tune with `DB_POOL_SIZE` (default 4) and keep it under the provider's
limit; the app already enforces a small fixed pool with no overflow.

## Auth

Current: Firebase (project `studio-2470990952-6a3d3`, Google provider enabled, `breakoutscan-web.vercel.app`
authorised). Frontend selects the provider with `NEXT_PUBLIC_AUTH_PROVIDER` (`firebase` | `supabase`),
plus `NEXT_PUBLIC_FIREBASE_API_KEY`, `..._AUTH_DOMAIN`, `..._PROJECT_ID`, `..._APP_ID` (all public
identifiers). The API trusts an OIDC issuer purely by configuration:

```
AUTH_ISSUER=https://securetoken.google.com/<firebase-project-id>
AUTH_AUDIENCE=<firebase-project-id>
AUTH_JWKS_URL=https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com
```

Any other OIDC provider (Auth0, Clerk, ...) works the same way with its own issuer/audience/JWKS.
Supabase tokens are still accepted (ES256 via the project's JWKS, or legacy HS256 via
`SUPABASE_JWT_SECRET`), so both providers can be live during a transition.

Opaque user ids (Firebase uids) are mapped to a stable UUIDv5 scoped by issuer, so the existing
`uuid` `user_id` columns keep working. If a user already has data under an old id, move it with
`scripts/remap_user_id.py --database ... --old <uuid> --new <uuid>`. (At the time of writing no
user had any watchlist/alerts data, so nothing needs remapping.)

To add another sign-in domain (a custom domain, a preview URL): Firebase console ->
Authentication -> Settings -> Authorised domains.

## API host

Railway's Hobby plan bills against a monthly credit, so it is not free. The API needs an
always-on process (Upstox websocket, NSE poller, breakout engine), which rules out scale-to-zero
free tiers (Render free, Cloud Run, Koyeb free): they stop the pollers.

The one free host that fits is **Oracle Cloud Always Free, Ampere A1** (up to 4 OCPU / 24 GB). The
AMD `VM.Standard.E2.1.Micro` shape is too small (about 0.5-1 GB RAM: it swap-thrashed under this
load). A1 capacity in ap-hyderabad-1 was unavailable when tried, so a retry loop is needed.

On an A1 host: run the API (`apps/api/Dockerfile`), Redis and Postgres as containers on one
network; point `DATABASE_URL` / `REDIS_URL` at them. Containers do **not** auto-start after a
reboot unless you add a systemd unit or `podman generate systemd`.

## Redis

Data is cache-shaped (prices, indicators, scan results) and rebuilds itself, so migrating means
pointing `REDIS_URL` at the new server. Redis Cloud's free tier allows ~30 connections: set
`REDIS_MAX_CONNECTIONS=25`. Watch memory - the daily-candle cache is the largest key family; if
30 MB is tight, shorten its TTL in `app/services/yahoo_finance.py`.

## Settings reference (all optional)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local | Postgres connection |
| `DB_POOL_SIZE` | 4 | Fixed pool size (no overflow) |
| `DB_DISABLE_STATEMENT_CACHE` | false | Needed behind PgBouncer transaction pooling (auto for `:6543` / `-pooler`) |
| `REDIS_URL` / `REDIS_MAX_CONNECTIONS` | local / 50 | Redis and its client pool cap |
| `AUTH_ISSUER` / `AUTH_AUDIENCE` / `AUTH_JWKS_URL` | empty | Trust an OIDC provider |
| `SUPABASE_URL` / `SUPABASE_JWT_SECRET` | empty | Accept Supabase tokens |
| `GROQ_MODEL` / `GROQ_FALLBACK_MODELS` | `openai/gpt-oss-120b` / two fallbacks | Groq retires models; change without a code deploy |
| `GEMINI_API_KEY`, `GROQ_API_KEY` | empty | AI Picks / per-stock analysis |

## Rollback

Every change is behind configuration: set `NEXT_PUBLIC_AUTH_PROVIDER=supabase` (and redeploy the
web app) to return to Supabase Auth, or point `DATABASE_URL` back at the previous database - the
migration script never modifies the source.

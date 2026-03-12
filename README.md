# BreakoutScan — India's Most Powerful Stock Screener

## Project Overview
BreakoutScan is a production-grade, full-stack Indian stock screener platform providing:
- **Real-time NSE/BSE data** via Upstox Developer API WebSocket V3
- **12 pre-built scans** + custom scan builder with 18 operators
- **Sub-2-second screener** using Redis pipeline batch fetching
- **Web app** (Next.js) + **iOS app** (React Native)
- **Alert system** with Push, Telegram, and Email notifications

## Quick Start (Development)

### 1. Backend Setup
```bash
cd backend
cp .env.example .env
# Fill in UPSTOX_API_KEY, UPSTOX_API_SECRET (optional for mock mode)

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Run backend (mock mode if Upstox not configured)
uvicorn main:app --reload --port 8000
```

### 2. Full Stack (Docker)
```bash
docker compose up -d
```

### 3. API
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Backend Architecture
```
backend/
├── main.py                     # FastAPI app + lifespan + WebSocket endpoints
├── config.py                   # Pydantic settings
├── database.py                 # SQLAlchemy async engine
├── models.py                   # ORM models (stocks, OHLCV, scans, alerts)
├── schemas.py                  # Pydantic request/response types
├── data/
│   ├── upstox_auth.py          # OAuth2 token manager (Redis-backed)
│   ├── upstox_instruments.py   # NSE/BSE instrument loader
│   ├── upstox_streamer.py      # WebSocket V3 streamer + mock fallback
│   ├── candle_builder.py       # Tick → OHLCV for 5 timeframes
│   ├── indicator_engine.py     # pandas-ta indicators, cached in Redis
│   └── nse_fallback.py         # NSE API + mock data
├── screener/
│   ├── conditions.py           # 18 operator condition evaluators
│   ├── prebuilt_scans.py       # 12 pre-built scan definitions
│   ├── engine.py               # evaluate_scan (Redis pipeline batch)
│   └── orb.py                  # Opening Range Breakout logic
├── routes/                     # FastAPI routers
│   ├── auth.py                 # Upstox OAuth2
│   ├── live.py                 # Indices, prices, market status
│   ├── stocks.py               # Search, OHLCV, fundamentals
│   ├── screener.py             # Run scans
│   ├── watchlist.py            # User watchlists
│   └── alerts.py               # Alert management
└── websocket/
    └── manager.py              # WebSocket connection manager
```

## Phase 0 Designs
Stitch MCP generated **13 UI designs** in `/stitch-designs/`:
- Web: `landing.html`, `dashboard.html`, `screener.html`, `chart.html`, `watchlist.html`, `alerts.html`, `fundamentals.html`, `login.html`
- iOS: `ios-home.html`, `ios-screener.html`, `ios-watchlist.html`, `ios-chart.html`, `ios-alerts.html`

## Stitch MCP Project
- Project ID: `576333172353268664`
- [View on Stitch →](https://stitch.withgoogle.com/projects/576333172353268664)

## Environment Variables
All configs are in `backend/.env.example`. Key variables:
- `UPSTOX_API_KEY`, `UPSTOX_API_SECRET` — get from [developer.upstox.com](https://developer.upstox.com)
- `DATABASE_URL` — PostgreSQL (TimescaleDB) connection string
- `REDIS_URL` — Redis connection
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` — for user auth

## Key API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/indices` | Live index data |
| GET | `/api/market/status` | Market open/closed |
| GET | `/api/prices/{symbol}` | Live stock price |
| POST | `/api/screener/run` | Run custom scan |
| GET | `/api/screener/prebuilt` | List 12 pre-built scans |
| POST | `/api/screener/prebuilt/{id}/run` | Run a pre-built scan |
| GET | `/api/stocks/search?q=` | Symbol search |
| WS | `/ws/prices` | Live price stream |
| WS | `/ws/scans` | Live scan hit stream |
| WS | `/ws/alerts/{user_id}` | Personal alert stream |

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.12 |
| Database | TimescaleDB (PostgreSQL 16) |
| Cache | Redis 7 |
| Indicators | pandas-ta |
| Market Data | Upstox WebSocket V3 |
| Web Frontend | Next.js 15 (Phase 5) |
| Mobile | React Native + Expo (Phase 6) |
| Deployment | Google Cloud Run + Vercel |

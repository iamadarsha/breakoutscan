<div align="center">

<img src="https://img.shields.io/badge/BreakoutScan-Live-brightgreen?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0zIDEzbDQtNCA0IDQgNi04eiIvPjwvc3ZnPg==" />

# BreakoutScan

### India's Real-Time NSE/BSE Stock Screener & AI Intelligence Platform

*Scan NIFTY 500 in seconds · AI trade briefs · Live options analytics · Production-grade security*

[![Railway](https://img.shields.io/badge/API-Railway%20Pro-8B5CF6?style=flat-square&logo=railway)](https://codex-screener-production.up.railway.app/health)
[![Vercel](https://img.shields.io/badge/Web-Vercel-000000?style=flat-square&logo=vercel)](https://breakoutscan-web.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.13x-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com/)

---

**[Live Demo](https://breakoutscan-web.vercel.app/dashboard)** · **[API Docs](https://codex-screener-production.up.railway.app/docs)** · **[Report Bug](https://github.com/iamadarsha/breakoutscan/issues)**

</div>

---

## What is BreakoutScan?

BreakoutScan is a **full-stack, production-grade stock intelligence platform** built for Indian equity markets. It eliminates the morning grind of manually scanning hundreds of stocks across multiple tabs by surfacing breakout setups, volume anomalies, and AI-generated trade ideas — all in a single Bloomberg-dark interface.

The platform covers the **full NIFTY 500 universe** across NSE and BSE, runs technical scans in under two seconds, and layers a dual-model AI pipeline on top to give traders context, not just numbers.

> Built solo. Deployed in production. Trusted by traders.

---

## Screenshots

```
┌─────────────────────────────────────────────────────────────────────┐
│  ● MARKET OPEN    NIFTY 50 24891 +0.81%   NIFTY BANK 56266 +0.32%  │
├─────────────────────────────────────────────────────────────────────┤
│  Dashboard                                                           │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ ACTIVE       │ │ TRIGGERED    │ │ VOLUME       │ │ MARKET     │ │
│  │ BREAKOUTS    │ │ ALERTS       │ │ SURGES       │ │ BREADTH    │ │
│  │     24       │ │     8        │ │     12       │ │   84%      │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│                                                                      │
│  ⚡ Live Breakout Feed          ● 24 signals                        │
│  DIXON    ↑ 3.2%   Bullish EMA Crossover · RSI 58                   │
│  HDFCBANK ↑ 1.1%   Price Above SMA(200)  · Vol 2.3x avg             │
│  INFY     ↑ 2.4%   MACD Bullish Cross    · Near 52W High            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Features

### ⚡ Real-Time NIFTY 500 Screener
Scan all 500 stocks in under 2 seconds against 13 prebuilt technical setups:

| Category | Scan | Trigger Condition |
|---|---|---|
| Momentum | RSI Oversold | RSI(14) < 30 |
| Momentum | RSI Overbought | RSI(14) > 70 |
| Moving Average | Bullish EMA Crossover | EMA(9) crosses above EMA(21) |
| Moving Average | Bearish EMA Crossover | EMA(9) crosses below EMA(21) |
| Moving Average | Price Above SMA(200) | Close > SMA(200) — uptrend confirmation |
| Moving Average | Price Below SMA(200) | Close < SMA(200) — downtrend confirmation |
| Volume | Volume Spike 2x | Volume > 2× 20-day average |
| Volatility | Bollinger Squeeze | Band width < 5% of midline — pre-breakout |
| Trend | MACD Bullish Cross | MACD line crosses above signal line |
| Trend | MACD Bearish Cross | MACD line crosses below signal line |
| Breakout | Near 52-Week High | Close > 95% of 52-week high |
| Intraday | ORB Breakout | Price breaks above Opening Range High |
| Pattern | Bullish Engulfing | Candlestick reversal pattern |

### 🤖 AI Trade Brief (Dual-Model Pipeline)
Every morning the system reads **40+ financial news articles** — earnings, macro events, FII/DII flows, RBI/SEBI updates — and runs them through:

- **Gemini 3.1 Pro** → macro context, sector reasoning, fundamental signals
- **Llama 4** → pattern recognition across historical technical setups

Output: plain-language trade ideas with conviction scores. Not just *what* is moving — but *why*, *what the setup looks like*, and *whether the risk/reward makes sense*.

### 📊 Options Intelligence Module
- Live PCR (Put-Call Ratio) by strike
- IV Percentile — know if options are cheap or expensive
- OI Buildup — track where large positions are being built
- Max Pain — the price at which maximum options expire worthless
- All updated every 30 seconds during market hours

### 📈 Interactive Charts
One-click from any screener result to a full interactive chart:
- 1D / 1W / 1M / 6M / 1Y timeframes
- EMA(9), EMA(21), SMA(50), SMA(200) overlays
- Volume bars with 20-day average baseline
- Bollinger Bands, MACD, RSI panels

### 🛡 Watchlist & Alerts
- Build personal watchlists across NIFTY 50 / NIFTY 500
- Set price, RSI, and volume alerts
- Alerts fire in real-time via WebSocket push

---

## Data Architecture — 5-Layer API Cascade

BreakoutScan uses a **5-layer broker API waterfall** — each layer takes over automatically if the one above fails or rate-limits:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Groww API          Primary real-time feed         │
│  Layer 2 — Upstox API         Secondary price data           │
│  Layer 3 — Dhan API           Options & derivatives layer    │
│  Layer 4 — Fyers API          Technical data redundancy      │
│  Layer 5 — Paytm Money API    Final fallback + portfolio ctx  │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  5 System Support APIs                                       │
│  • Health Monitor    watches all 5 data layers              │
│  • Circuit Breaker   auto-switches on failure               │
│  • Cache Manager     eliminates redundant calls             │
│  • Session State     keeps results stable mid-switch        │
│  • Alert System      notifies before users notice           │
└─────────────────────────────────────────────────────────────┘
```

This means scan results update faster than Chartink's free-tier 5-minute delay — with **zero manual intervention** when any individual layer degrades.

---

## Tech Stack

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| UI Runtime | React 19 |
| Styling | Tailwind CSS v4 |
| Components | shadcn/ui |
| Charts | Lightweight Charts (TradingView) |
| State | TanStack Query v5 |
| Real-time | WebSockets (native) |
| Animations | Framer Motion |

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.12) |
| Technical Analysis | pandas-ta 0.4.x |
| Data Science | pandas 2.x + numpy 2.x |
| Task Queue | asyncio background tasks |
| Rate Limiting | slowapi |
| Caching | Redis (Upstash) |
| WebSocket | python-socketio |

### AI Pipeline
| Model | Role |
|---|---|
| Gemini 3.1 Pro | Macro reasoning, news synthesis, sector context |
| Llama 4 | Pattern recognition, historical setup matching |
| Google Generative AI SDK | Gemini API integration |
| Groq SDK | Llama inference (sub-100ms) |

### Infrastructure
| Service | Purpose |
|---|---|
| Railway Pro | FastAPI backend + auto-deploy |
| Vercel | Next.js frontend + Edge CDN |
| Supabase | PostgreSQL + Auth + Row Level Security |
| Redis (Upstash) | Live price cache + indicator store |
| Docker | Containerised API builds |

---

## Use Cases

### 🏢 Retail Trading Desks & Prop Firms
**Problem:** Analysts spend 60–90 minutes each morning manually screening stocks before the 9:15 AM open.

**Solution:** BreakoutScan pre-runs all 13 technical scans across NIFTY 500 overnight and at market open. Analysts arrive to a ranked shortlist — sorted by signal strength, volume confirmation, and AI conviction score. The desk saves 60+ minutes per session and acts on cleaner, data-driven setups.

*Key features used: Screener, AI Trade Brief, Multi-scan aggregation*

---

### 📱 Independent Retail Traders
**Problem:** Free tools like Chartink have 5-minute delayed data. Paying for real-time data across multiple platforms (charts, screener, options) is expensive and requires constant tab-switching.

**Solution:** BreakoutScan combines screener + charts + options data in a single zero-delay interface. A trader can spot a breakout signal, check the chart, verify the options setup, and review the AI context — without leaving the platform.

*Key features used: Live screener, Options module, One-click charts, AI briefs*

---

### 🏦 Portfolio Management Companies (PMS / AIF)
**Problem:** Fund managers running momentum or factor strategies need systematic, repeatable scan criteria applied consistently across their universe — not ad-hoc manual screening.

**Solution:** The `/api/screener/run` and `/api/screener/custom` endpoints allow programmatic scan execution with configurable conditions. Custom scans accept any combination of indicators (RSI, EMA, SMA, MACD, Bollinger, ATR, ADX, VWAP) with standard operators — enabling systematic strategy backtesting and live signal generation via API.

*Key features used: Custom scan API, Prebuilt scan API, Webhook alerts*

---

### 📊 SEBI-Registered Research Analysts (RA)
**Problem:** Writing daily market commentary and stock-specific trade notes requires synthesising NSE data, news flow, and technical charts — a multi-hour process done manually.

**Solution:** The AI Trade Brief pipeline reads 40+ news articles overnight and outputs structured trade notes with entry rationale, sector context, and risk framing. RAs can use this as a first-draft foundation, cutting commentary preparation time by 70%.

*Key features used: AI Picks page, AI Trade Brief, Fundamentals module*

---

### 🎓 Algo Trading Students & Quant Researchers
**Problem:** Learning systematic trading requires a live, real-data environment to test scan logic and understand how technical conditions map to real market behaviour.

**Solution:** BreakoutScan exposes a fully documented REST API (`/docs`) with live NIFTY 500 data, pre-computed indicators (RSI, EMA, SMA, MACD, Bollinger, ATR, ADX, VWAP, 52W High), and a custom scan endpoint. Researchers can write scan conditions in JSON and test them against the live market — no data vendor subscription required.

*Key features used: Custom scan API, Indicator data API, Live charts*

---

### 🏗 Fintech Startups Building on Top
**Problem:** Building a trading platform from scratch requires solving data ingestion, indicator computation, options analytics, and AI integration — a 12–18 month engineering effort.

**Solution:** BreakoutScan's API layer can serve as a data and intelligence backend for fintech applications. The 5-layer data cascade, Redis-cached indicator store, and AI pipeline are all accessible via documented REST endpoints — letting product teams focus on their UX rather than rebuilding market data infrastructure.

*Key features used: Full REST API, WebSocket feed, AI endpoint, Options API*

---

## Repository Structure

```
breakoutscan/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/routes/     # REST endpoints
│   │   │   │   ├── screener.py       # /api/screener/*
│   │   │   │   ├── market.py         # /api/market/*
│   │   │   │   ├── stocks.py         # /api/stocks/*
│   │   │   │   ├── ai_suggestions.py # /api/ai/*
│   │   │   │   ├── alerts.py         # /api/alerts/*
│   │   │   │   └── fundamentals.py   # /api/fundamentals/*
│   │   │   ├── services/
│   │   │   │   ├── screener_engine.py    # Core scan execution
│   │   │   │   ├── yahoo_finance.py      # Indicator computation
│   │   │   │   ├── nse_poller.py         # Live data + universe
│   │   │   │   ├── prebuilt_scans.py     # 13 scan definitions
│   │   │   │   ├── condition_evaluator.py# Scan DSL
│   │   │   │   └── redis_cache.py        # Cache layer
│   │   │   └── core/
│   │   │       ├── config.py             # Settings + env
│   │   │       └── rate_limit.py         # slowapi limits
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── web/                    # Next.js 15 frontend
│   │   └── src/
│   │       ├── app/
│   │       │   ├── dashboard/      # Main trading dashboard
│   │       │   ├── screener/       # Full screener page
│   │       │   ├── ai-picks/       # AI trade briefs
│   │       │   ├── charts/         # Interactive charts
│   │       │   ├── alerts/         # Alert management
│   │       │   ├── watchlist/      # Personal watchlist
│   │       │   └── fundamentals/   # Company fundamentals
│   │       ├── components/
│   │       │   ├── dashboard/      # Dashboard widgets
│   │       │   └── layout/         # App shell, sidebar, topbar
│   │       └── hooks/              # TanStack Query hooks
│   │
│   ├── mobile/                 # Expo React Native app (iOS/Android)
│   └── ios/                    # Native iOS configuration
│
├── packages/
│   └── contracts/              # Shared TypeScript types
│
├── docs/                       # Architecture docs, design system
├── infra/                      # Infrastructure configuration
├── docker-compose.yml          # Local development
└── README.md
```

---

## Security

Production-grade hardening applied throughout:

| Layer | Implementation |
|---|---|
| Rate Limiting | slowapi — 30 req/min screener, 10 req/min AI, 60 req/min default |
| CORS | Strict origin allowlist — production domain only, no wildcards |
| Debug Routes | Blocked at middleware layer in production (`ENVIRONMENT=production`) |
| Secrets | Zero hardcoded credentials — all via environment variables |
| Database | Supabase Row Level Security enforced on every table |
| Dependencies | All packages pinned with explicit version ranges — no surprise upgrades |
| Graceful Degradation | API down → frontend shows clean fallback, not crash |

---

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.12+
- Docker + Docker Compose
- Redis (or Upstash Redis URL)
- Supabase project

### Local Development

```bash
# Clone
git clone https://github.com/iamadarsha/breakoutscan.git
cd breakoutscan

# Copy environment variables
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, REDIS_URL, GEMINI_API_KEY

# Start everything
docker compose up --build
```

Services start at:
- **API:** `http://localhost:8001/health`
- **API Docs:** `http://localhost:8001/docs`
- **Web:** `http://localhost:3000`

### API-Only (without Docker)

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload --port 8001
```

### Frontend Only

```bash
cd apps/web
npm install
npm run dev
```

---

## API Reference

Base URL: `https://codex-screener-production.up.railway.app`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System health — Redis, poller, universe size |
| GET | `/api/market/status` | Market open/closed, next session times |
| GET | `/api/market/breadth` | Advance/Decline ratio, total stocks |
| GET | `/api/market/indices` | NIFTY 50, BANK, IT, PHARMA, AUTO live data |
| GET | `/api/stocks` | NIFTY 500 stock list with live prices |
| GET | `/api/stocks/{symbol}` | Single stock detail + indicators |
| GET | `/api/screener/prebuilt` | List all 13 prebuilt scan definitions |
| POST | `/api/screener/run` | Run a prebuilt scan by ID |
| POST | `/api/screener/custom` | Run a custom scan with your own conditions |
| GET | `/api/fundamentals/{symbol}` | P/E, EPS, revenue, sector data |
| GET | `/api/alerts` | List user alerts |
| POST | `/api/alerts` | Create a new alert |

Full interactive docs at `/docs`.

---

## Environment Variables

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Redis
REDIS_URL=redis://...

# AI
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...

# Market Data
INDIAN_API_KEY=...

# Security
ENVIRONMENT=production
SECRET_KEY=...

# CORS (comma-separated, optional)
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

---

## Deployment

### Railway (API)

The API deploys automatically on push to `main`. Railway uses the `apps/api/Dockerfile`.

Build strategy (OOM-safe):
```dockerfile
# Phase 1: heavy data-science stack with pre-built wheels only
RUN pip install --prefer-binary numpy pandas pandas-ta

# Phase 2: remaining dependencies
RUN pip install --prefer-binary -r requirements.txt
```

### Vercel (Web)

The web app deploys automatically from `apps/web` on push to `main`.

---

## Performance

| Operation | Time |
|---|---|
| NIFTY 500 full scan (13 conditions) | < 2 seconds |
| Indicator compute for 50 symbols | ~15 seconds (5 parallel batches) |
| AI Trade Brief generation | 3–8 seconds |
| Live price cache refresh | 30 seconds |
| Indicator cache TTL | 4 hours |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

```bash
# Create a feature branch
git checkout -b feature/your-feature

# Make changes, then run tests
npm run test:api

# Commit and push
git push origin feature/your-feature
```

---

## Roadmap

- [ ] Mobile app (Expo iOS/Android) — in development
- [ ] Options chain full view with Greeks
- [ ] Backtesting module — test any scan condition historically
- [ ] Portfolio P&L tracker with positions
- [ ] Push notifications for alerts (iOS/Android)
- [ ] Webhook delivery for scan results
- [ ] Multi-user team workspaces

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ by [Adarsha Chatterjee](https://github.com/iamadarsha)

*Made with love by a fellow trader · Trade With Adarsha · [@iamadarsha](https://instagram.com/iamadarsha)*

**[breakoutscan.in](https://breakoutscan.in)** · **[Live App](https://breakoutscan-web.vercel.app/dashboard)** · **[API](https://codex-screener-production.up.railway.app/docs)**

</div>

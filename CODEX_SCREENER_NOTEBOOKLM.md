# BreakoutScan: Complete Project Knowledge Base

> This document is optimized for Google NotebookLM. Upload this file as a source to generate mind maps, infographics, audio overviews, and study guides about the BreakoutScan project.

---

## Project Identity

- **Project Name**: BreakoutScan
- **Internal Codename**: BreakoutScan
- **What It Does**: Real-time Indian stock market screener with AI-powered stock recommendations
- **Target Users**: Indian retail traders and investors who want technical analysis for NSE and BSE stocks without paying for expensive platforms
- **Live Website**: breakoutscan-web-production.up.railway.app
- **Live API**: breakoutscan-api-production.up.railway.app
- **Repository Structure**: Monorepo with 3 apps (web frontend, Python API backend, iOS native app)

---

## Mind Map: Project Architecture Hierarchy

The project has a clear hierarchy. At the top level is the BreakoutScan platform. It branches into three main applications: the Web App, the API Backend, and the iOS App. Each application connects to shared services: a PostgreSQL database on Supabase, a Redis cache on Railway, and external data APIs.

The Web App branches into 8 pages: Dashboard, AI Picks, Screener, Charts, Watchlist, Alerts, Fundamentals, and Settings. Each page connects to specific API endpoints on the backend.

The API Backend branches into 5 service modules: Market Data Service, AI Suggestions Service, Screener Engine, Price History Service, and User Features Service. The AI Suggestions Service further branches into its 3-layer fallback system: Layer 1 (RSS + Technical Scoring, zero API), Layer 2 (Gemini 3.1 Flash Lite), and Layer 3 (Groq/xAI).

The external data layer branches into 4 categories: Stock Market APIs (NSE via indianapi.in, Yahoo Finance, Upstox WebSocket), AI Services (Gemini, Groq, xAI), News Feeds (10 RSS sources), and Reference Data (Wikipedia, TradingView).

---

## Infographic: Frontend Tech Stack

The frontend is built with these technologies, grouped by purpose:

**Core Framework**: Next.js version 15.3.1 provides the application framework with server-side rendering. React version 19.1.0 powers the UI components. TypeScript version 5.9.3 adds static type checking.

**Styling and Design**: Tailwind CSS version 3.4.17 is the utility-first CSS framework. The design follows a dark terminal theme inspired by professional trading terminals, using zinc and slate dark backgrounds with emerald green for positive price movements and red for negative movements. Framer Motion version 12.10.5 handles all animations including page transitions, card reveals, and micro-interactions.

**State Management**: Zustand version 5.0.3 manages client-side state for live price data and WebSocket connections. React Query (TanStack Query) version 5.75.4 handles all server state with automatic caching, background refetching, and stale-while-revalidate patterns.

**Data Visualization**: TradingView Lightweight Charts version 5.0.8 renders professional-grade candlestick charts with volume panels on the Charts page. Recharts version 2.15.3 creates donut charts for market breadth and bar charts for volume displays.

**UI Components**: Lucide React version 0.503.0 provides the icon library with 1500+ SVG icons. React Hook Form version 7.56.3 handles form state with minimal re-renders. Zod version 3.24.4 provides schema validation. TanStack React Table version 8.21.3 provides headless sortable and filterable data tables. Sonner version 2.0.3 provides toast notifications.

**Deployment Platform**: Railway hosts the frontend with automatic deployments from the GitHub main branch.

---

## Infographic: Backend Tech Stack

The backend is a Python application using these technologies:

**Core Framework**: FastAPI is the async Python web framework that auto-generates OpenAPI documentation. Uvicorn is the ASGI server. Pydantic Settings manages configuration from environment variables.

**Database and ORM**: PostgreSQL version 16 with TimescaleDB extension is the primary database, hosted on Supabase in the Mumbai (ap-south-1) region. TimescaleDB hypertables store time-series OHLCV candlestick data efficiently. SQLAlchemy version 2.0 with async support provides the ORM layer. Alembic manages 4 database migration versions.

**Caching Layer**: Redis version 7 on Railway provides in-memory caching. The cache stores 461 price keys (JSON strings with 300-second TTL), 380 indicator keys (hashes with 600-second TTL), AI suggestion results (TTL until 9 AM next trading day), and market index data.

**HTTP and Data Fetching**: httpx provides async HTTP calls to external APIs. feedparser parses RSS news feeds from 10 sources. yfinance fetches historical OHLCV data from Yahoo Finance and computes technical indicators.

**AI Integration**: Google Generative AI SDK connects to Gemini 3.1 Flash Lite as the primary AI engine. Groq SDK connects to Llama 3.3 70B as the secondary fallback. xAI SDK connects to Grok as an additional fallback.

**Logging**: structlog provides structured JSON logging for production debugging.

**Deployment Platform**: Railway hosts the backend with automatic Docker-based deployments from GitHub main branch.

---

## Infographic: iOS App Tech Stack

**Framework**: SwiftUI provides the declarative UI. **Web Integration**: WKWebView loads the production Railway URL inside the native app shell. **Language**: Swift 5.9+. **IDE**: Xcode 26.3. **Features**: Purple gradient launch screen with "BS" logo, pull-to-refresh, external links open in Safari.

---

## Infographic: External Services and Platforms Used

### Hosting Platforms (2 platforms)
1. **Railway** - Hosts both the Next.js frontend web app AND the FastAPI backend API. Auto-deploys from GitHub. Also hosts the Redis cache.
2. **Supabase** - Hosts PostgreSQL 16 with TimescaleDB in Mumbai region. Provides database dashboard, SQL editor, and connection pooling.

### Stock Market Data APIs (4 sources)
1. **NSE via indianapi.in** - Real-time NSE stock listings, trending stocks, IPO data, mutual fund data. Authenticated via API key.
2. **Yahoo Finance (yfinance)** - Historical OHLCV data for all timeframes. Computes RSI, EMA, MACD, Bollinger Bands. No auth required.
3. **Upstox API v2** - Real-time WebSocket tick data for live price updates. OAuth2 authentication.
4. **NSE Direct Scraping** - Fallback data source for index values and market status.

### AI and LLM Services (4 services)
1. **Technical Scoring Engine** (Layer 1) - Custom-built, zero API dependency. Uses RSS + Redis data + composite scoring. Always runs first.
2. **Google Gemini 3.1 Flash Lite** (Layer 2) - Primary LLM AI engine. Two API keys for redundancy. Free-tier with daily quota (500 RPD).
3. **Groq with Llama 3.3 70B** (Layer 3) - Secondary AI fallback. ~500K free tokens/day. OpenAI-compatible.
4. **xAI Grok** (Layer 3 alternate) - Additional AI fallback alongside Groq.

### News Sources (10 RSS Feeds)
1. Google News India - 5 feeds: Indian stock market, NSE stocks, Indian economy, stock market trading, Nifty 50
2. Moneycontrol - 2 feeds: market news, stock analysis
3. Economic Times Markets - 1 feed: market and financial news
4. Mint Markets - 1 feed: business and market news
5. Business Standard Markets - 1 feed: market and company news

### Reference Data (2 sources)
1. **Wikipedia API** - Company information and descriptions for stock detail pages
2. **TradingView Lightweight Charts** - Client-side charting library for professional chart rendering

### Development Tools (4 tools)
1. **GitHub** - Source control for the monorepo
2. **Docker and Docker Compose** - Local development with PostgreSQL, Redis, API, and web containers
3. **Claude Code CLI** - AI-assisted development using Model Context Protocol (MCP)
4. **Xcode 26.3** - iOS app development

---

## Mind Map: AI Stock Picker 3-Layer Fallback System

The AI Stock Picker is the flagship feature. It guarantees 15 stock recommendations (5 intraday, 5 weekly, 5 monthly) regardless of API availability. The system flows through three layers in sequence.

**Layer 1: Technical Scoring Engine** (zero API, RSS-based) is tried first with zero external API dependency. Step 1: Load Nifty 500 stock list from nifty500_seed.json. Step 2: Scan 40 RSS headlines for stock symbol or company name mentions. Step 3: Bulk-read 461 price keys and 380 indicator keys from Redis using pipeline reads (2 round trips instead of 841 individual calls). Step 4: Score each stock on a 0-100 composite scale with 5 factors: News mentions (0-25 points), Price momentum (0-25 points), RSI signal (0-20 points), EMA crossover (0-15 points), Volume (0-15 points). Step 5: Apply timeframe-specific weights, select top 5 per timeframe with no duplicates. Step 6: Generate rationale strings. Timeout is 15 seconds.

If Layer 1 fails, **Layer 2: Google Gemini 3.1 Flash Lite** activates. It receives 40 parsed RSS headlines plus a market summary containing NIFTY 50 level, top gainers, and top losers. Gemini analyzes news sentiment and market conditions to produce 15 picks with entry price, target, stop loss, and rationale. It uses a primary API key first, then falls back to a backup key. The call is wrapped in a Python thread executor with 20-second timeout because Gemini's SDK blocks the event loop during internal retries on 429 quota-exceeded errors.

If Layer 2 fails, **Layer 3: Groq Llama 3.3 70B and xAI Grok** activates. It sends the same prompt and expects the same output format. Groq offers ~500K free tokens/day. Timeout is 25 seconds.

The results are cached in Redis with TTL until 9 AM next trading day. The GET endpoint returns cached results instantly. If empty, returns "pending" and triggers background generation.

---

## Mind Map: Application Pages (8 pages)

**Dashboard**: Main landing page. Shows stat cards (active breakouts, triggered alerts, volume surges, market breadth). Features a scrolling index ticker with NIFTY 50, NIFTY BANK, NIFTY IT, NIFTY MIDCAP 50. Includes market breadth donut chart and live breakout feed.

**AI Picks**: AI-generated stock recommendations. Three timeframe tabs: Intraday (5 picks), Weekly (5 picks), Monthly (5 picks). Each pick card shows symbol, company name, entry price, target price, stop loss, rationale text, confidence percentage, and live stock change percentages.

**Screener**: Technical scan engine with 13 prebuilt scans: RSI Oversold, RSI Overbought, Bullish EMA Crossover, Bearish EMA Crossover, Price Above SMA200, Price Below SMA200, Volume Spike, Bollinger Squeeze, MACD Bullish Cross, Near 52-Week High, ORB Breakout, Bullish Engulfing, and Custom Scan Builder with AND/OR logic.

**Charts**: Interactive candlestick charts with TradingView Lightweight Charts v5. Timeframes: 1min, 5min, 15min, 1day. Overlays: EMA20, EMA50, RSI14, MACD, Bollinger Bands. Volume panel below chart. Wikipedia company info panel.

**Watchlist**: Personal stock tracking with live prices. Search modal filters Nifty 500 universe. Shows LTP, change%, volume, high, low per stock.

**Alerts**: Price alert creation with target price and direction (above/below). Triggered alerts in timeline view. Real-time WebSocket notifications.

**Fundamentals**: Filter stocks by PE ratio, PB ratio, market cap, ROE, dividend yield, debt-to-equity.

**Settings**: User preferences and configuration. Includes dark/light theme toggle for switching between dark terminal theme and light mode.

---

## Mind Map: Data Flow Architecture

Data flows through 4 pipelines into the platform:

**Pipeline 1 - Live Price Pipeline**: NSE Poller runs every 30 seconds. Fetches live prices from indianapi.in. Writes to Redis as price:{SYMBOL} keys with 300-second TTL. Serves Dashboard, Watchlist, and Screener pages.

**Pipeline 2 - Technical Indicator Pipeline**: Yahoo Finance fetches historical OHLCV data. Computes RSI 14, EMA 9, EMA 21, MACD (12,26,9), and Bollinger Bands (20,2). Stores in Redis as ind:{SYMBOL}:1d hashes with 600-second TTL. Serves Charts, Screener, and AI Picks pages.

**Pipeline 3 - AI Suggestions Pipeline**: Aggregates 10 RSS feeds into 40 headlines. Loads market summary from Redis. Passes through 3-layer AI chain (Gemini -> Groq/Grok -> Technical Scoring). Caches results in Redis until 9 AM next trading day. Serves AI Picks page.

**Pipeline 4 - Real-time WebSocket Pipeline**: Upstox WebSocket streams live tick data. Broadcasts to connected frontend clients. Powers live price updates on Dashboard and Watchlist.

The frontend makes REST API calls to the FastAPI backend, which reads from Redis cache first (for speed) or PostgreSQL/Supabase (for persistence) depending on data type.

---

## Mind Map: Project Build Phases (6 phases)

**Phase 1 - Foundation**: Monorepo setup, FastAPI backend init, Next.js 15 frontend with React 19 and TypeScript, Docker Compose for local dev, Supabase database schema creation.

**Phase 2 - Data Pipeline**: NSE Poller with 30-second cycle, Redis cache layer, Yahoo Finance historical data integration, technical indicator engine (RSI, EMA, MACD, Bollinger Bands), Nifty 500 seed data loading.

**Phase 3 - Core Features**: Dashboard with stat cards and index ticker, Screener with 13 prebuilt scans, Charts with TradingView v5, Watchlist with live prices, Alerts with price triggers.

**Phase 4 - AI Stock Picker**: Gemini API with primary + backup keys, Groq fallback with Llama 3.3 70B, RSS feed parser for 10 news sources, Technical scoring engine as zero-API fallback, 3-layer fallback chain, background generation with instant GET response.

**Phase 5 - Deployment**: Railway backend auto-deploy, Railway frontend SSR deploy, Redis on Railway with 461 cached keys, iOS SwiftUI app with WebView.

**Phase 6 - Production Hardening**: Gemini thread executor fix (SDK blocks event loop), Redis pipeline reads (841 keys in 2 round trips), global timeouts on every layer, mobile UI fixes for iPhone, debug endpoint for production troubleshooting.

---

## Database Schema

**PostgreSQL Tables on Supabase**:
- stocks: Symbol, company name, sector, industry, market cap. 500 NSE stocks from Nifty 500 universe.
- watchlist: Links user IDs to stock symbols.
- alerts: Target price, direction (above/below), active/triggered status.
- ohlcv: TimescaleDB hypertable for time-series candlestick data. 1-minute and daily candles.

**Redis Cache Keys on Railway**:
- price:{SYMBOL}: JSON string with LTP, change, change_pct, volume, high, low. 461 keys. 300s TTL.
- ind:{SYMBOL}:1d: Hash with rsi_14, ema_9, ema_21, macd, macd_signal, bb_upper, bb_lower, bb_mid. 380 keys. 600s TTL.
- ai:suggestions: JSON with 15 stock picks. TTL until 9 AM next trading day.
- market:indices: JSON with NIFTY 50, NIFTY BANK, NIFTY IT, NIFTY MIDCAP 50.
- market:breadth: JSON with advances, declines, unchanged.

---

## API Endpoints Summary

**Market Data**: GET /api/market/status, GET /api/market/breadth, GET /api/market/sectors, GET /api/indices

**Stock Data**: GET /api/stocks, GET /api/prices/history, GET /api/prices/indicators, GET /api/company/{symbol}

**Screener**: POST /api/screener/run (custom scan), GET /api/screener/prebuilt/{scan_name} (13 prebuilt scans)

**AI Suggestions**: GET /api/ai-suggestions (cached instant), POST /api/ai-suggestions/refresh (force regenerate), GET /api/ai-suggestions/debug (diagnostics)

**User Features**: CRUD /api/watchlist, CRUD /api/alerts, GET /api/fundamentals

**Authentication**: GET /auth/upstox/login (OAuth2 initiation), GET /auth/upstox/callback (OAuth2 callback)

---

## Design System

**Color Palette**: Dark zinc/slate backgrounds (#0a0a0a to #1a1a2e). Semi-transparent card surfaces. Emerald green (#10b981) for positive/up movements. Red (#ef4444) for negative/down movements. Purple gradient for branding accents. Gray-300 for body text, white for headings.

**Typography**: System font stack (Inter/sans-serif) for text. Monospace font for prices and numbers.

**Component Patterns**: Terminal-inspired aesthetic with subtle glow effects. Mobile-first responsive design with breakpoints at 640px, 768px, and 1024px. Sortable and filterable data tables. Toast notifications via Sonner. Modal dialogs for search and confirmation.

---

## Technology Count Summary

For creating an infographic, here are the counts:

- **Frontend Technologies**: 13 (Next.js, React, TypeScript, Tailwind CSS, Zustand, React Query, TradingView Charts, Framer Motion, Recharts, Lucide Icons, React Hook Form, Zod, Sonner)
- **Backend Technologies**: 12 (FastAPI, Python, SQLAlchemy, Alembic, Uvicorn, Pydantic, httpx, feedparser, yfinance, structlog, Google GenAI SDK, Groq SDK)
- **Database Technologies**: 4 (PostgreSQL, TimescaleDB, Redis, Supabase)
- **AI/LLM Services**: 4 (Gemini 3.1 Flash Lite, Groq Llama 3.3 70B, xAI Grok, Custom Scoring Engine)
- **External Data APIs**: 5 (NSE/indianapi.in, Yahoo Finance, Upstox WebSocket, NSE Direct, Wikipedia)
- **News Sources**: 10 RSS feeds from 5 publishers
- **Hosting Platforms**: 2 (Railway, Supabase)
- **iOS Technologies**: 4 (SwiftUI, WKWebView, Swift, Xcode)
- **DevOps Tools**: 3 (GitHub, Docker, Railway Auto-Deploy)
- **Development Tools**: 2 (Claude Code CLI with MCP, Mermaid.js)

**Total unique technologies and services: 59**

---

## Key Architecture Decisions

1. **Monorepo**: All code in one repository for unified deployment and shared configuration.
2. **Redis-first caching**: All frequently accessed data goes through Redis before database, reducing latency from seconds to milliseconds.
3. **3-layer AI fallback**: Ensures AI picks never return empty, even during complete API outages.
4. **Thread executor for Gemini**: Google's SDK blocks Python's event loop during retries. Using run_in_executor enables proper timeout cancellation.
5. **Redis pipelines**: Reading 841 keys individually took 60+ seconds. Pipelines batch into 2 round trips.
6. **Background generation**: AI picks generate in background tasks so the GET endpoint always returns instantly.
7. **TimescaleDB hypertables**: Efficient time-range queries for candlestick data.

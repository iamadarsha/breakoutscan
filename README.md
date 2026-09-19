<div align="center">

<img src="docs/assets/hero.svg" alt="BreakoutScan: a screener and breakout monitor for NSE stocks" width="100%"/>

<br/>

[![Live app](https://img.shields.io/badge/live%20app-breakoutscan--web.vercel.app-5a3fe0?style=for-the-badge)](https://breakoutscan-web.vercel.app/dashboard)
[![API docs](https://img.shields.io/badge/API-interactive%20docs-067a50?style=for-the-badge)](https://codex-screener-production.up.railway.app/docs)

![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=nextdotjs)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.12-009688?style=flat-square&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/Postgres-Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-cache-DC382D?style=flat-square&logo=redis&logoColor=white)
![Tests](https://img.shields.io/badge/backend%20tests-343-067a50?style=flat-square)

**[The problem](#01--the-problem)** ·
**[The product](#02--the-product)** ·
**[Day to day](#03--how-it-fits-a-trading-day)** ·
**[Under the hood](#05--how-it-works)** ·
**[Where it stands](#06--where-it-stands)** ·
**[Limits](#07--what-it-does-not-do-read-this)** ·
**[Run it](#09--run-it-yourself)**

</div>

---

> **BreakoutScan is an informational tool.** It is not investment advice, a recommendation to buy or sell any security, or a trading system. Read [what it does not do](#07--what-it-does-not-do-read-this) before relying on anything it shows.

---

## 01 · The problem

Following the Indian market on your own usually means keeping several things open at once: a screener for scans, a charting site, a news feed, and a spreadsheet for fundamentals. Each covers one slice, and none of them tell you whether a move has actually *held*.

That costs the most between 09:15 and 09:45, when there are hundreds of stocks moving and only a few minutes to decide which ones deserve a look.

## 02 · The product

BreakoutScan puts the routine parts of that workflow in one place: **scan the NIFTY 500, watch breakouts confirm rather than just tick, check a chart, and read a news-driven shortlist**, then keep a watchlist of the names you follow.

<div align="center">

<img src="docs/assets/platform-tour.gif" alt="A 10-step tour of BreakoutScan: dashboard, sectors, screener, results, AI picks, chart, fundamentals, watchlist, alerts, dark mode" width="100%"/>

<sub>A tour of the live product (real data captured with the market closed, so it shows the last session). Watchlist and Alerts are signed-in screens, shown here with a demo list.</sub>

</div>

### What's in it

| | |
|---|---|
| **Dashboard** | Headline numbers, a breakout feed grouped by stock, market breadth, and a sector strip that expands into a gain-to-loss heatmap |
| **Screener** | 13 prebuilt scans over the NIFTY 500, a custom condition builder, results that open right under the scan you ran |
| **Breakout engine** | 12 trigger types that must *confirm* before they count, see [below](#the-breakout-engine) |
| **AI Picks** | News-driven intraday, weekly and monthly ideas with a confidence level, target, stop-loss and the headlines behind each |
| **Charts** | Quote bar plus an interactive chart with EMA, RSI, MACD and Bollinger overlays, and a BUY / HOLD / SELL read for the stock |
| **Fundamentals** | Screens for value, quality, low debt and income (P/E, P/B, ROE, D/E, dividend yield, market cap) |
| **Watchlist & Alerts** | Personal watchlist with live prices; per-stock breakout alerts, recorded to your history |
| **Phone & dark mode** | Full layout down to 320px, light by default, dark on request |

### Screens

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/dashboard.png" alt="Dashboard: KPI strip, breakout feed, market breadth"/><br/><sub><b>Dashboard.</b> Headline numbers first, then the feed. Rows are grouped by stock with the triggers that fired.</sub></td>
<td width="50%"><img src="docs/assets/screens/sectors.png" alt="Sector heatmap expanded"/><br/><sub><b>Sector strip → heatmap.</b> Collapsed it shows the leaders and laggards; expanded, every sector on a continuous green-to-red scale.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/screens/scan-results.png" alt="Screener results opening under the scan that was run"/><br/><sub><b>Screener.</b> Run a scan and the results appear directly beneath it, sortable, with company names and sectors.</sub></td>
<td width="50%"><img src="docs/assets/screens/ai-picks.png" alt="AI Picks with confidence, target and stop-loss"/><br/><sub><b>AI Picks.</b> Each idea carries confidence, a target, a stop-loss and the news it came from.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/screens/chart.png" alt="Chart page with quote bar, EMA and RSI"/><br/><sub><b>Chart.</b> Quote bar on top, then the chart with your indicators.</sub></td>
<td width="50%"><img src="docs/assets/screens/fundamentals.png" alt="Fundamentals screen using the Quality Large Caps preset"/><br/><sub><b>Fundamentals.</b> Preset screens or your own limits. Right-aligned figures so columns compare at a glance.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/assets/screens/watchlist.png" alt="Watchlist with live day range and volume"/><br/><sub><b>Watchlist</b> (demo list, live prices). Day range and volume per stock.</sub></td>
<td width="50%"><img src="docs/assets/screens/alerts.png" alt="Breakout alerts"/><br/><sub><b>Alerts</b> (demo alerts). Pick a stock and how often you want to hear about it.</sub></td>
</tr>
</table>

<div align="center">
<img src="docs/assets/screens/mobile-trio.png" alt="Phone layouts: dashboard, screener with the More menu open, AI picks" width="78%"/>
<br/><sub>The same product on a 390px phone: bottom navigation with a "More" menu, no horizontal scrolling.</sub>
</div>

<details>
<summary><b>Dark mode</b></summary>
<br/>
<img src="docs/assets/screens/dashboard-dark.png" alt="Dashboard in dark mode"/>
</details>

---

## 03 · How it fits a trading day

<div align="center">
<img src="docs/assets/day.svg" alt="A trading day in four phases and which parts of the app help in each" width="100%"/>
</div>

These are realistic routines, not promises of results. Each says what the tool gives you and where your own judgement still has to do the work.

<details open>
<summary><b>Before the open: a ten-minute prep</b></summary>

1. **Dashboard.** With the market closed the feed shows the *last confirmed session* and says so. See which stocks broke out, on which triggers.
2. **Sector strip.** Expand it to see which sectors led and lagged yesterday.
3. **AI Picks.** Skim the intraday list as a reading list. Every pick lists its sources, so you can open the headline and decide whether it still matters.
4. **Watchlist.** Check the names you already follow.

*What it gives you:* a shortlist to look at. *What it doesn't:* a reason to enter. That's still your call.
</details>

<details>
<summary><b>The first fifteen minutes: opening range</b></summary>

1. Run **ORB Breakout Long** and **Volume Spike (2×)** from the Screener.
2. Watch the dashboard feed. A breakout only appears once it has *held* through its confirmation window, which cuts down on one-tick fakes (though not on all of them).
3. Open the chart for two or three candidates and check the level it broke.

*Limit:* the live feed depends on the data source being up. The app tells you when it has fallen back or is stale.
</details>

<details>
<summary><b>During the session: keep an eye on a few names</b></summary>

- **Watchlist** shows live price, change, volume and day range for the stocks you follow.
- **Alerts** record a confirmed breakout for a stock you chose ("once", "every time" or "daily digest") to your alert history.
- On a **chart**, the AI read gives you a second opinion with the reasoning shown, useful as a prompt for your own research.

*Limit:* alerts are stored and visible in-app. Email / Telegram / push delivery is not built yet.
</details>

<details>
<summary><b>After the close: swing setups</b></summary>

- Run **Bullish EMA Crossover**, **Near 52-Week High**, **Bollinger Squeeze** and **Price Above SMA(200)** to build tomorrow's list.
- Build a **custom scan** when the prebuilt ones don't fit, e.g. RSI below 40 *and* close above EMA(50).
- Use the results as a starting list and then read the charts.
</details>

<details>
<summary><b>On the weekend: fundamentals</b></summary>

- The **Fundamentals** presets ("Low PE", "High ROE", "Low Debt", "High Dividend Yield", "Undervalued Growth", "Quality Large Caps") narrow the universe to a manageable list.
- Add your own limits (P/E, P/B, ROE, D/E, dividend yield, market cap) and filter by symbol.

*Limit:* the figures come from Yahoo Finance, an unofficial source. Some companies have missing values (shown as "–"). Verify anything that matters against filings.
</details>

---

## 04 · What's inside

### The screener

Thirteen prebuilt scans run over the NIFTY 500. Anything else can be built in the custom builder from RSI, EMA, MACD, Bollinger, ATR, ADX, volume and price conditions.

| Scan | What it looks for |
|---|---|
| RSI Oversold / Overbought | RSI(14) below 30 / above 70 |
| Bullish / Bearish EMA Crossover | EMA(9) above / below EMA(21) |
| Price Above / Below SMA(200) | Close above / below the 200-day average |
| Volume Spike (2×) | Volume more than twice the 20-period average |
| Bollinger Squeeze | Band width under 4%: volatility contracting |
| MACD Bullish / Bearish Cross | MACD line above / below its signal line |
| Near 52-Week High | Close within 5% of the 52-week high |
| ORB Breakout Long | Price above the opening-range high (first 15 minutes) |
| Bullish Engulfing | The candlestick reversal pattern |

### The breakout engine

A price poking through a level isn't a breakout yet. The engine watches twelve kinds of level and walks each one through a small state machine, and **only confirmed breakouts are stored**.

<div align="center">
<img src="docs/assets/lifecycle.svg" alt="Breakout lifecycle: armed, triggered, confirmed or failed; invalidated or expired" width="100%"/>
</div>

<details>
<summary><b>The 12 triggers and how each one confirms</b></summary>
<br/>

| Trigger | The level it watches | Confirms after | Watch expires |
|---|---|---|---|
| Previous day high / low | Yesterday's extremes | 1 × 5-min bar | End of day |
| Opening range (ORB) | High / low of the first 15 minutes | 1 × 5-min bar | End of day |
| 52-week high / low | 252-day extremes | 2 × 15-min bars | 20 bars |
| Donchian channel | Highest high / lowest low of recent bars | 2 × 15-min bars | 20 bars |
| NR4 / NR7 | Narrowest-range bar of the last 4 / 7 | 1 × 15-min bar | End of day |
| Inside bar | Range of the bar before | 1 × 15-min bar | End of day |
| Volume breakout | Volume above a multiple of its average | 1 × 5-min bar | End of day |
| VWAP | Session VWAP reclaimed / lost | 1 × 5-min bar | End of day |
| EMA cross | EMA(9) vs EMA(21) | 1 × 15-min bar | 10 bars |
| MACD cross | MACD vs signal line | 1 × 15-min bar | 10 bars |
| Bollinger squeeze release | Squeeze ending | 1 × 15-min bar | 10 bars |

A confirmed breakout that reverses through its level afterwards is recorded as **FAILED**, so false breakouts are counted, not silently dropped.
</details>

#### Breakout DNA

Every confirmed breakout is scored from 0 to 100 in six visible parts, not one opaque number.

<div align="center">
<img src="docs/assets/dna.svg" alt="Breakout DNA score: volume 25, trend 20, distance 15, momentum 15, volatility 15, confirmation speed 10" width="100%"/>
</div>

> **Honest status:** the score is computed and stored with each confirmed breakout and returned by the API (which can filter by minimum score). **The dashboard doesn't display it yet.**

### AI Picks and the per-stock call

- **AI Picks** reads about 40 recent market headlines (Google News RSS) and asks **Gemini 3.5 Flash Lite** for intraday, weekly and monthly ideas: BUY or SELL, a confidence level, a target %, a stop-loss %, and the sources behind each.
- The **chart-page call** (BUY / HOLD / SELL with reasoning) uses **Groq**, with a model fallback list, because providers retire models.
- Both run on **free-tier API keys**, so they can be rate-limited or slow. The AI reads headlines and indicators, not company filings, and it can be wrong. Treat it as a reading list.

### Sectors, regime, patterns

Sector performance is computed from live prices across 56 sectors. The API also exposes a simple market-regime read (trending, choppy, high volatility). The engine includes detectors for candlestick and chart-structure patterns (triangles, flags, double tops and bottoms, head and shoulders, cup and handle, Darvas boxes), though only *Bullish Engulfing* is exposed as a prebuilt scan today.

---

## 05 · How it works

<div align="center">
<img src="docs/assets/pipeline.svg" alt="Data flow: Upstox and NSE feeds and Yahoo Finance into the FastAPI engine, then Redis and Postgres, then the Next.js web app" width="100%"/>
</div>

**Resilience by design.** The live feed is Upstox's V3 WebSocket. If it stalls, a failover controller switches to polling NSE, and the breakout engine reads from the shared price and candle store rather than from either feed directly, so signals keep working through a switch. Redis is a cache that rebuilds itself. When the market is closed the engine idles instead of polling, and the app shows the last confirmed session, labelled as such.

<details>
<summary><b>Stack</b></summary>
<br/>

| Layer | What's used |
|---|---|
| **Web** | Next.js 15 (App Router), React 19, Tailwind CSS 3, TanStack Query and Table, Framer Motion, Recharts, TradingView's chart widget |
| **API** | FastAPI on Python 3.12, SQLAlchemy 2 (async) with Alembic migrations, pandas / pandas-ta, WebSockets |
| **Data** | Postgres (Supabase), Redis, Upstox V3 (live), NSE polling (fallback), Yahoo Finance (history, fundamentals) |
| **Auth** | Firebase Auth (Google sign-in); the API verifies OIDC tokens by configuration, and Supabase tokens are still accepted |
| **AI** | Gemini (AI Picks), Groq (per-stock call) |
| **Hosting** | Vercel (web), Railway (API and Redis), Supabase (database) |

</details>

**Design system.** The interface follows a small "Ledger" system: hairline panels, one type scale, tabular monospaced numbers, green and red *only* for price direction, and one accent colour for interactive state. It was audited for contrast, labels and touch targets across light and dark at 320–1440px.

---

## 06 · Where it stands

|  |  |
|---|---|
| **Status** | Live in production. Built and maintained by one developer. |
| **Coverage** | NIFTY 500 · 13 prebuilt scans · 12 breakout triggers · 56 sectors |
| **Automated tests** | 343 backend tests (indicators, scan DSL, breakout state machine, auth, data retention, API routes). The frontend has type-checking and a production build, but **no automated unit tests yet**. |
| **Last release check** | Type-check and production build, plus an automated browser sweep of every route at 3 widths in light and dark (contrast, overflow, labels, console errors) and a click-through of every control. |
| **Running cost** | The API and Redis run on a paid Railway plan; the web app, database, auth and AI keys use free tiers. The database needed [egress and retention work](docs/FREE_STACK_MIGRATION.md) to stay inside the free plan. |
| **Users** | No usage numbers are published, because none are tracked. |

## 07 · What it does *not* do (read this)

Being clear about limits matters more than the feature list.

- **It doesn't place orders**, track a portfolio, or backtest a strategy.
- **It isn't advice.** Scans are rules of thumb and AI output is a model's reading of headlines. Both can be wrong.
- **Data is only as good as its sources.** Yahoo Finance and NSE polling are unofficial and can throttle or break. The Upstox live feed needs valid API credentials. Prices can lag or go stale. It's not built for high-frequency use.
- **Fundamentals are incomplete.** Some companies lack ROE, debt or dividend figures.
- **Alerts don't send anything yet.** Confirmed breakouts are recorded for the stocks you chose and shown in-app. Email, Telegram and push delivery aren't built, though the settings for them exist in the database. There are no price or RSI *threshold* alerts either.
- **The Breakout DNA score isn't shown in the UI yet** (see above).
- **No options data.** Nothing on option chains, open interest or PCR.
- **When the market is closed**, the dashboard shows the last confirmed session, not live activity.
- **The native phone app is an early scaffold**, not a released product. The web app is what works on a phone today.
- **No license has been chosen yet.**

## 08 · What's next

Honest gaps, roughly in the order they'd help a daily user:

1. Show the **Breakout DNA score** in the feed and let you sort by it.
2. **Deliver alerts** (email, Telegram, push) instead of only recording them.
3. **Threshold alerts** on price and indicators, alongside breakout alerts.
4. **Save custom scans** and re-run them.
5. **Replay a scan on past sessions** to see how often it would have caught a good move (design started, not built).
6. A proper frontend test suite.

---

## 09 · Run it yourself

You'll need Python 3.12, Node 20+, and a Postgres and a Redis. The quickest way to get the two datastores is the compose file:

```bash
git clone https://github.com/iamadarsha/breakoutscan.git
cd breakoutscan
cp .env.example .env                  # then fill in what you have (notes below)
docker compose up -d postgres redis  # Postgres on :5432, Redis on :6379
```

```bash
# API  (http://localhost:8001 · docs at /docs)
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql+asyncpg://breakoutscan:breakoutscan@localhost:5432/breakoutscan"
export REDIS_URL="redis://localhost:6379/0"
alembic upgrade head                  # create the tables
uvicorn app.main:app --reload --port 8001
```

```bash
# Web  (http://localhost:3000)
cd apps/web
npm install
INTERNAL_API_URL=http://localhost:8001 npm run dev   # the web app proxies /api to the API (no CORS setup needed)
```

<details>
<summary><b>What you need to provide, and what works without it</b></summary>
<br/>

The UI loads with nothing configured, but data depends on what you provide. (For live WebSocket prices in the browser, also set `NEXT_PUBLIC_WS_URL=ws://localhost:8001`; without it the app falls back to polling.)

- **Live prices:** Upstox API credentials. An Analytics Token is free and read-only, see [`docs/UPSTOX_ONBOARDING.md`](docs/UPSTOX_ONBOARDING.md). Without it the NSE fallback is used.
- **AI Picks and the per-stock call:** `GEMINI_API_KEY` and `GROQ_API_KEY` (both have free tiers).
- **Sign-in, watchlist, alerts:** a Firebase (or Supabase) project. The auth settings are in [`docs/FREE_STACK_MIGRATION.md`](docs/FREE_STACK_MIGRATION.md).
- `.env.example` still lists Supabase variables from an earlier setup; the migration guide above describes the current one.
- `docker compose up --build` also defines the API and web containers. I couldn't re-test that full-stack path when writing this, so treat the manual route above as the reference.

**Checks**

```bash
cd apps/api && pytest                              # 343 tests
cd apps/web && npx tsc --noEmit && npm run build
```

</details>

## Repository map

```
breakoutscan/
├── apps/
│   ├── api/                FastAPI service
│   │   └── app/
│   │       ├── api/routes/     REST endpoints (screener, breakouts, market, alerts, …)
│   │       ├── market/         feed pipeline, candles, indicators, failover, regime
│   │       ├── breakouts/      12 triggers, state machine, DNA scoring
│   │       ├── screener/dsl/   scan language: parser, validator, evaluator
│   │       ├── patterns/       candlestick + structural patterns
│   │       ├── services/       AI, fundamentals, retention, Yahoo/NSE clients
│   │       └── tests/          343 tests
│   ├── web/                Next.js app (dashboard, screener, charts, …)
│   ├── mobile/             Expo app (early scaffold)
│   └── ios/                native iOS wrapper (early)
├── docs/                   architecture notes, migration guide, provider matrix
└── docker-compose.yml      local Postgres + Redis + API + web
```

**More reading:** [Free-stack & migration guide](docs/FREE_STACK_MIGRATION.md) · [Data provider matrix](docs/DATA_PROVIDER_MATRIX.md) · [Architecture audit](docs/ARCHITECTURE_AUDIT.md) · [Security remediation](docs/SECURITY_REMEDIATION.md) · [Upstox onboarding](docs/UPSTOX_ONBOARDING.md)

---

<div align="center">
<sub>Made by <a href="https://www.instagram.com/iamadarsha/">@iamadarsha</a> · <a href="https://github.com/iamadarsha/breakoutscan/issues">Report a bug</a> · Not investment advice</sub>
</div>

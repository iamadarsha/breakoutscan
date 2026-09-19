# BreakoutScan — Interactive Mind Map & Workflow (for Figma)

> **How to import into Figma**: Copy each Mermaid code block into [Mermaid Chart Figma Plugin](https://www.figma.com/community/plugin/1365764431157) or use the live edit links below to export as SVG/PNG and paste into FigJam.

---

## 1. Project Architecture Mind Map

```mermaid
mindmap
  root((BreakoutScan))
    **Frontend**
      Next.js 15 + React 19
        Dashboard
          Stat Cards
          Index Ticker Bar
          Breadth Donut
          Breakout Feed
        AI Picks Page
          Intraday 5 picks
          Weekly 5 picks
          Monthly 5 picks
          Live Price Streaming
            WebSocket + REST fallback
        Screener
          13 Prebuilt Scans (stable)
          Custom Scan Builder
        Charts
          TradingView Widget
          Candlestick + Volume
          RSI / MACD / BB / EMA
        Watchlist
          Add/Remove Stocks
          Live Prices
        Alerts
        Fundamentals
        Settings
      Styling
        Tailwind CSS
        Dark Terminal Theme
        Framer Motion
        Dark/Light Theme Toggle
      State
        React Query
        Zustand
      Deploy: Railway
    **Backend API**
      FastAPI + Python 3.12
        Routes
          /api/ai-suggestions
          /api/prices
          /api/market
          /api/screener
          /api/watchlist
          /api/alerts
          /api/stocks
          /api/fundamentals
          /api/company
          /auth/upstox
        Services
          AI Suggestions 3-Layer
            Layer 1: RSS + Technical Scoring (zero API)
            Layer 2: Gemini 3.1 Flash Lite
            Layer 3: Groq + xAI
          NSE Poller 30s cycle
          Yahoo Finance OHLCV
          Indicator Engine
          Screener Engine
          Prebuilt Scans
        WebSocket
          Price Updates
          Scan Progress
          Alert Triggers
      Deploy: Railway
    **Data Layer**
      Redis Cache
        461 Price Keys
        380 Indicator Keys
        AI Suggestions Cache
        Market Indices
        Scan Results
      Supabase PostgreSQL
        Stocks Table
        Watchlist
        Alerts
        OHLCV History
      Seed Data
        nifty500_seed.json
        500 NSE Symbols
    **External APIs**
      Stock Data
        NSE via indianapi.in
        Yahoo Finance
        Upstox WebSocket
      AI / LLM
        Google Gemini
        Groq Llama 3.3
        xAI Grok
      News RSS 10 Feeds
        Google News x5
        Moneycontrol x2
        Economic Times
        Mint
        Business Standard
      Wikipedia
    **iOS App**
      SwiftUI WebView
      Bundle: com.codexscreener.app
      Loads Railway URL
    **DevOps**
      GitHub Repo
      Railway Auto-Deploy
      Railway Frontend Deploy
      Docker Compose Local
```

---

## 2. Project Build Workflow (Step-by-Step Phases)

```mermaid
flowchart TD
    subgraph Phase1["Phase 1: Foundation"]
        A1[Project Setup<br/>Monorepo Structure] --> A2[FastAPI Backend<br/>Python 3.12]
        A2 --> A3[Next.js 15 Frontend<br/>React 19 + TypeScript]
        A3 --> A4[Docker Compose<br/>PostgreSQL + Redis]
        A4 --> A5[Supabase Setup<br/>Database Schema]
    end

    subgraph Phase2["Phase 2: Data Pipeline"]
        B1[NSE Poller Service<br/>30s poll cycle] --> B2[Redis Cache Layer<br/>Price + Indicator keys]
        B2 --> B3[Yahoo Finance<br/>Historical OHLCV]
        B3 --> B4[Indicator Engine<br/>RSI, EMA, MACD, BB]
        B4 --> B5[Nifty 500 Seed Data<br/>500 stock metadata]
    end

    subgraph Phase3["Phase 3: Core Features"]
        C1[Dashboard<br/>Stat Cards + Indices] --> C2[Screener Engine<br/>13 Prebuilt Scans]
        C2 --> C3[Chart Page<br/>Lightweight Charts v5]
        C3 --> C4[Watchlist<br/>Add/Remove + Live Prices]
        C4 --> C5[Alerts System<br/>Price Triggers]
    end

    subgraph Phase4["Phase 4: AI Stock Picker"]
        D1[RSS + Technical Scoring<br/>Zero API Layer 1] --> D2[Gemini 3.1 Flash Lite<br/>Layer 2 AI]
        D2 --> D3[RSS Feed Parser<br/>10 News Sources]
        D3 --> D4[Technical Scoring Engine<br/>Layer 3 Zero-API]
        D4 --> D5[3-Layer Fallback Chain<br/>Always Returns Picks]
        D5 --> D6[Background Generation<br/>Instant GET Response]
    end

    subgraph Phase5["Phase 5: Deployment"]
        E1[Railway Backend<br/>Auto-deploy from main] --> E2[Railway Frontend<br/>Next.js SSR]
        E2 --> E3[Redis on Railway<br/>461 prices cached]
        E3 --> E4[iOS SwiftUI App<br/>WebView Wrapper]
    end

    subgraph Phase6["Phase 6: Production Hardening"]
        F1[Gemini Thread Executor<br/>SDK blocks event loop] --> F2[Redis Pipeline Reads<br/>841 keys in 2 trips]
        F2 --> F3[Global Timeouts<br/>Every layer protected]
        F3 --> F4[Mobile UI Fixes<br/>iPhone viewport + touch]
        F4 --> F5[Debug Endpoint<br/>/api/ai-suggestions/debug]
    end

    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> Phase5
    Phase5 --> Phase6

    style Phase1 fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style Phase2 fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Phase3 fill:#0f3460,stroke:#533483,color:#e0e0e0
    style Phase4 fill:#533483,stroke:#e94560,color:#e0e0e0
    style Phase5 fill:#e94560,stroke:#ff6b6b,color:#fff
    style Phase6 fill:#2d6a4f,stroke:#40916c,color:#fff
```

---

## 3. AI Stock Picker — 3-Layer Fallback Flow

```mermaid
flowchart LR
    User[User Opens Website] --> GET["GET /api/ai-suggestions"]
    GET -->|Cache Hit| Return[Return 15 Picks Instantly]
    GET -->|Cache Miss| Pending["Return pending + Background Task"]

    Pending --> RSS["Fetch 10 RSS Feeds"]
    RSS --> Market["Load Market Summary"]

    Market --> L1{"Layer 1: Technical"}
    L1 -->|Success| Cache["Cache in Redis"]
    L1 -->|Fail| L2{"Layer 2: Gemini"}
    L2 -->|Success| Cache
    L2 -->|Fail| L3{"Layer 3: Groq"}

    L3 --> Score["Score 461 Stocks"]
    Score --> Pick["Top 5 x 3 Timeframes"]
    Pick --> Cache
    Cache --> Return

    style L1 fill:#4285f4,color:#fff
    style L2 fill:#f97316,color:#fff
    style L3 fill:#22c55e,color:#fff
```

---

## 4. Data Flow Architecture

```mermaid
flowchart TB
    subgraph Sources["External Data Sources"]
        NSE[NSE via indianapi.in]
        YF[Yahoo Finance]
        RSS[10 RSS News Feeds]
        Wiki[Wikipedia API]
        Gemini[Google Gemini AI]
        Groq[Groq Llama 3.3]
    end

    subgraph Backend["FastAPI Backend - Railway"]
        Poller[NSE Poller<br/>Every 30s]
        YFS[Yahoo Finance Service<br/>OHLCV + Indicators]
        AIS[AI Suggestions Service<br/>3-Layer Engine]
        SE[Screener Engine<br/>13 Scans]
        WS[WebSocket Manager]
    end

    subgraph Cache["Redis Cache - Railway"]
        Prices["price:{SYMBOL}<br/>461 keys, 300s TTL"]
        Indicators["ind:{SYMBOL}:1d<br/>380 keys, 600s TTL"]
        AICache["ai:suggestions<br/>TTL until 9AM next day"]
        MktData["market:indices<br/>market:breadth"]
    end

    subgraph DB["Supabase PostgreSQL"]
        Stocks[stocks table]
        WL[watchlist table]
        Alerts[alerts table]
        OHLCV[ohlcv table]
    end

    subgraph Frontend["Next.js Frontend - Railway"]
        Dashboard[Dashboard Page]
        AIPicks[AI Picks Page]
        Screener[Screener Page]
        Charts[Charts Page]
        Watchlist[Watchlist Page]
    end

    NSE --> Poller
    YF --> YFS
    RSS --> AIS
    Gemini --> AIS
    Groq --> AIS
    Wiki --> Backend

    Poller --> Prices
    Poller --> MktData
    YFS --> Indicators
    YFS --> OHLCV
    AIS --> AICache
    SE --> Indicators

    Prices --> Frontend
    AICache --> AIPicks
    MktData --> Dashboard
    Indicators --> Charts
    DB --> Watchlist
```

---

## How to Use in Figma

### Option 1: Mermaid Chart Plugin (Recommended)
1. Install [Mermaid Chart Plugin](https://www.figma.com/community/plugin/1365764431157) in Figma
2. Open plugin → paste any Mermaid code block above
3. Click "Render" → diagram appears as editable Figma shapes

### Option 2: SVG Import
1. Visit [Mermaid Live Editor](https://mermaid.live)
2. Paste any code block above
3. Download as SVG
4. Import SVG into Figma → all shapes are editable

### Option 3: FigJam
1. Open FigJam (Figma's whiteboard tool)
2. Use the Mermaid plugin or paste SVG exports
3. Add sticky notes, arrows, and annotations

---

**Created**: March 16, 2026
**Tool**: Claude Code + Mermaid.js

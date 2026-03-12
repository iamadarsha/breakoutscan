"""
Equifidy AI Stock Suggestions Service.
Uses Google News RSS + Gemini 2.5 Flash to generate AI-powered stock picks.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timedelta
from typing import Optional

import feedparser
import httpx
import structlog
import redis.asyncio as aioredis

from config import settings

log = structlog.get_logger(__name__)

# ── Redis keys ────────────────────────────────────────────────────────────────
REDIS_KEY_SUGGESTIONS = "ai:suggestions"
REDIS_KEY_LAST_REFRESH = "ai:last_refresh"
REDIS_TTL = 60 * 60 * 12  # 12 hours


# ── News Gathering (Google News RSS) ─────────────────────────────────────────

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

NEWS_QUERIES = [
    "Indian stock market today",
    "NSE BSE stocks breakout",
    "India sector rotation stocks",
    "Nifty stocks buy recommendation",
    "Indian stocks momentum rally",
    "India quarterly results earnings",
]


async def fetch_news(max_articles: int = 30) -> list[dict]:
    """Fetch recent Indian stock market news from Google News RSS."""
    articles = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in NEWS_QUERIES:
            try:
                url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; EquifidyBot/1.0)"
                })
                if resp.status_code != 200:
                    continue

                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:5]:
                    published = ""
                    if hasattr(entry, "published"):
                        published = entry.published
                    articles.append({
                        "title": entry.get("title", ""),
                        "source": entry.get("source", {}).get("title", ""),
                        "published": published,
                        "link": entry.get("link", ""),
                    })
            except Exception as e:
                log.warning("news_fetch_failed", query=query, error=str(e))
                continue

    # Deduplicate by title
    seen = set()
    unique = []
    for a in articles:
        key = a["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique[:max_articles]


# ── Gemini AI Analysis ────────────────────────────────────────────────────────

def _build_prompt(news_articles: list[dict], market_data_summary: str) -> str:
    """Build the Gemini prompt for stock analysis."""
    news_text = ""
    for i, a in enumerate(news_articles, 1):
        news_text += f"{i}. [{a['source']}] {a['title']}\n"

    return f"""You are an expert Indian stock market analyst for Equifidy, a stock screening platform.
Analyze the following market news and data, then suggest stock picks for three timeframes.

## Current Market News (India)
{news_text}

## Market Data Summary
{market_data_summary}

## Your Task
Provide exactly 5 stock suggestions for each of these 3 categories:

### 1. INTRADAY PICKS (for today's trading session)
- Stocks with momentum, volume surge, or breakout patterns
- Focus on liquid large/mid-cap stocks
- Entry within ±1% of current price

### 2. WEEKLY PICKS (1-5 day swing trades)
- Stocks with technical breakout potential
- Sector rotation plays
- Earnings momentum plays

### 3. MONTHLY PICKS (2-4 week positional trades)
- Fundamental + technical convergence
- Sector tailwinds
- Strong chart patterns

## Response Format
Return ONLY valid JSON (no markdown, no explanation outside JSON):
{{
  "intraday": [
    {{
      "symbol": "RELIANCE",
      "company_name": "Reliance Industries Ltd",
      "action": "BUY",
      "confidence": 85,
      "target_pct": 2.5,
      "stop_loss_pct": 1.0,
      "reasoning": "Strong volume breakout above 20-day EMA with sector tailwind from oil prices",
      "tags": ["Breakout", "Volume Surge"]
    }}
  ],
  "weekly": [...],
  "monthly": [...]
}}

Rules:
- Use ONLY NSE-listed Indian stocks (use NSE ticker symbols like RELIANCE, TCS, INFY, HDFCBANK, etc.)
- confidence: 60-95 (integer percentage)
- target_pct: expected upside % (positive number)
- stop_loss_pct: downside risk % (positive number)
- action: "BUY" or "SELL"
- tags: 1-3 short tags per pick
- reasoning: 1-2 sentence explanation
- Be specific and actionable
- Diversify across sectors
"""


async def _get_market_data_summary(redis: aioredis.Redis) -> str:
    """Build a brief market data summary from Redis cache."""
    summary_parts = []

    try:
        # Get Nifty 50 index data
        nifty_data = await redis.get("index:NIFTY 50")
        if nifty_data:
            nifty = json.loads(nifty_data)
            summary_parts.append(
                f"Nifty 50: {nifty.get('ltp', 'N/A')} "
                f"({nifty.get('change_pct', 0):+.2f}%)"
            )

        # Get Bank Nifty
        bank_data = await redis.get("index:NIFTY BANK")
        if bank_data:
            bank = json.loads(bank_data)
            summary_parts.append(
                f"Bank Nifty: {bank.get('ltp', 'N/A')} "
                f"({bank.get('change_pct', 0):+.2f}%)"
            )

        # Get top gainers/losers from LTP cache
        top_movers = []
        keys = await redis.keys("ltp:*")
        if keys:
            pipe = redis.pipeline()
            for k in keys[:200]:
                pipe.get(k)
            values = await pipe.execute()

            stocks = []
            for k, v in zip(keys[:200], values):
                if v:
                    try:
                        d = json.loads(v)
                        symbol = k.decode() if isinstance(k, bytes) else k
                        symbol = symbol.replace("ltp:", "")
                        change_pct = d.get("change_pct", 0)
                        stocks.append((symbol, change_pct))
                    except Exception:
                        continue

            stocks.sort(key=lambda x: x[1], reverse=True)
            if stocks:
                gainers = stocks[:5]
                losers = stocks[-5:]
                summary_parts.append("Top Gainers: " + ", ".join(f"{s}({c:+.1f}%)" for s, c in gainers))
                summary_parts.append("Top Losers: " + ", ".join(f"{s}({c:+.1f}%)" for s, c in losers))
    except Exception as e:
        log.warning("market_summary_failed", error=str(e))

    return "\n".join(summary_parts) if summary_parts else "Market data unavailable — use news and general market knowledge."


async def generate_suggestions(redis: aioredis.Redis, force: bool = False) -> dict:
    """Generate AI stock suggestions using Gemini."""
    if not settings.gemini_api_key:
        log.warning("gemini_api_key_not_configured")
        return {"error": "Gemini API key not configured", "suggestions": None}

    # Check cache (unless forced)
    if not force:
        cached = await redis.get(REDIS_KEY_SUGGESTIONS)
        if cached:
            return json.loads(cached)

    log.info("ai_suggestions_generating")
    start = time.time()

    # 1. Gather news
    news = await fetch_news()
    log.info("ai_news_gathered", count=len(news))

    # 2. Get market data summary
    market_summary = await _get_market_data_summary(redis)

    # 3. Build prompt
    prompt = _build_prompt(news, market_summary)

    # 4. Call Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text.strip()

        # Parse JSON (handle markdown code blocks if present)
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        suggestions = json.loads(raw_text)

    except json.JSONDecodeError as e:
        log.error("ai_json_parse_failed", error=str(e), raw=raw_text[:200])
        return {"error": "Failed to parse AI response", "suggestions": None}
    except Exception as e:
        log.error("ai_gemini_call_failed", error=str(e))
        return {"error": f"Gemini API error: {str(e)}", "suggestions": None}

    elapsed = time.time() - start

    # 5. Build response
    result = {
        "suggestions": suggestions,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generation_time_ms": int(elapsed * 1000),
        "news_count": len(news),
        "model": "gemini-2.5-flash",
        "news_headlines": [a["title"] for a in news[:10]],
    }

    # 6. Cache in Redis
    await redis.set(REDIS_KEY_SUGGESTIONS, json.dumps(result), ex=REDIS_TTL)
    await redis.set(REDIS_KEY_LAST_REFRESH, datetime.utcnow().isoformat(), ex=REDIS_TTL)

    log.info("ai_suggestions_generated", elapsed_ms=int(elapsed * 1000), picks=sum(
        len(suggestions.get(k, [])) for k in ["intraday", "weekly", "monthly"]
    ))

    return result


async def get_cached_suggestions(redis: aioredis.Redis) -> Optional[dict]:
    """Get cached AI suggestions from Redis."""
    cached = await redis.get(REDIS_KEY_SUGGESTIONS)
    if cached:
        return json.loads(cached)
    return None

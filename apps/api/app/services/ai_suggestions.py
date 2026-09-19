"""AI-powered stock suggestions with 3-layer fallback:

Layer 1: Gemini 3.5 Flash Lite (primary + backup key, 500 RPD) — reads the
         fetched RSS headlines + live market data and reasons about picks.
         This is the primary path: it runs first, every time keys are
         configured, not just when something else fails.
Layer 2: Groq Llama 3.3 70B / xAI Grok — alternative LLM providers, used
         only if Gemini is unavailable or exhausted.
Layer 3: RSS-headline + technical-scoring engine (zero API dependency) —
         an honest last-resort fallback for when no AI provider responds
         at all, not a substitute for AI reasoning.
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import re
from datetime import datetime, timedelta
from typing import Any

from app.utils.time import IST, now_ist

log = logging.getLogger(__name__)

REDIS_KEY = "ai:suggestions"

# Per-stage timeout budget. These are sized so the WORST case (every layer
# times out and falls all the way through to the technical fallback) still
# finishes comfortably inside the outer timeout both HTTP callers and the
# scheduled morning job wrap this function in (see AI_SUGGESTIONS_OUTER_TIMEOUT
# in the route module and main.py's scheduler job) — previously these numbers
# were picked independently per layer and could sum past the outer timeout,
# silently truncating a slow-but-otherwise-successful AI response.
RSS_FETCH_TIMEOUT = 15
MARKET_SUMMARY_TIMEOUT = 8
GEMINI_PER_KEY_TIMEOUT = 15
GEMINI_LAYER_TIMEOUT = 32  # 2 keys × 15s + overhead margin
GROQ_TIMEOUT = 15
XAI_TIMEOUT = 15
ALT_AI_LAYER_TIMEOUT = 32  # groq + xai × 15s + overhead margin
TECHNICAL_LAYER_TIMEOUT = 10
# Worst case: 15 + 8 + 32 + 32 + 10 = 97s. Callers should wrap with >= 110s.

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=indian+stock+market+NSE&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=nifty+sensex+breakout&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=india+equity+market+today&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=india+broker+report+stock+recommendation&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=motilal+oswal+OR+icici+direct+OR+hdfc+securities+stock+pick&hl=en-IN&gl=IN&ceid=IN:en",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.moneycontrol.com/rss/stocksinnews.xml",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://www.business-standard.com/rss/markets-106.rss",
]

# ---------------------------------------------------------------------------
# Nifty 500 symbol lookup (loaded once from seed JSON)
# ---------------------------------------------------------------------------
_SEED_PATH = pathlib.Path(__file__).resolve().parents[2] / "data" / "nifty500_seed.json"
_SYMBOL_META: dict[str, dict[str, str]] = {}
_NAME_KEYWORDS: dict[str, str] = {}  # lowercase keyword -> symbol

def _ensure_symbol_lookup() -> None:
    """Load Nifty 500 metadata once.

    A company-name keyword (e.g. "power", "steel", "motors") that belongs
    to more than one company is genuinely ambiguous — matching a headline
    on it would silently attribute news to the wrong stock. Such keywords
    are dropped entirely rather than resolved by last-symbol-wins, which
    is what a plain dict assignment would do.
    """
    global _SYMBOL_META, _NAME_KEYWORDS
    if _SYMBOL_META:
        return
    try:
        log.info("loading nifty500_seed.json from %s (exists=%s)", _SEED_PATH, _SEED_PATH.exists())
        data = json.loads(_SEED_PATH.read_text())
        keyword_candidates: dict[str, set[str]] = {}
        skip_words = {"limited", "ltd", "india", "industries", "the", "and", "pvt", "corp"}
        for s in data:
            sym = s["symbol"]
            _SYMBOL_META[sym] = {
                "name": s.get("company_name", sym),
                "sector": s.get("sector", ""),
            }
            # Symbol itself is unambiguous by construction (one row per symbol).
            keyword_candidates.setdefault(sym.upper(), set()).add(sym)
            # Meaningful company-name words (>3 chars, skip common suffixes) —
            # collected as candidates first so collisions can be detected.
            for word in s.get("company_name", "").split():
                w = word.strip(".,()").lower()
                if len(w) > 3 and w not in skip_words:
                    keyword_candidates.setdefault(w.upper(), set()).add(sym)

        ambiguous = 0
        for keyword, symbols in keyword_candidates.items():
            if len(symbols) == 1:
                _NAME_KEYWORDS[keyword] = next(iter(symbols))
            else:
                ambiguous += 1
        log.info(
            "symbol_lookup_loaded symbols=%d keywords=%d dropped_ambiguous=%d",
            len(_SYMBOL_META), len(_NAME_KEYWORDS), ambiguous,
        )
    except Exception as e:
        log.warning("failed to load nifty500_seed.json: %s", e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_trading_day(dt: datetime | None = None) -> bool:
    if dt is None:
        dt = now_ist()
    return dt.weekday() < 5


def get_next_trading_day_9am() -> datetime:
    dt = now_ist().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while dt.weekday() > 4:
        dt += timedelta(days=1)
    return dt


def _compute_ttl_seconds() -> int:
    now = now_ist()
    next_9am = get_next_trading_day_9am()
    delta = (next_9am - now).total_seconds()
    return max(int(delta), 21600)


def _has_picks(picks: dict[str, list]) -> bool:
    """Check if picks dict has any actual stock picks."""
    return sum(len(v) for k, v in picks.items() if k in ("intraday", "weekly", "monthly")) > 0


def _normalize_confidence(picks: list) -> list:
    for pick in picks:
        c = pick.get("confidence", 5)
        if isinstance(c, (int, float)) and c > 10:
            pick["confidence"] = max(1, min(10, round(c / 10)))
    return picks


def _parse_ai_response(text: str) -> dict[str, list] | None:
    """Parse JSON from AI model response, handling markdown fences."""
    text = text.strip()
    fence_match = re.match(r"^```(?:\w+)?\s*\n(.*?)```\s*$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict) and all(k in parsed for k in ("intraday", "weekly", "monthly")):
        for key in ("intraday", "weekly", "monthly"):
            parsed[key] = _normalize_confidence(parsed.get(key, []))
        return parsed
    if isinstance(parsed, list):
        parsed = _normalize_confidence(parsed)
        return {"intraday": parsed[:5], "weekly": parsed[5:10], "monthly": parsed[10:15]}
    return None


# ---------------------------------------------------------------------------
# RSS headlines
# ---------------------------------------------------------------------------
async def _fetch_news_headlines() -> list[dict[str, str]]:
    import feedparser
    import httpx

    headlines: list[dict[str, str]] = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BreakoutScan/1.0)"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        for url in RSS_FEEDS:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    source_name = feed.feed.get("title", "News")
                    for entry in feed.entries[:10]:
                        title = entry.get("title", "")
                        if not title:
                            continue
                        headlines.append({
                            "title": title,
                            "url": entry.get("link", ""),
                            "source": source_name,
                            "published_at": entry.get("published", ""),
                        })
            except Exception as e:
                log.warning("rss_fetch_failed url=%s error=%s", url, e)

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for h in headlines:
        if h["title"] not in seen:
            seen.add(h["title"])
            unique.append(h)
    return unique[:40]


async def _get_market_summary() -> str:
    from app.services.redis_cache import get_json, get_redis

    summary_parts: list[str] = []
    try:
        indices = await get_json("market:indices")
        if indices:
            summary_parts.append("=== Market Indices ===")
            if isinstance(indices, list):
                for idx in indices:
                    name = idx.get("name", idx.get("symbol", ""))
                    ltp = idx.get("ltp", idx.get("last", ""))
                    chg = idx.get("change_pct", idx.get("pChange", ""))
                    summary_parts.append(f"  {name}: {ltp} ({chg}%)")
            elif isinstance(indices, dict):
                for name, data in indices.items():
                    if isinstance(data, dict):
                        ltp = data.get("ltp", data.get("last", ""))
                        chg = data.get("change_pct", data.get("pChange", ""))
                        summary_parts.append(f"  {name}: {ltp} ({chg}%)")
    except Exception as e:
        log.warning("failed to read market indices: %s", e)

    try:
        r = await get_redis()
        price_keys = []
        async for key in r.scan_iter(match="price:*", count=500):
            price_keys.append(key)

        stocks: list[dict[str, Any]] = []
        for pk in price_keys[:500]:
            try:
                raw = await r.get(pk)
                if not raw:
                    continue
                data = json.loads(raw) if isinstance(raw, str) else {}
                if data:
                    symbol = data.get("symbol", pk.replace("price:", ""))
                    change_pct = float(data.get("change_pct", data.get("pChange", 0)) or 0)
                    ltp = data.get("ltp", data.get("last", data.get("close", "")))
                    stocks.append({"symbol": symbol, "change_pct": change_pct, "ltp": ltp})
            except Exception:
                continue

        if stocks:
            stocks.sort(key=lambda x: x["change_pct"], reverse=True)
            summary_parts.append("\n=== Top 5 Gainers ===")
            for s in stocks[:5]:
                summary_parts.append(f"  {s['symbol']}: LTP {s['ltp']} ({s['change_pct']:+.2f}%)")
            summary_parts.append("\n=== Top 5 Losers ===")
            for s in stocks[-5:]:
                summary_parts.append(f"  {s['symbol']}: LTP {s['ltp']} ({s['change_pct']:+.2f}%)")
    except Exception as e:
        log.warning("failed to read price data: %s", e)

    return "\n".join(summary_parts) if summary_parts else "Market data unavailable."


# ---------------------------------------------------------------------------
# Shared AI prompt
# ---------------------------------------------------------------------------
def _build_ai_prompt(headlines: list[dict[str, str]], market_summary: str) -> str:
    news_block = "\n".join(
        f'[{i+1}] "{h["title"]}" ({h["source"]}) — {h["url"]}'
        for i, h in enumerate(headlines)
    )
    today = now_ist().strftime("%Y-%m-%d")

    return f"""You are an expert Indian stock market analyst with deep knowledge of NSE-listed equities.

=== LIVE MARKET DATA ===
{market_summary}

=== RECENT NEWS HEADLINES (with sources) ===
{news_block}

Today's date: {today}

Generate stock picks across 3 timeframes:
1. **Intraday** (5 picks) – stocks likely to move within today's session
2. **Weekly** (5 picks) – stocks expected to perform over the next 1-5 trading sessions
3. **Monthly** (5 picks) – stocks with strong positional potential over the next 2-4 weeks

Total: 15 picks (no duplicates across timeframes).

For EACH pick, provide ALL of these fields:
- symbol: exact NSE trading symbol (e.g., RELIANCE, TCS, INFY)
- name: full company name
- sector: industry sector
- rationale: 2-3 sentences explaining WHY, referencing specific news headlines by number
- confidence: score from 1 to 10 (integer)
- catalyst: the specific news or technical catalyst driving this pick
- target_horizon: "intraday", "weekly", or "monthly" (must match timeframe)
- action: "BUY" or "SELL" — judge each stock independently on its own merits. Weak,
  overextended, or negative-news stocks should get a genuine "SELL" call, not be
  omitted or forced into "BUY". A realistic, well-reasoned picks list is NOT
  all-BUY — include SELL calls whenever the data and news actually support one.
- target_pct: expected % gain/loss target (positive number)
- stop_loss_pct: suggested stop-loss % from entry (positive number)
- tags: array of relevant tags (e.g., ["momentum", "breakout", "earnings", "sector-rotation", "news-driven"])
- news_sources: array of the specific news sources that influenced this pick, each with {{"title":"headline text","url":"link","source":"source name","published_at":"date"}}

RULES:
- IMPORTANT: Only suggest NSE-listed stocks from the NIFTY 500 index (not just Nifty 50 — include mid-caps and smaller large-caps)
- Never suggest penny stocks (price < Rs 50)
- Mix of large-cap and mid-cap across diverse sectors
- Always cite which news or market data influenced each pick
- Intraday: targets 0.5-3%, stop-losses 0.3-1.5%
- Weekly: targets 2-8%, stop-losses 1-4%
- Monthly: targets 5-20%, stop-losses 3-8%
- No duplicate symbols across timeframes

Return ONLY a valid JSON object (no markdown fences, no explanation outside JSON):
{{"intraday":[{{"symbol":"...","name":"...","sector":"...","rationale":"...","confidence":8,"catalyst":"...","target_horizon":"intraday","action":"BUY","target_pct":1.5,"stop_loss_pct":0.8,"tags":["momentum","news-driven"],"news_sources":[{{"title":"...","url":"...","source":"...","published_at":"..."}}]}}],"weekly":[...],"monthly":[...]}}"""


# ---------------------------------------------------------------------------
# LAYER 1: Gemini
# ---------------------------------------------------------------------------
async def _call_gemini(headlines: list[dict[str, str]], market_summary: str) -> dict[str, list[dict[str, Any]]]:
    """Layer 1: Gemini 2.0 Flash Lite via google-genai SDK, primary + backup key.
    Runs the synchronous SDK call in a thread so asyncio.wait_for can cancel it.
    """
    from google import genai as genai_sdk

    from app.core.config import get_settings

    settings = get_settings()
    api_keys: list[str] = []
    if settings.gemini_api_key:
        api_keys.append(settings.gemini_api_key)
    if settings.gemini_backup_api_key:
        api_keys.append(settings.gemini_backup_api_key)
    if not api_keys:
        log.info("layer1_skip: no gemini keys configured")
        return {"intraday": [], "weekly": [], "monthly": []}

    prompt = _build_ai_prompt(headlines, market_summary)

    def _sync_gemini_call(api_key: str) -> str:
        """Run Gemini synchronously in a thread so timeout actually works."""
        client = genai_sdk.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        return response.text

    last_error = None
    loop = asyncio.get_event_loop()
    for i, api_key in enumerate(api_keys):
        key_label = "primary" if i == 0 else "backup"
        try:
            text = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_gemini_call, api_key),
                timeout=GEMINI_PER_KEY_TIMEOUT,
            )
            parsed = _parse_ai_response(text)
            if parsed and _has_picks(parsed):
                total = sum(len(v) for v in parsed.values())
                log.info("layer1_gemini_success key=%s picks=%d", key_label, total)
                return parsed
            log.warning("layer1_gemini_empty key=%s", key_label)
        except asyncio.TimeoutError:
            log.warning("layer1_gemini_timeout key=%s (%ds)", key_label, GEMINI_PER_KEY_TIMEOUT)
            last_error = TimeoutError(f"Gemini {key_label} timed out")
        except Exception as e:
            last_error = e
            log.warning("layer1_gemini_failed key=%s error=%s type=%s", key_label, e, type(e).__name__)

    log.warning("layer1_gemini_exhausted last_error=%s", last_error)
    return {"intraday": [], "weekly": [], "monthly": []}


# ---------------------------------------------------------------------------
# LAYER 2: Groq / xAI (alternative AI providers)
# ---------------------------------------------------------------------------
async def _call_alternative_ai(headlines: list[dict[str, str]], market_summary: str) -> dict[str, list[dict[str, Any]]]:
    """Try Groq (Llama 3.3 70B) then xAI (Grok) as fallback AI providers."""
    from app.core.config import get_settings
    import httpx

    settings = get_settings()
    prompt = _build_ai_prompt(headlines, market_summary)
    messages = [
        {"role": "system", "content": "You are an expert Indian stock market analyst. Return ONLY valid JSON."},
        {"role": "user", "content": prompt},
    ]

    # Try Groq first (free tier: 500K tokens/day)
    if settings.groq_api_key:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.groq_api_key)
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4096,
                ),
                timeout=GROQ_TIMEOUT,
            )
            text = response.choices[0].message.content or ""
            parsed = _parse_ai_response(text)
            if parsed and _has_picks(parsed):
                total = sum(len(v) for v in parsed.values())
                log.info("layer2_groq_success picks=%d", total)
                return parsed
            log.warning("layer2_groq_empty_response")
        except asyncio.TimeoutError:
            log.warning("layer2_groq_timeout")
        except Exception as e:
            log.warning("layer2_groq_failed error=%s type=%s", e, type(e).__name__)

    # Try xAI/Grok
    if settings.xai_api_key:
        try:
            async with httpx.AsyncClient(timeout=XAI_TIMEOUT) as client:
                resp = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.xai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "grok-3-mini-fast",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    parsed = _parse_ai_response(text)
                    if parsed and _has_picks(parsed):
                        total = sum(len(v) for v in parsed.values())
                        log.info("layer2_xai_success picks=%d", total)
                        return parsed
                else:
                    log.warning("layer2_xai_http_error status=%d", resp.status_code)
        except Exception as e:
            log.warning("layer2_xai_failed error=%s type=%s", e, type(e).__name__)

    log.warning("layer2_all_alternative_ai_failed")
    return {"intraday": [], "weekly": [], "monthly": []}


# ---------------------------------------------------------------------------
# LAYER 3: Technical Scoring Engine (zero API dependency)
# ---------------------------------------------------------------------------
def _extract_headline_symbols(headlines: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Match headlines to Nifty 500 symbols. Returns symbol -> [matching headlines]."""
    _ensure_symbol_lookup()
    symbol_headlines: dict[str, list[dict[str, str]]] = {}

    for h in headlines:
        title_upper = h["title"].upper()
        matched: set[str] = set()
        # Check for exact symbol matches (word-bounded)
        for sym in _SYMBOL_META:
            if len(sym) >= 3 and re.search(rf'\b{re.escape(sym)}\b', title_upper):
                matched.add(sym)
        # Check company name keywords
        for keyword, sym in _NAME_KEYWORDS.items():
            if len(keyword) >= 5 and keyword in title_upper and sym not in matched:
                matched.add(sym)
        for sym in matched:
            symbol_headlines.setdefault(sym, []).append(h)

    return symbol_headlines


async def _load_stock_data() -> dict[str, dict[str, Any]]:
    """Bulk-load price + indicator data from Redis using pipelines for speed."""
    from app.services.redis_cache import get_redis

    r = await get_redis()
    stocks: dict[str, dict[str, Any]] = {}

    # Collect all price keys
    price_keys: list[str] = []
    async for key in r.scan_iter(match="price:*", count=500):
        price_keys.append(key)
    log.info("layer3_load_stock_data: found %d price keys", len(price_keys))

    # Pipeline GET for all price keys (much faster than sequential)
    if price_keys:
        pipe = r.pipeline(transaction=False)
        for pk in price_keys[:500]:
            pipe.get(pk)
        results = await pipe.execute()

        for pk, raw in zip(price_keys[:500], results):
            try:
                if not raw:
                    continue
                data = json.loads(raw) if isinstance(raw, str) else {}
                if data:
                    symbol = data.get("symbol", pk.replace("price:", ""))
                    stocks[symbol] = {
                        "ltp": float(data.get("ltp", data.get("last", data.get("close", 0))) or 0),
                        "change_pct": float(data.get("change_pct", data.get("pChange", 0)) or 0),
                        "volume": float(data.get("volume", 0) or 0),
                    }
            except Exception as e:
                log.debug("layer3_price_parse_error key=%s: %s", pk, e)

    # Collect all indicator keys
    ind_keys: list[str] = []
    async for key in r.scan_iter(match="ind:*:1d", count=500):
        ind_keys.append(key)
    log.info("layer3_load_stock_data: found %d indicator keys, stocks=%d", len(ind_keys), len(stocks))

    # Pipeline HGETALL for all indicator keys
    if ind_keys:
        pipe = r.pipeline(transaction=False)
        for ik in ind_keys[:500]:
            pipe.hgetall(ik)
        results = await pipe.execute()

        for ik, data in zip(ind_keys[:500], results):
            try:
                if not data:
                    continue
                key_str = ik if isinstance(ik, str) else ik.decode()
                parts = key_str.split(":")
                if len(parts) >= 2:
                    symbol = parts[1]
                    if symbol in stocks:
                        stocks[symbol]["rsi_14"] = float(data.get("rsi_14", 0) or 0)
                        stocks[symbol]["ema_9"] = float(data.get("ema_9", 0) or 0)
                        stocks[symbol]["ema_21"] = float(data.get("ema_21", 0) or 0)
            except Exception:
                continue

    return stocks


def _score_stock(
    symbol: str,
    data: dict[str, Any],
    headline_count: int,
    timeframe: str,
    median_volume: float = 0.0,
) -> float:
    """Composite score (0-100) for a stock in a given timeframe.

    `median_volume` is the universe's median traded volume for this run,
    used to score volume *relatively* — an absolute volume number is
    meaningless without something to compare it against.
    """
    ltp = data.get("ltp", 0)
    if ltp < 50:  # skip penny stocks
        return 0

    change_pct = abs(data.get("change_pct", 0))
    rsi = data.get("rsi_14", 50)
    ema_9 = data.get("ema_9", 0)
    ema_21 = data.get("ema_21", 0)
    volume = data.get("volume", 0)

    # News score (0-25)
    news_score = min(25, headline_count * 10) if headline_count else 0

    # Momentum score (0-25)
    if change_pct >= 3:
        momentum = 25
    elif change_pct >= 2:
        momentum = 20
    elif change_pct >= 1:
        momentum = 15
    elif change_pct >= 0.5:
        momentum = 10
    else:
        momentum = 5

    # RSI score (0-20) — extremity in EITHER direction is an actionable
    # signal (oversold -> BUY reversal candidate, overbought -> SELL
    # candidate); direction is decided separately by _determine_action.
    # Scoring only oversold highly would mean overbought stocks — the very
    # candidates a SELL call should surface — never rank into the picks
    # list at all.
    if rsi < 30 or rsi > 70:
        rsi_score = 20
    elif rsi < 40 or rsi > 60:
        rsi_score = 14
    else:
        rsi_score = 8  # neutral

    # EMA trend-clarity score (0-15) — a clear trend in either direction is
    # a stronger signal than no trend; direction is decided separately.
    if ema_9 > 0 and ema_21 > 0:
        ema_score = 15
    else:
        ema_score = 8  # no data, neutral

    # Volume score (0-15) — relative to the universe's median volume this
    # run, so a stock trading well above its peers' typical volume scores
    # higher than one that merely has *some* nonzero volume.
    if median_volume > 0 and volume > 0:
        ratio = volume / median_volume
        vol_score = min(15.0, 5.0 + ratio * 5.0)
    elif volume > 0:
        vol_score = 8.0  # no universe baseline available — neutral
    else:
        vol_score = 5.0

    # Weight by timeframe
    if timeframe == "intraday":
        return news_score * 1.2 + momentum * 1.3 + rsi_score * 0.8 + ema_score * 0.5 + vol_score * 1.2
    elif timeframe == "weekly":
        return news_score * 0.8 + momentum * 0.8 + rsi_score * 1.0 + ema_score * 1.3 + vol_score * 0.8
    else:  # monthly
        return news_score * 0.5 + momentum * 0.5 + rsi_score * 1.3 + ema_score * 1.2 + vol_score * 0.5


def _determine_action(data: dict[str, Any]) -> str:
    """BUY vs SELL from momentum + RSI + EMA together, rather than
    defaulting to BUY unless one narrow bearish condition is met — that
    made SELL calls nearly impossible to reach in practice."""
    change_pct = data.get("change_pct", 0)
    ema_9 = data.get("ema_9", 0)
    ema_21 = data.get("ema_21", 0)
    rsi = data.get("rsi_14", 50)

    has_ema = ema_9 > 0 and ema_21 > 0
    bullish_ema = has_ema and ema_9 > ema_21
    bearish_ema = has_ema and ema_9 < ema_21

    score = 0
    if rsi > 70:
        score -= 2  # overbought
    elif rsi < 30:
        score += 2  # oversold reversal
    if bullish_ema:
        score += 2
    elif bearish_ema:
        score -= 2
    if change_pct >= 1:
        score += 1
    elif change_pct <= -1:
        score -= 1

    return "SELL" if score < 0 else "BUY"


def _compute_targets(timeframe: str, change_pct: float) -> tuple[float, float]:
    volatility = max(0.5, abs(change_pct))
    if timeframe == "intraday":
        target = round(min(3.0, max(0.5, volatility * 1.2)), 1)
        sl = round(min(1.5, max(0.3, volatility * 0.6)), 1)
    elif timeframe == "weekly":
        target = round(min(8.0, max(2.0, volatility * 2.5)), 1)
        sl = round(min(4.0, max(1.0, volatility * 1.2)), 1)
    else:
        target = round(min(15.0, max(5.0, volatility * 4.0)), 1)
        sl = round(min(8.0, max(3.0, volatility * 2.0)), 1)
    return target, sl


def _build_rationale(
    symbol: str,
    data: dict[str, Any],
    headlines: list[dict[str, str]],
    timeframe: str,
) -> tuple[str, str, list[str]]:
    """Generate template rationale, catalyst, and tags."""
    _ensure_symbol_lookup()
    meta = _SYMBOL_META.get(symbol, {"name": symbol, "sector": ""})
    name = meta["name"]
    change_pct = data.get("change_pct", 0)
    rsi = data.get("rsi_14", 0)
    ema_9 = data.get("ema_9", 0)
    ema_21 = data.get("ema_21", 0)
    ltp = data.get("ltp", 0)

    ema_status = "bullish" if ema_9 > ema_21 else "bearish"
    tags: list[str] = []
    parts: list[str] = []

    # News-driven
    if headlines:
        parts.append(f"{name} featured in {len(headlines)} recent market headline(s)")
        tags.append("news-driven")

    # Momentum
    if abs(change_pct) >= 1:
        direction = "upward" if change_pct > 0 else "downward"
        parts.append(f"showing {direction} momentum ({change_pct:+.1f}%)")
        tags.append("momentum")

    # EMA
    if ema_9 > 0 and ema_21 > 0:
        parts.append(f"{ema_status} EMA alignment (9 {'>' if ema_9 > ema_21 else '<'} 21)")
        if ema_9 > ema_21:
            tags.append("ema-crossover")

    # RSI
    if rsi > 0:
        if rsi < 35:
            parts.append(f"RSI at {rsi:.0f} indicates oversold territory — potential reversal")
            tags.append("oversold-reversal")
        elif rsi > 70:
            parts.append(f"RSI at {rsi:.0f} in overbought zone")
            tags.append("overbought")
        else:
            parts.append(f"RSI at {rsi:.0f} in healthy range")

    rationale = ". ".join(parts) + "." if parts else f"{name} selected based on technical screening of Nifty 500 universe."

    # Catalyst
    if headlines:
        catalyst = headlines[0]["title"][:120]
    elif abs(change_pct) >= 1:
        catalyst = f"Strong price momentum ({change_pct:+.1f}%) with {ema_status} technical setup"
    else:
        catalyst = f"Technical signal: {ema_status} EMA crossover" if ema_9 > 0 else "Nifty 500 screening signal"

    if not tags:
        tags = ["technical"]

    return rationale, catalyst, tags


async def _generate_technical_picks(headlines: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    """Layer 3: RSS-headline + technical-scoring fallback, zero AI API needed.

    Used only when Gemini and Groq/xAI (Layers 1-2) are unavailable or
    exhausted — not the primary path. Works in two modes:
    - With live price data: full technical + news scoring
    - Without price data (market closed): news-headline-only scoring
    """
    _ensure_symbol_lookup()

    # Extract which symbols appear in headlines
    headline_map = _extract_headline_symbols(headlines)
    log.info("layer3_headline_symbols found=%d", len(headline_map))

    # Load all stock data from Redis
    all_stocks = await _load_stock_data()
    log.info("layer3_stock_data loaded=%d", len(all_stocks))

    # Fallback: if no live price data, build stocks from headline-matched symbols
    if not all_stocks and headline_map:
        log.info("layer3_no_price_data: using headline-only mode with %d matched symbols", len(headline_map))
        for sym in headline_map:
            if sym in _SYMBOL_META:
                all_stocks[sym] = {"ltp": 100, "change_pct": 0, "volume": 0}
    elif not all_stocks:
        log.warning("layer3_no_stock_data_and_no_headlines")
        return {"intraday": [], "weekly": [], "monthly": []}

    # Median volume across the universe this run, used to score each stock's
    # volume relative to its peers (see _score_stock) rather than as a flat
    # "has any volume at all" signal.
    volumes = sorted(v.get("volume", 0) for v in all_stocks.values() if v.get("volume", 0) > 0)
    median_volume = volumes[len(volumes) // 2] if volumes else 0.0

    result: dict[str, list[dict[str, Any]]] = {}
    used_symbols: set[str] = set()

    for timeframe in ("intraday", "weekly", "monthly"):
        scored: list[tuple[str, float, dict]] = []
        for symbol, data in all_stocks.items():
            if symbol in used_symbols:
                continue
            if data.get("ltp", 0) < 50:  # skip penny stocks
                continue
            headline_count = len(headline_map.get(symbol, []))
            score = _score_stock(symbol, data, headline_count, timeframe, median_volume)
            scored.append((symbol, score, data))

        scored.sort(key=lambda x: x[1], reverse=True)
        log.info("layer3_%s scored=%d top3=%s", timeframe, len(scored),
                 [(s, round(sc, 1)) for s, sc, _ in scored[:3]])
        picks: list[dict[str, Any]] = []

        for symbol, score, data in scored[:5]:
            used_symbols.add(symbol)
            meta = _SYMBOL_META.get(symbol, {"name": symbol, "sector": ""})
            sym_headlines = headline_map.get(symbol, [])
            action = _determine_action(data)
            target_pct, sl_pct = _compute_targets(timeframe, data.get("change_pct", 0))
            rationale, catalyst, tags = _build_rationale(symbol, data, sym_headlines, timeframe)

            picks.append({
                "symbol": symbol,
                "name": meta["name"],
                "sector": meta["sector"],
                "rationale": rationale,
                "confidence": max(1, min(10, round(score / 10))),
                "catalyst": catalyst,
                "target_horizon": timeframe,
                "action": action,
                "target_pct": target_pct,
                "stop_loss_pct": sl_pct,
                "tags": tags,
                "news_sources": sym_headlines[:3],
            })

        result[timeframe] = picks

    total = sum(len(v) for v in result.values())
    log.info("layer3_technical_success picks=%d", total)
    return result


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
async def generate_suggestions() -> dict[str, Any]:
    log.info("generate_suggestions: starting")
    try:
        headlines = await asyncio.wait_for(_fetch_news_headlines(), timeout=RSS_FETCH_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("generate_suggestions: RSS fetch timed out")
        headlines = []
    except Exception as e:
        log.warning("generate_suggestions: RSS fetch error: %s", e)
        headlines = []

    try:
        market_summary = await asyncio.wait_for(_get_market_summary(), timeout=MARKET_SUMMARY_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("generate_suggestions: market summary timed out")
        market_summary = "Market data unavailable."
    except Exception as e:
        log.warning("generate_suggestions: market summary error: %s", e)
        market_summary = "Market data unavailable."

    log.info("fetched %d news headlines, market_summary_len=%d", len(headlines), len(market_summary))

    if not headlines and market_summary == "Market data unavailable.":
        return {
            "intraday": [], "weekly": [], "monthly": [],
            "generated_at": now_ist().isoformat(),
            "headline_count": 0,
            "next_refresh": get_next_trading_day_9am().isoformat(),
        }

    # Layer 1 (primary): Gemini actually reads the headlines + market data
    # and reasons about picks. This runs first every time a key is
    # configured — it is not a fallback path.
    source = "gemini"
    picks: dict[str, list] = {"intraday": [], "weekly": [], "monthly": []}
    try:
        picks = await asyncio.wait_for(
            _call_gemini(headlines, market_summary), timeout=GEMINI_LAYER_TIMEOUT
        )
    except asyncio.TimeoutError:
        log.warning("layer1_global_timeout")
    except Exception as e:
        log.warning("layer1_unexpected: %s %s", type(e).__name__, e)

    # Layer 2: Groq / xAI — alternative LLM providers, tried only if Gemini
    # produced nothing usable.
    if not _has_picks(picks):
        source = "groq"
        try:
            picks = await asyncio.wait_for(
                _call_alternative_ai(headlines, market_summary), timeout=ALT_AI_LAYER_TIMEOUT
            )
        except asyncio.TimeoutError:
            log.warning("layer2_global_timeout")
        except Exception as e:
            log.warning("layer2_unexpected: %s %s", type(e).__name__, e)

    # Layer 3 (last resort): RSS + technical scoring, zero AI API needed.
    # Only reached if no AI provider responded at all.
    if not _has_picks(picks):
        source = "technical-analysis"
        try:
            picks = await asyncio.wait_for(
                _generate_technical_picks(headlines), timeout=TECHNICAL_LAYER_TIMEOUT
            )
        except asyncio.TimeoutError:
            log.warning("layer3_global_timeout")
        except Exception as e:
            log.warning("layer3_unexpected: %s %s", type(e).__name__, e)

    total_count = sum(len(v) for k, v in picks.items() if k in ("intraday", "weekly", "monthly"))
    log.info("ai_suggestions source=%s total_picks=%d", source, total_count)

    result = {
        "intraday": picks.get("intraday", []),
        "weekly": picks.get("weekly", []),
        "monthly": picks.get("monthly", []),
        "generated_at": now_ist().isoformat(),
        "headline_count": len(headlines),
        "next_refresh": get_next_trading_day_9am().isoformat(),
        "source": source,
    }

    if total_count > 0:
        try:
            from app.services.redis_cache import set_json
            ttl = _compute_ttl_seconds()
            await set_json(REDIS_KEY, result, ttl=ttl)
            log.info("ai_suggestions_cached count=%d ttl=%d source=%s", total_count, ttl, source)
        except Exception as e:
            log.warning("failed to cache ai suggestions: %s", e)

    return result


async def get_suggestions() -> dict[str, Any] | None:
    try:
        from app.services.redis_cache import get_json
        cached = await get_json(REDIS_KEY)
        if cached:
            return cached
    except Exception:
        pass
    return None


async def get_or_generate_suggestions() -> dict[str, Any]:
    """Get cached suggestions or generate fresh ones. Never returns None."""
    cached = await get_suggestions()
    if cached:
        return cached
    try:
        return await generate_suggestions()
    except Exception as e:
        log.error("Failed to generate AI suggestions: %s", e)
        return {
            "intraday": [], "weekly": [], "monthly": [],
            "generated_at": now_ist().isoformat(),
            "headline_count": 0,
            "error": "Generation failed — will retry on next request",
        }

"""Per-symbol BUY/SELL/HOLD analysis for the chart page.

Unlike ai_suggestions.py (which curates a *list* of picks — a stock either
makes the cut or doesn't), this is scoped to one stock a user is actively
looking at, so HOLD is a first-class, expected outcome, not just "wasn't
picked". Same fallback discipline as ai_suggestions.py: Groq (+ targeted
RSS headlines for this specific company) first, deterministic technical
scoring only if Groq is unavailable or fails — never silently empty.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
from urllib.parse import quote

from app.utils.time import now_ist

log = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "stock_analysis:"
ANALYSIS_TTL = 15 * 60  # 15 min — fresh enough for intraday news, cheap on Groq/RSS

RSS_TIMEOUT = 10
GROQ_TIMEOUT = 15


async def get_or_generate_analysis(symbol: str) -> dict[str, Any]:
    from app.services.redis_cache import get_json, set_json

    symbol = symbol.upper()
    cache_key = f"{REDIS_KEY_PREFIX}{symbol}"
    cached = await get_json(cache_key)
    if cached:
        return cached

    result = await generate_stock_analysis(symbol)
    await set_json(cache_key, result, ttl=ANALYSIS_TTL)
    return result


async def generate_stock_analysis(symbol: str) -> dict[str, Any]:
    from app.services.ai_suggestions import _SYMBOL_META, _ensure_symbol_lookup

    symbol = symbol.upper()
    _ensure_symbol_lookup()
    meta = _SYMBOL_META.get(symbol, {"name": symbol, "sector": ""})
    name, sector = meta["name"], meta.get("sector", "")

    data, headlines = await asyncio.gather(
        _load_symbol_data(symbol),
        _fetch_symbol_headlines(symbol, name),
    )

    result: dict[str, Any] | None = None
    source = "groq"
    try:
        prompt = _build_stock_prompt(symbol, name, sector, data, headlines)
        result = await asyncio.wait_for(_call_groq_for_stock(prompt), timeout=GROQ_TIMEOUT + 2)
    except asyncio.TimeoutError:
        log.warning("stock_analysis_groq_global_timeout symbol=%s", symbol)
        result = None

    if not result:
        source = "technical-analysis"
        result = _technical_fallback(symbol, data, headlines)

    result["symbol"] = symbol
    result["name"] = name
    result["sector"] = sector
    result.setdefault("news_sources", headlines[:3])
    result["source"] = source
    result["generated_at"] = now_ist().isoformat()
    return result


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
async def _load_symbol_data(symbol: str) -> dict[str, Any]:
    from app.services.redis_cache import get_redis

    data: dict[str, Any] = {}
    try:
        r = await get_redis()
        raw_price = await r.get(f"price:{symbol}")
        if raw_price:
            p = json.loads(raw_price) if isinstance(raw_price, str) else {}
            data["ltp"] = float(p.get("ltp", p.get("last", p.get("close", 0))) or 0)
            data["change_pct"] = float(p.get("change_pct", p.get("pChange", 0)) or 0)
            data["volume"] = float(p.get("volume", 0) or 0)

        ind = await r.hgetall(f"ind:{symbol}:1d")
        if ind:
            data["rsi_14"] = float(ind.get("rsi_14", 0) or 0)
            data["ema_9"] = float(ind.get("ema_9", 0) or 0)
            data["ema_21"] = float(ind.get("ema_21", 0) or 0)
            data["macd"] = float(ind.get("macd", 0) or 0)
            data["macd_signal"] = float(ind.get("macd_signal", 0) or 0)
    except Exception as e:
        log.warning("stock_analysis_data_load_failed symbol=%s error=%s", symbol, e)
    return data


async def _fetch_symbol_headlines(symbol: str, company_name: str) -> list[dict[str, str]]:
    import feedparser
    import httpx

    query = quote(f'"{company_name}" OR ({symbol} NSE India)')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BreakoutScan/1.0)"}
    headlines: list[dict[str, str]] = []
    try:
        async with httpx.AsyncClient(timeout=RSS_TIMEOUT, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    if not title:
                        continue
                    source_field = entry.get("source", {})
                    source_name = (
                        source_field.get("title", "Google News")
                        if isinstance(source_field, dict)
                        else "Google News"
                    )
                    headlines.append({
                        "title": title,
                        "url": entry.get("link", ""),
                        "source": source_name,
                        "published_at": entry.get("published", ""),
                    })
    except Exception as e:
        log.warning("stock_analysis_rss_fetch_failed symbol=%s error=%s", symbol, e)
    return headlines


# ---------------------------------------------------------------------------
# Layer 1: Groq
# ---------------------------------------------------------------------------
def _build_stock_prompt(
    symbol: str, name: str, sector: str, data: dict[str, Any], headlines: list[dict[str, str]]
) -> str:
    headline_lines = "\n".join(f"- {h['title']} ({h['source']})" for h in headlines[:12])
    if not headline_lines:
        headline_lines = "No recent headlines found."

    return f"""You are an expert Indian stock market analyst. Analyze {name} ({symbol}), sector: {sector}.

Current data:
- LTP: {data.get('ltp', 'unknown')}
- Change: {data.get('change_pct', 0):+.2f}%
- RSI(14): {data.get('rsi_14', 'unknown')}
- EMA9 vs EMA21: {data.get('ema_9', 0)} vs {data.get('ema_21', 0)}

Recent news headlines:
{headline_lines}

Based on this data and news, give a single trade call. Respond with ONLY valid JSON in exactly this shape, no markdown fences, no extra text:
{{"action": "BUY" | "SELL" | "HOLD", "confidence": <integer 1-10>, "rationale": "<2-3 sentences grounded in the data/news above>", "catalyst": "<one short phrase: the single biggest reason for this call>", "target_pct": <expected % move if BUY/SELL, 0 if HOLD>, "stop_loss_pct": <suggested stop-loss % if BUY/SELL, 0 if HOLD>, "tags": ["<short-tag>", "..."]}}"""


async def _call_groq_for_stock(prompt: str) -> dict[str, Any] | None:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.groq_api_key:
        log.info("stock_analysis_groq_skip: no key configured")
        return None

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an expert Indian stock market analyst. Return ONLY valid JSON, no markdown fences."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1024,
            ),
            timeout=GROQ_TIMEOUT,
        )
        text = response.choices[0].message.content or ""
        parsed = _parse_stock_response(text)
        if parsed:
            log.info("stock_analysis_groq_success action=%s", parsed.get("action"))
            return parsed
        log.warning("stock_analysis_groq_unparseable")
        return None
    except asyncio.TimeoutError:
        log.warning("stock_analysis_groq_timeout")
        return None
    except Exception as e:
        log.warning("stock_analysis_groq_failed error=%s type=%s", e, type(e).__name__)
        return None


def _parse_stock_response(text: str) -> dict[str, Any] | None:
    text = text.strip()
    fence_match = re.match(r"^```(?:\w+)?\s*\n(.*?)```\s*$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    action = str(parsed.get("action", "")).upper()
    if action not in ("BUY", "SELL", "HOLD"):
        return None

    try:
        confidence = int(parsed.get("confidence", 5))
    except (TypeError, ValueError):
        confidence = 5
    confidence = max(1, min(10, confidence))

    return {
        "action": action,
        "confidence": confidence,
        "rationale": str(parsed.get("rationale", "")) or "No rationale provided.",
        "catalyst": str(parsed.get("catalyst", "")) or "",
        "target_pct": float(parsed.get("target_pct", 0) or 0),
        "stop_loss_pct": float(parsed.get("stop_loss_pct", 0) or 0),
        "tags": [str(t) for t in parsed.get("tags", [])][:6],
    }


# ---------------------------------------------------------------------------
# Layer 2 (last resort): deterministic technical scoring
# ---------------------------------------------------------------------------
def _technical_fallback(
    symbol: str, data: dict[str, Any], headlines: list[dict[str, str]]
) -> dict[str, Any]:
    rsi = data.get("rsi_14", 0)
    ema_9 = data.get("ema_9", 0)
    ema_21 = data.get("ema_21", 0)
    change_pct = data.get("change_pct", 0)

    has_ema = ema_9 > 0 and ema_21 > 0
    bullish_ema = has_ema and ema_9 > ema_21
    bearish_ema = has_ema and ema_9 < ema_21

    score = 0
    if rsi and rsi < 35:
        score += 2
    elif rsi and rsi > 70:
        score -= 2
    if bullish_ema:
        score += 2
    elif bearish_ema:
        score -= 2
    if change_pct >= 1:
        score += 1
    elif change_pct <= -1:
        score -= 1

    if score >= 2:
        action = "BUY"
    elif score <= -2:
        action = "SELL"
    else:
        action = "HOLD"

    confidence = max(1, min(10, 5 + abs(score)))

    if action == "HOLD":
        target_pct, stop_loss_pct = 0.0, 0.0
    else:
        volatility = max(0.5, abs(change_pct))
        target_pct = round(min(8.0, max(2.0, volatility * 2.0)), 1)
        stop_loss_pct = round(min(4.0, max(1.0, volatility * 1.0)), 1)

    parts: list[str] = []
    tags: list[str] = []
    if rsi:
        if rsi < 35:
            parts.append(f"RSI at {rsi:.0f} indicates oversold territory")
            tags.append("oversold")
        elif rsi > 70:
            parts.append(f"RSI at {rsi:.0f} is in overbought territory")
            tags.append("overbought")
        else:
            parts.append(f"RSI at {rsi:.0f} is in a neutral range")
    if has_ema:
        parts.append(f"EMA9 is {'above' if bullish_ema else 'below'} EMA21 ({'bullish' if bullish_ema else 'bearish'} trend)")
        tags.append("ema-bullish" if bullish_ema else "ema-bearish")
    if abs(change_pct) >= 1:
        parts.append(f"price is {'up' if change_pct > 0 else 'down'} {abs(change_pct):.1f}% today")
        tags.append("momentum")
    if not parts:
        parts.append("no strong technical signal in either direction")
    if not tags:
        tags.append("neutral")

    rationale = f"No AI provider was available, so this call is technical-only: {'; '.join(parts)}."
    catalyst = headlines[0]["title"][:120] if headlines else "No recent news found; call is technical-only"

    return {
        "action": action,
        "confidence": confidence,
        "rationale": rationale,
        "catalyst": catalyst,
        "target_pct": target_pct,
        "stop_loss_pct": stop_loss_pct,
        "tags": tags,
    }

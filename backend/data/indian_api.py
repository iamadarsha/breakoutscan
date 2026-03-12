"""
Indian Stock API integration — https://stock.indianapi.in
Provides real-time live prices, trending stocks, and stock details.
Used alongside Yahoo Finance for better live data coverage.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Optional

import httpx
import redis.asyncio as aioredis
import structlog

from config import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://stock.indianapi.in"

# Map our NSE symbol names to Indian API company names for /stock endpoint
SYMBOL_TO_NAME = {
    "RELIANCE": "Reliance Industries",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "INFY": "Infosys",
    "TCS": "TCS",
    "BHARTIARTL": "Bharti Airtel",
    "SBIN": "State Bank of India",
    "LT": "Larsen & Toubro",
    "BAJFINANCE": "Bajaj Finance",
    "HINDUNILVR": "Hindustan Unilever",
    "ITC": "ITC",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "AXISBANK": "Axis Bank",
    "MARUTI": "Maruti Suzuki",
    "TITAN": "Titan Company",
    "SUNPHARMA": "Sun Pharmaceutical",
    "TATAMOTORS": "Tata Motors",
    "WIPRO": "Wipro",
    "ULTRACEMCO": "UltraTech Cement",
    "ONGC": "Oil and Natural Gas",
    "NTPC": "NTPC",
    "POWERGRID": "Power Grid",
    "NESTLEIND": "Nestle India",
    "TATASTEEL": "Tata Steel",
    "JSWSTEEL": "JSW Steel",
    "ADANIENT": "Adani Enterprises",
    "ADANIPORTS": "Adani Ports",
    "BAJAJ-AUTO": "Bajaj Auto",
    "BAJAJFINSV": "Bajaj Finserv",
    "COALINDIA": "Coal India",
    "DRREDDY": "Dr Reddy",
    "EICHERMOT": "Eicher Motors",
    "GRASIM": "Grasim Industries",
    "HCLTECH": "HCL Technologies",
    "HEROMOTOCO": "Hero MotoCorp",
    "HINDALCO": "Hindalco",
    "INDUSINDBK": "IndusInd Bank",
    "M&M": "Mahindra & Mahindra",
    "TECHM": "Tech Mahindra",
    "DIVISLAB": "Divi's Laboratories",
    "CIPLA": "Cipla",
    "APOLLOHOSP": "Apollo Hospitals",
    "ASIANPAINT": "Asian Paints",
    "BRITANNIA": "Britannia Industries",
    "HDFCLIFE": "HDFC Life",
    "SBILIFE": "SBI Life Insurance",
    "TATACONSUM": "Tata Consumer",
    "BPCL": "Bharat Petroleum",
    "SHRIRAMFIN": "Shriram Finance",
    "ZOMATO": "Zomato",
}

# Reverse map: RIC codes from Indian API → our symbols
RIC_TO_SYMBOL = {
    "RELI.NS": "RELIANCE", "HDBK.NS": "HDFCBANK", "ICBK.NS": "ICICIBANK",
    "INFY.NS": "INFY", "TCS.NS": "TCS", "BRTI.NS": "BHARTIARTL",
    "SBI.NS": "SBIN", "LART.NS": "LT", "BJFN.NS": "BAJFINANCE",
    "HLL.NS": "HINDUNILVR", "ITC.NS": "ITC", "KTKM.NS": "KOTAKBANK",
    "AXBK.NS": "AXISBANK", "MRTI.NS": "MARUTI", "TITN.NS": "TITAN",
    "SUN.NS": "SUNPHARMA", "TAMO.NS": "TATAMOTORS", "WIPR.NS": "WIPRO",
    "ULTC.NS": "ULTRACEMCO", "ONGC.NS": "ONGC", "NTPC.NS": "NTPC",
    "PGRD.NS": "POWERGRID", "NEST.NS": "NESTLEIND", "TISC.NS": "TATASTEEL",
    "JSTL.NS": "JSWSTEEL", "ADEL.NS": "ADANIENT", "APSE.NS": "ADANIPORTS",
    "BAJA.NS": "BAJAJ-AUTO", "BJFS.NS": "BAJAJFINSV", "COAL.NS": "COALINDIA",
    "REDY.NS": "DRREDDY", "EICH.NS": "EICHERMOT", "GRAS.NS": "GRASIM",
    "HCLT.NS": "HCLTECH", "HROM.NS": "HEROMOTOCO", "HALC.NS": "HINDALCO",
    "INBK.NS": "INDUSINDBK", "MAHM.NS": "M&M", "TEML.NS": "TECHM",
    "DIVI.NS": "DIVISLAB", "CIPL.NS": "CIPLA", "APLH.NS": "APOLLOHOSP",
    "ASPN.NS": "ASIANPAINT", "BRIT.NS": "BRITANNIA", "HDFL.NS": "HDFCLIFE",
    "SBIL.NS": "SBILIFE", "TACP.NS": "TATACONSUM", "BPCL.NS": "BPCL",
    "SHMF.NS": "SHRIRAMFIN", "ZOMT.NS": "ZOMATO",
    "JIOF.NS": "JIOFINANCE",
}

# Also map by company name fragments for fuzzy matching from trending
COMPANY_NAME_TO_SYMBOL = {}
for sym, name in SYMBOL_TO_NAME.items():
    # Store lowercase fragments for matching
    COMPANY_NAME_TO_SYMBOL[name.lower()] = sym


def _match_trending_to_symbol(company_name: str, ric: str = "") -> Optional[str]:
    """Try to match a trending stock to our universe symbol."""
    # Try RIC first
    if ric and ric in RIC_TO_SYMBOL:
        return RIC_TO_SYMBOL[ric]
    # Try exact company name match
    cn_lower = company_name.lower()
    for fragment, sym in COMPANY_NAME_TO_SYMBOL.items():
        if fragment in cn_lower or cn_lower in fragment:
            return sym
    return None


async def fetch_trending_prices(redis: aioredis.Redis) -> int:
    """
    Fetch trending stocks (gainers + losers) from Indian API
    and update LTP in Redis for matched symbols.
    Returns number of prices updated.
    """
    api_key = settings.indian_api_key
    if not api_key:
        return 0

    updated = 0
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/trending",
                headers={"X-Api-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        trending = data.get("trending_stocks", {})
        all_stocks = trending.get("top_gainers", []) + trending.get("top_losers", [])

        pipe = redis.pipeline()
        for stock in all_stocks:
            ric = stock.get("ric", "")
            company = stock.get("company_name", "")
            sym = _match_trending_to_symbol(company, ric)
            if not sym:
                continue

            try:
                price = float(stock.get("price", 0))
                close = float(stock.get("close", 0))
                pct = float(stock.get("percent_change", 0))
                vol = int(float(stock.get("volume", 0)))
                high = float(stock.get("high", 0))
                low = float(stock.get("low", 0))
                open_ = float(stock.get("open", 0))

                ltp_data = {
                    "ltp": round(price, 2),
                    "change_pct": round(pct, 2),
                    "volume": vol,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "prev_close": close,
                    "source": "indianapi",
                    "ts": time.time(),
                }
                pipe.setex(f"ltp:{sym}", 300, json.dumps(ltp_data))  # 5 min TTL
                updated += 1
            except (ValueError, TypeError):
                continue

        if updated > 0:
            await pipe.execute()

        log.info("indian_api_trending_updated", updated=updated, total=len(all_stocks))

    except httpx.HTTPStatusError as e:
        log.warning("indian_api_http_error", status=e.response.status_code)
    except Exception as e:
        log.warning("indian_api_trending_error", error=str(e))

    return updated


async def fetch_stock_price(symbol: str, redis: aioredis.Redis) -> Optional[dict]:
    """
    Fetch a single stock's live price from Indian API.
    Used as a fallback/supplement when trending doesn't cover a symbol.
    """
    api_key = settings.indian_api_key
    if not api_key:
        return None

    name = SYMBOL_TO_NAME.get(symbol)
    if not name:
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BASE_URL}/stock",
                params={"name": name},
                headers={"X-Api-Key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        current_price = data.get("currentPrice", {})
        nse_price = current_price.get("NSE") or current_price.get("BSE")
        if not nse_price:
            return None

        price = float(nse_price)
        pct = float(data.get("percentChange", 0))

        ltp_data = {
            "ltp": round(price, 2),
            "change_pct": round(pct, 2),
            "volume": 0,  # /stock doesn't return volume
            "source": "indianapi",
            "ts": time.time(),
        }

        # Update Redis
        await redis.setex(f"ltp:{symbol}", 300, json.dumps(ltp_data))

        return ltp_data

    except Exception as e:
        log.warning("indian_api_stock_error", symbol=symbol, error=str(e))
        return None


async def periodic_live_prices(redis: aioredis.Redis, interval_seconds: int = 60):
    """
    Background task to refresh live prices from Indian API every N seconds.
    Uses /trending endpoint (1 API call for ~20 stocks) to stay within rate limits.
    """
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await fetch_trending_prices(redis)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("indian_api_periodic_error", error=str(e))
            await asyncio.sleep(30)

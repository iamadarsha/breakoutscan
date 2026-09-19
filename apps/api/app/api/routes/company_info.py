"""Company info endpoint using Wikipedia API (free, no key required)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter

from app.services.redis_cache import get_json, set_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/company", tags=["company"])

# Map common NSE symbols to Wikipedia article titles
SYMBOL_TO_WIKI: dict[str, str] = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "BHARTIARTL": "Bharti Airtel",
    "SBIN": "State Bank of India",
    "LT": "Larsen & Toubro",
    "ITC": "ITC Limited",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "BAJFINANCE": "Bajaj Finance",
    "AXISBANK": "Axis Bank",
    "TATAMOTORS": "Tata Motors",
    "MARUTI": "Maruti Suzuki",
    "SUNPHARMA": "Sun Pharmaceutical Industries",
    "TATASTEEL": "Tata Steel",
    "WIPRO": "Wipro",
    "NTPC": "NTPC Limited",
    "POWERGRID": "Power Grid Corporation of India",
    "M&M": "Mahindra & Mahindra",
    "ASIANPAINT": "Asian Paints",
    "ONGC": "Oil and Natural Gas Corporation",
    "TITAN": "Titan Company",
    "ADANIENT": "Adani Enterprises",
    "ULTRACEMCO": "UltraTech Cement",
    "BAJAJFINSV": "Bajaj Finserv",
    "JSWSTEEL": "JSW Steel",
    "TECHM": "Tech Mahindra",
    "HCLTECH": "HCL Technologies",
    "COALINDIA": "Coal India",
    "DRREDDY": "Dr. Reddy's Laboratories",
    "INDUSINDBK": "IndusInd Bank",
    "NESTLEIND": "Nestlé India",
    "CIPLA": "Cipla",
    "GRASIM": "Grasim Industries",
    "APOLLOHOSP": "Apollo Hospitals Enterprise",
    "HEROMOTOCO": "Hero MotoCorp",
    "EICHERMOT": "Eicher Motors",
    "DIVISLAB": "Divi's Laboratories",
    "BPCL": "Bharat Petroleum",
    "TATACONSUM": "Tata Consumer Products",
    "SBILIFE": "SBI Life Insurance Company",
    "BRITANNIA": "Britannia Industries",
    "HDFCLIFE": "HDFC Life",
    "ADANIPORTS": "Adani Ports and Special Economic Zone",
    "HINDALCO": "Hindalco Industries",
    "BAJAJ-AUTO": "Bajaj Auto",
    "SHRIRAMFIN": "Shriram Finance",
    "TRENT": "Trent (company)",
    "ADANIGREEN": "Adani Green Energy",
    "ADANIPOWER": "Adani Power",
    "ZOMATO": "Zomato",
    "PAYTM": "Paytm",
    "NYKAA": "Nykaa",
    "POLICYBZR": "PB Fintech",
    "DMART": "Avenue Supermarts",
    "PIDILITIND": "Pidilite Industries",
    "SIEMENS": "Siemens India",
    "VEDL": "Vedanta Limited",
    "TATAPOWER": "Tata Power",
    "IRCTC": "Indian Railway Catering and Tourism Corporation",
    "HAL": "Hindustan Aeronautics Limited",
    "BEL": "Bharat Electronics Limited",
    "BANKBARODA": "Bank of Baroda",
    "PNB": "Punjab National Bank",
    "CANBK": "Canara Bank",
}


async def _fetch_wikipedia(company_name: str) -> dict[str, Any] | None:
    """Fetch company summary from Wikipedia API."""
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + company_name.replace(" ", "_")
    headers = {"User-Agent": "BreakoutScan/1.0 (stock market app)"}

    async with httpx.AsyncClient(timeout=8, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "title": data.get("title", company_name),
                    "description": data.get("description", ""),
                    "extract": data.get("extract", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source"),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                }
        except Exception as e:
            logger.warning("wikipedia_fetch_failed company=%s error=%s", company_name, e)

    return None


async def _search_wikipedia(query: str) -> dict[str, Any] | None:
    """Search Wikipedia for a company and return best match summary."""
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "search": query + " company India",
        "limit": 3,
        "format": "json",
    }
    headers = {"User-Agent": "BreakoutScan/1.0 (stock market app)"}

    async with httpx.AsyncClient(timeout=8, headers=headers) as client:
        try:
            resp = await client.get(search_url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                titles = data[1] if len(data) > 1 else []
                for title in titles:
                    result = await _fetch_wikipedia(title)
                    if result and result.get("extract"):
                        return result
        except Exception as e:
            logger.warning("wikipedia_search_failed query=%s error=%s", query, e)

    return None


@router.get("/{symbol}")
async def get_company_info(symbol: str) -> dict[str, Any]:
    """Get company info from Wikipedia. Cached in Redis for 24 hours."""
    symbol = symbol.upper()
    cache_key = f"company_info:{symbol}"

    # Check cache
    try:
        cached = await get_json(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    # Try direct lookup first
    wiki_title = SYMBOL_TO_WIKI.get(symbol)
    result = None

    if wiki_title:
        result = await _fetch_wikipedia(wiki_title)

    # Fallback: search Wikipedia
    if not result:
        # Try with the symbol as company name
        from app.api.routes.stocks import FALLBACK_STOCKS
        stock_info = next((s for s in FALLBACK_STOCKS if s["symbol"] == symbol), None)
        company_name = stock_info["company_name"] if stock_info else symbol
        result = await _search_wikipedia(company_name)

    if not result:
        return {
            "symbol": symbol,
            "title": symbol,
            "description": "",
            "extract": "Company information not available at the moment.",
            "thumbnail": None,
            "url": "",
            "source": "none",
        }

    response = {
        "symbol": symbol,
        **result,
        "source": "wikipedia",
    }

    # Cache for 24 hours
    try:
        await set_json(cache_key, response, ttl=86400)
    except Exception:
        pass

    return response

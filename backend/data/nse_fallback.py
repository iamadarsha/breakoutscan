"""
NSE Fallback Data Source.
Uses NSE official API (as fallback when Upstox WebSocket is unavailable).
Handles session cookies, index data, and stock quotes.
"""
from __future__ import annotations
import asyncio
from typing import Optional
import httpx
import structlog

log = structlog.get_logger(__name__)

NSE_BASE = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

# MOCK market data for development (when Upstox + NSE both unavailable)
MOCK_INDICES = [
    {"name": "NIFTY 50", "ltp": 22541.30, "change": 134.50, "change_pct": 0.60},
    {"name": "BANKNIFTY", "ltp": 48234.75, "change": -89.25, "change_pct": -0.18},
    {"name": "SENSEX", "ltp": 74121.90, "change": 389.40, "change_pct": 0.53},
    {"name": "NIFTY IT", "ltp": 38450.00, "change": 210.00, "change_pct": 0.55},
    {"name": "NIFTY PHARMA", "ltp": 19823.45, "change": -127.30, "change_pct": -0.64},
    {"name": "NIFTY AUTO", "ltp": 22167.80, "change": 89.60, "change_pct": 0.41},
    {"name": "NIFTY FMCG", "ltp": 53428.60, "change": 234.50, "change_pct": 0.44},
    {"name": "INDIA VIX", "ltp": 14.23, "change": -0.89, "change_pct": -5.89},
]

MOCK_STOCKS = {
    "RELIANCE": {"ltp": 2847.50, "change_pct": 1.24, "volume": 4200000},
    "HDFCBANK": {"ltp": 1678.90, "change_pct": 0.89, "volume": 8100000},
    "TATAMOTORS": {"ltp": 924.35, "change_pct": 3.40, "volume": 12300000},
    "WIPRO": {"ltp": 489.60, "change_pct": -2.10, "volume": 5800000},
    "ICICIBANK": {"ltp": 1124.75, "change_pct": 0.45, "volume": 9200000},
    "INFY": {"ltp": 1789.20, "change_pct": -1.32, "volume": 6400000},
    "TCS": {"ltp": 4128.00, "change_pct": 0.78, "volume": 2100000},
    "SBIN": {"ltp": 789.40, "change_pct": 1.89, "volume": 15600000},
    "BAJFINANCE": {"ltp": 7892.00, "change_pct": 2.14, "volume": 1800000},
    "LT": {"ltp": 3567.45, "change_pct": 0.92, "volume": 3400000},
}


class NSESession:
    """
    HTTP session with NSE India API — handles cookie management.
    NSE requires cookies from the homepage before API calls work.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._cookies_initialized = False

    async def _ensure_session(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=NSE_HEADERS,
                timeout=15.0,
                follow_redirects=True,
            )

        if not self._cookies_initialized:
            try:
                # Hit homepage to get session cookies
                await self._client.get(NSE_BASE)
                self._cookies_initialized = True
            except Exception as e:
                log.warning("nse_session_init_failed", error=str(e))

    async def get_all_indices(self) -> list[dict]:
        """Fetch all NSE index data."""
        await self._ensure_session()
        try:
            resp = await self._client.get(f"{NSE_BASE}/api/allIndices")
            resp.raise_for_status()
            data = resp.json()
            result = []
            for item in data.get("data", []):
                result.append({
                    "name": item.get("indexSymbol", ""),
                    "ltp": float(item.get("last", 0)),
                    "change": float(item.get("change", 0)),
                    "change_pct": float(item.get("percentChange", 0)),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "advances": int(item.get("advances", 0)),
                    "declines": int(item.get("declines", 0)),
                })
            return result
        except Exception as e:
            log.warning("nse_indices_failed", error=str(e), using="mock_data")
            return MOCK_INDICES

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Fetch stock quote from NSE."""
        await self._ensure_session()
        try:
            resp = await self._client.get(
                f"{NSE_BASE}/api/quote-equity",
                params={"symbol": symbol},
            )
            resp.raise_for_status()
            data = resp.json()
            pd_data = data.get("priceInfo", {})
            return {
                "symbol": symbol,
                "ltp": float(pd_data.get("lastPrice", 0)),
                "open": float(pd_data.get("open", 0)),
                "high": float(pd_data.get("intraDayHighLow", {}).get("max", 0)),
                "low": float(pd_data.get("intraDayHighLow", {}).get("min", 0)),
                "prev_close": float(pd_data.get("previousClose", 0)),
                "change": float(pd_data.get("change", 0)),
                "change_pct": float(pd_data.get("pChange", 0)),
                "volume": int(data.get("marketDeptOrderBook", {}).get("tradeInfo", {}).get("totalTradedVolume", 0)),
                "week_high_52": float(pd_data.get("weekHighLow", {}).get("max", 0)),
                "week_low_52": float(pd_data.get("weekHighLow", {}).get("min", 0)),
            }
        except Exception as e:
            log.warning("nse_quote_failed", symbol=symbol, error=str(e))
            return MOCK_STOCKS.get(symbol)

    async def get_market_status(self) -> dict:
        """Check if NSE market is open."""
        await self._ensure_session()
        try:
            resp = await self._client.get(f"{NSE_BASE}/api/marketStatus")
            resp.raise_for_status()
            data = resp.json()
            market_state = data.get("marketState", [])
            nse_state = next(
                (m for m in market_state if m.get("market") == "Capital Market"), {}
            )
            is_open = nse_state.get("marketStatus", "").upper() == "OPEN"
            return {
                "is_open": is_open,
                "session": "normal" if is_open else "closed",
                "message": nse_state.get("marketStatusMessage", "Market Closed"),
            }
        except Exception as e:
            log.warning("nse_market_status_failed", error=str(e))
            import pytz
            from datetime import datetime
            ist = pytz.timezone("Asia/Kolkata")
            now = datetime.now(ist)
            is_open = (
                now.weekday() < 5  # Monday–Friday
                and (9, 15) <= (now.hour, now.minute) <= (15, 30)
            )
            return {"is_open": is_open, "session": "normal" if is_open else "closed", "message": ""}

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ── Singleton ───────────────────────────────────────────────────────────────

_nse_session: Optional[NSESession] = None


def get_nse_session() -> NSESession:
    global _nse_session
    if _nse_session is None:
        _nse_session = NSESession()
    return _nse_session


async def get_mock_indices() -> list[dict]:
    """Return mock index data with slight random drift for demo purposes."""
    import random
    result = []
    for idx in MOCK_INDICES:
        drift = random.uniform(-0.15, 0.15)
        new_ltp = round(idx["ltp"] * (1 + drift / 100), 2)
        result.append({**idx, "ltp": new_ltp})
    return result

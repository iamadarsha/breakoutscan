"""
Upstox Instruments Loader.
Downloads NSE/BSE instrument CSV files from Upstox CDN and builds
a trading_symbol → instrument_key mapping stored in Redis.
"""
import gzip
import io
import json
from typing import Optional
import asyncio

import httpx
import pandas as pd
import redis.asyncio as aioredis
import structlog

from config import settings

log = structlog.get_logger(__name__)

# Redis keys
NSE_INSTRUMENTS_KEY = "instruments:nse"    # HASH: symbol → instrument_key
BSE_INSTRUMENTS_KEY = "instruments:bse"
NIFTY50_KEY = "universe:nifty50"           # SET of symbols
NIFTY500_KEY = "universe:nifty500"
NSE_ALL_KEY = "universe:nse_all"
NSE_SYMBOLS_KEY = "symbols:nse"            # SORTED SET: symbol for lookup


async def download_instruments_csv(url: str) -> pd.DataFrame:
    """Download a gzipped CSV from Upstox CDN and return as DataFrame."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as f:
        df = pd.read_csv(f)

    log.info("instruments_downloaded", url=url, rows=len(df))
    return df


async def load_nse_instruments(redis: aioredis.Redis) -> int:
    """Download NSE instruments and store symbol→instrument_key in Redis."""
    try:
        df = await download_instruments_csv(settings.upstox_nse_instruments_url)

        # Upstox CSV columns: tradingsymbol, instrument_key, name, instrument_type, expiry, ...
        # Filter for equity instruments only
        eq_df = df[df["instrument_type"] == "EQ"].copy() if "instrument_type" in df.columns else df.copy()

        pipe = redis.pipeline()
        pipe.delete(NSE_INSTRUMENTS_KEY)

        all_symbols = []
        mapping = {}
        for _, row in eq_df.iterrows():
            symbol = str(row.get("tradingsymbol", "")).strip()
            ikey = str(row.get("instrument_key", "")).strip()
            if symbol and ikey:
                mapping[symbol] = ikey
                all_symbols.append(symbol)

        if mapping:
            pipe.hset(NSE_INSTRUMENTS_KEY, mapping=mapping)
            # Also store all NSE EQ symbols as a set for universe selection
            pipe.delete(NSE_ALL_KEY)
            # Store in batches
            if all_symbols:
                pipe.sadd(NSE_ALL_KEY, *all_symbols)

        await pipe.execute()
        log.info("nse_instruments_loaded", count=len(mapping))
        return len(mapping)

    except Exception as e:
        log.error("nse_instruments_failed", error=str(e))
        return 0


async def load_bse_instruments(redis: aioredis.Redis) -> int:
    """Download BSE instruments and store symbol→instrument_key in Redis."""
    try:
        df = await download_instruments_csv(settings.upstox_bse_instruments_url)
        eq_df = df[df["instrument_type"] == "EQ"].copy() if "instrument_type" in df.columns else df.copy()

        pipe = redis.pipeline()
        pipe.delete(BSE_INSTRUMENTS_KEY)

        mapping = {}
        for _, row in eq_df.iterrows():
            symbol = str(row.get("tradingsymbol", "")).strip()
            ikey = str(row.get("instrument_key", "")).strip()
            if symbol and ikey:
                mapping[symbol] = ikey

        if mapping:
            pipe.hset(BSE_INSTRUMENTS_KEY, mapping=mapping)

        await pipe.execute()
        log.info("bse_instruments_loaded", count=len(mapping))
        return len(mapping)

    except Exception as e:
        log.error("bse_instruments_failed", error=str(e))
        return 0


async def fetch_nifty50_constituents(redis: aioredis.Redis) -> list[str]:
    """Fetch NIFTY 50 constituent symbols from NSE API and store in Redis."""
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # NSE requires cookies — first hit the main page
            await client.get("https://www.nseindia.com/", headers=headers)
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        symbols = [item["symbol"] for item in data.get("data", []) if "symbol" in item]

        if symbols:
            pipe = redis.pipeline()
            pipe.delete(NIFTY50_KEY)
            pipe.sadd(NIFTY50_KEY, *symbols)
            await pipe.execute()
            log.info("nifty50_loaded", count=len(symbols))

        return symbols

    except Exception as e:
        log.warning("nifty50_fetch_failed", error=str(e), using="hardcoded_fallback")
        # Hardcoded NIFTY 50 symbols as fallback
        fallback = [
            "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK",
            "INFOSYS", "INFY", "SBILIFE", "KOTAKBANK", "LT",
            "HINDUNILVR", "AXISBANK", "SUNPHARMA", "BAJFINANCE", "ASIANPAINT",
            "MARUTI", "ULTRACEMCO", "TITAN", "NESTLEIND", "INDUSINDBANK",
            "TATAMOTORS", "WIPRO", "HCLTECH", "TECHM", "POWERGRID",
            "NTPC", "ONGC", "COALINDIA", "JSWSTEEL", "TATASTEEL",
            "M&M", "HINDALCO", "DIVISLAB", "DRREDDY", "CIPLA",
            "ADANIPORTS", "GRASIM", "BAJAJFINSV", "ADANIENT", "APOLLOHOSP",
            "EICHERMOT", "HEROMOTOCO", "BPCL", "SBIN", "ITC",
            "BRITANNIA", "TATACONSUM", "BAJAJ-AUTO", "LTIM", "UPL"
        ]
        if fallback:
            pipe = redis.pipeline()
            pipe.delete(NIFTY50_KEY)
            pipe.sadd(NIFTY50_KEY, *fallback)
            await pipe.execute()
        return fallback


async def get_instrument_key(redis: aioredis.Redis, symbol: str, exchange: str = "NSE") -> Optional[str]:
    """Look up instrument_key for a given symbol."""
    key_map = NSE_INSTRUMENTS_KEY if exchange == "NSE" else BSE_INSTRUMENTS_KEY
    result = await redis.hget(key_map, symbol)
    if result:
        return result.decode("utf-8") if isinstance(result, bytes) else result
    return None


async def get_universe_symbols(redis: aioredis.Redis, universe: str) -> list[str]:
    """Return list of symbols for the given universe."""
    universe_map = {
        "NSE_ALL": NSE_ALL_KEY,
        "NIFTY50": NIFTY50_KEY,
        "NIFTY500": NIFTY500_KEY,
    }
    key = universe_map.get(universe, NSE_ALL_KEY)
    members = await redis.smembers(key)
    return [m.decode("utf-8") if isinstance(m, bytes) else m for m in members]


async def run_daily_instrument_setup():
    """Run at 8:00 AM IST — download instruments and NIFTY50 list."""
    redis = aioredis.from_url(settings.redis_url)
    try:
        nse_count, bse_count = await asyncio.gather(
            load_nse_instruments(redis),
            load_bse_instruments(redis),
        )
        await fetch_nifty50_constituents(redis)
        log.info("daily_instrument_setup_complete", nse=nse_count, bse=bse_count)
    finally:
        await redis.aclose()

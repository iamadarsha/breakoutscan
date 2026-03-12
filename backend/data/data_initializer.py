"""
Data Initializer — Fetches real market data from Yahoo Finance,
computes technical indicators, and populates Redis for screener + charts.
Runs at startup and periodically refreshes.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import redis.asyncio as aioredis
import structlog

log = structlog.get_logger(__name__)

# ── NSE Stock Universe (Nifty 50 + popular mid-caps) ──────────────────────

NSE_UNIVERSE = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL",
    "SBIN", "LT", "BAJFINANCE", "HINDUNILVR", "ITC", "KOTAKBANK",
    "AXISBANK", "MARUTI", "TITAN", "SUNPHARMA", "TATAMOTORS", "WIPRO",
    "ULTRACEMCO", "ONGC", "NTPC", "POWERGRID", "NESTLEIND", "TATASTEEL",
    "JSWSTEEL", "ADANIENT", "ADANIPORTS", "BAJAJ-AUTO", "BAJAJFINSV",
    "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH",
    "HEROMOTOCO", "HINDALCO", "INDUSINDBK", "M&M", "TECHM",
    "DIVISLAB", "CIPLA", "APOLLOHOSP", "ASIANPAINT", "BRITANNIA",
    "HDFCLIFE", "SBILIFE", "TATACONSUM", "BPCL", "SHRIRAMFIN",
    "ZOMATO",
]

COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries Ltd.", "HDFCBANK": "HDFC Bank Ltd.",
    "ICICIBANK": "ICICI Bank Ltd.", "INFY": "Infosys Ltd.",
    "TCS": "Tata Consultancy Services", "BHARTIARTL": "Bharti Airtel Ltd.",
    "SBIN": "State Bank of India", "LT": "Larsen & Toubro Ltd.",
    "BAJFINANCE": "Bajaj Finance Ltd.", "HINDUNILVR": "Hindustan Unilever Ltd.",
    "ITC": "ITC Ltd.", "KOTAKBANK": "Kotak Mahindra Bank",
    "AXISBANK": "Axis Bank Ltd.", "MARUTI": "Maruti Suzuki India Ltd.",
    "TITAN": "Titan Company Ltd.", "SUNPHARMA": "Sun Pharmaceutical",
    "TATAMOTORS": "Tata Motors Ltd.", "WIPRO": "Wipro Ltd.",
    "ULTRACEMCO": "UltraTech Cement Ltd.", "ONGC": "Oil & Natural Gas Corp.",
    "NTPC": "NTPC Ltd.", "POWERGRID": "Power Grid Corp.",
    "NESTLEIND": "Nestle India Ltd.", "TATASTEEL": "Tata Steel Ltd.",
    "JSWSTEEL": "JSW Steel Ltd.", "ADANIENT": "Adani Enterprises Ltd.",
    "ADANIPORTS": "Adani Ports & SEZ", "BAJAJ-AUTO": "Bajaj Auto Ltd.",
    "BAJAJFINSV": "Bajaj Finserv Ltd.", "COALINDIA": "Coal India Ltd.",
    "DRREDDY": "Dr. Reddy's Laboratories", "EICHERMOT": "Eicher Motors Ltd.",
    "GRASIM": "Grasim Industries Ltd.", "HCLTECH": "HCL Technologies Ltd.",
    "HEROMOTOCO": "Hero MotoCorp Ltd.", "HINDALCO": "Hindalco Industries",
    "INDUSINDBK": "IndusInd Bank Ltd.", "M&M": "Mahindra & Mahindra Ltd.",
    "TECHM": "Tech Mahindra Ltd.", "DIVISLAB": "Divi's Laboratories",
    "CIPLA": "Cipla Ltd.", "APOLLOHOSP": "Apollo Hospitals Enterprise",
    "ASIANPAINT": "Asian Paints Ltd.", "BRITANNIA": "Britannia Industries",
    "HDFCLIFE": "HDFC Life Insurance", "SBILIFE": "SBI Life Insurance",
    "TATACONSUM": "Tata Consumer Products", "BPCL": "Bharat Petroleum Corp.",
    "SHRIRAMFIN": "Shriram Finance Ltd.", "ZOMATO": "Zomato Ltd.",
}

SECTOR_MAP = {
    "RELIANCE": "Energy", "HDFCBANK": "Banking", "ICICIBANK": "Banking",
    "INFY": "IT", "TCS": "IT", "BHARTIARTL": "Telecom",
    "SBIN": "Banking", "LT": "Infrastructure", "BAJFINANCE": "NBFC",
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "KOTAKBANK": "Banking",
    "AXISBANK": "Banking", "MARUTI": "Automobile", "TITAN": "Consumer",
    "SUNPHARMA": "Pharma", "TATAMOTORS": "Automobile", "WIPRO": "IT",
    "ULTRACEMCO": "Cement", "ONGC": "Energy", "NTPC": "Power",
    "POWERGRID": "Power", "NESTLEIND": "FMCG", "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals", "ADANIENT": "Conglomerate", "ADANIPORTS": "Ports",
    "BAJAJ-AUTO": "Automobile", "BAJAJFINSV": "NBFC", "COALINDIA": "Mining",
    "DRREDDY": "Pharma", "EICHERMOT": "Automobile", "GRASIM": "Cement",
    "HCLTECH": "IT", "HEROMOTOCO": "Automobile", "HINDALCO": "Metals",
    "INDUSINDBK": "Banking", "M&M": "Automobile", "TECHM": "IT",
    "DIVISLAB": "Pharma", "CIPLA": "Pharma", "APOLLOHOSP": "Healthcare",
    "ASIANPAINT": "Paints", "BRITANNIA": "FMCG", "HDFCLIFE": "Insurance",
    "SBILIFE": "Insurance", "TATACONSUM": "FMCG", "BPCL": "Energy",
    "SHRIRAMFIN": "NBFC", "ZOMATO": "Technology",
}


def _safe(val, default=None):
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
        return float(val)
    except Exception:
        return default


def _fetch_yf_data(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Synchronous yfinance download for a single symbol."""
    yf_symbol = f"{symbol}.NS"
    try:
        df = yf.download(yf_symbol, period=period, interval=interval, progress=False, timeout=15)
        if df.empty:
            return pd.DataFrame()
        # Handle multi-level columns from yfinance 1.x+
        # Columns are MultiIndex like (Price, Ticker) e.g. ('Close', 'RELIANCE.NS')
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)  # Drop ticker level, keep price names
        df.reset_index(inplace=True)
        df.rename(columns={
            "Date": "timestamp", "Datetime": "timestamp",
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Adj Close": "adj_close", "Volume": "volume",
        }, inplace=True)
        # Ensure numeric
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["close"], inplace=True)
        return df
    except Exception as e:
        log.warning("yf_fetch_failed", symbol=symbol, error=str(e))
        return pd.DataFrame()


def compute_indicators_from_df(df: pd.DataFrame) -> dict:
    """Compute all technical indicators from OHLCV DataFrame."""
    if len(df) < 20:
        return {}

    results = {}

    # RSI
    for period in [9, 14, 21]:
        rsi = ta.rsi(df["close"], length=period)
        if rsi is not None and len(rsi) >= 3:
            results[f"rsi_{period}"] = [_safe(rsi.iloc[-1]), _safe(rsi.iloc[-2]), _safe(rsi.iloc[-3])]

    # EMA
    for period in [9, 20, 50, 200]:
        if len(df) >= period:
            ema = ta.ema(df["close"], length=period)
            if ema is not None and len(ema) >= 2:
                results[f"ema_{period}"] = [_safe(ema.iloc[-1]), _safe(ema.iloc[-2])]

    # SMA
    for period in [20, 50, 200]:
        if len(df) >= period:
            sma = ta.sma(df["close"], length=period)
            if sma is not None and len(sma) >= 2:
                results[f"sma_{period}"] = [_safe(sma.iloc[-1]), _safe(sma.iloc[-2])]

    # MACD
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None and len(macd) >= 2:
        results["macd_line"] = [_safe(macd.iloc[-1, 0]), _safe(macd.iloc[-2, 0])]
        results["macd_signal"] = [_safe(macd.iloc[-1, 1]), _safe(macd.iloc[-2, 1])]
        results["macd_histogram"] = [_safe(macd.iloc[-1, 2]), _safe(macd.iloc[-2, 2])]

    # Bollinger Bands
    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None and len(bb) >= 2:
        cols = bb.columns.tolist()
        bbu = [c for c in cols if "BBU" in c]
        bbm = [c for c in cols if "BBM" in c]
        bbl = [c for c in cols if "BBL" in c]
        if bbu and bbm and bbl:
            results["bb_upper"] = [_safe(bb[bbu[0]].iloc[-1]), _safe(bb[bbu[0]].iloc[-2])]
            results["bb_middle"] = [_safe(bb[bbm[0]].iloc[-1]), _safe(bb[bbm[0]].iloc[-2])]
            results["bb_lower"] = [_safe(bb[bbl[0]].iloc[-1]), _safe(bb[bbl[0]].iloc[-2])]
            results["bb_width"] = [
                _safe(bb[bbu[0]].iloc[-1] - bb[bbl[0]].iloc[-1]),
                _safe(bb[bbu[0]].iloc[-2] - bb[bbl[0]].iloc[-2]),
            ]

    # ATR
    atr = ta.atr(df["high"], df["low"], df["close"], length=14)
    if atr is not None and len(atr) >= 1:
        results["atr_14"] = [_safe(atr.iloc[-1])]

    # Supertrend
    try:
        st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
        if st is not None and len(st) >= 2:
            dir_col = [c for c in st.columns if "SUPERTd" in c]
            if dir_col:
                results["supertrend_direction"] = [
                    int(_safe(st[dir_col[0]].iloc[-1], 0)),
                    int(_safe(st[dir_col[0]].iloc[-2], 0)),
                ]
    except Exception:
        pass

    # Volume SMA
    vol_sma = ta.sma(df["volume"].astype(float), length=20)
    if vol_sma is not None and len(vol_sma) >= 1:
        results["volume_sma_20"] = [_safe(vol_sma.iloc[-1])]

    # Volume Ratio
    if "volume_sma_20" in results and results["volume_sma_20"][0] and results["volume_sma_20"][0] > 0:
        results["volume_ratio"] = [float(df["volume"].iloc[-1]) / results["volume_sma_20"][0]]

    # Current OHLCV
    results["close"] = [_safe(df["close"].iloc[-1]), _safe(df["close"].iloc[-2]) if len(df) >= 2 else None]
    results["open"] = [_safe(df["open"].iloc[-1]), _safe(df["open"].iloc[-2]) if len(df) >= 2 else None]
    results["high"] = [_safe(df["high"].iloc[-1]), _safe(df["high"].iloc[-2]) if len(df) >= 2 else None]
    results["low"] = [_safe(df["low"].iloc[-1]), _safe(df["low"].iloc[-2]) if len(df) >= 2 else None]
    results["volume"] = [int(df["volume"].iloc[-1]), int(df["volume"].iloc[-2]) if len(df) >= 2 else None]

    # 52-week high/low
    if len(df) >= 200:
        last_252 = df.tail(252)
    else:
        last_252 = df
    results["week_high_52"] = [_safe(last_252["high"].max())]
    results["week_low_52"] = [_safe(last_252["low"].min())]

    # Previous day data (for intraday scans)
    if len(df) >= 2:
        results["prev_day_high"] = [_safe(df["high"].iloc[-2])]
        results["prev_day_low"] = [_safe(df["low"].iloc[-2])]
        results["prev_day_close"] = [_safe(df["close"].iloc[-2])]

    return results


def _fetch_all_yf_data(symbols: list[str], period: str = "6mo", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Fetch data for multiple symbols using yfinance batch download (thread-safe)."""
    yf_symbols = [f"{s}.NS" for s in symbols]
    ticker_str = " ".join(yf_symbols)
    result = {}

    try:
        df = yf.download(ticker_str, period=period, interval=interval, progress=False, timeout=30, group_by="ticker")
        if df.empty:
            return result

        for sym, yf_sym in zip(symbols, yf_symbols):
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    if yf_sym in df.columns.get_level_values(0):
                        sym_df = df[yf_sym].copy()
                    else:
                        continue
                else:
                    sym_df = df.copy()

                sym_df.reset_index(inplace=True)
                # Flatten columns if still MultiIndex
                if isinstance(sym_df.columns, pd.MultiIndex):
                    sym_df.columns = [col[0] if isinstance(col, tuple) else col for col in sym_df.columns]

                sym_df.rename(columns={
                    "Date": "timestamp", "Datetime": "timestamp",
                    "Open": "open", "High": "high", "Low": "low",
                    "Close": "close", "Volume": "volume",
                }, inplace=True)

                for col in ["open", "high", "low", "close", "volume"]:
                    if col in sym_df.columns:
                        sym_df[col] = pd.to_numeric(sym_df[col], errors="coerce")
                sym_df.dropna(subset=["close"], inplace=True)

                if not sym_df.empty:
                    result[sym] = sym_df
            except Exception as e:
                log.warning("yf_parse_failed", symbol=sym, error=str(e))

    except Exception as e:
        log.error("yf_batch_download_failed", error=str(e))

    return result


async def initialize_market_data(redis: aioredis.Redis, symbols: list[str] = None):
    """
    Fetch real market data from Yahoo Finance for all symbols,
    compute indicators, and populate Redis.
    """
    if symbols is None:
        symbols = NSE_UNIVERSE

    log.info("data_init_starting", symbols=len(symbols))
    start = time.monotonic()

    success_count = 0
    failed = []

    # Fetch all symbols in one batch download (thread-safe)
    all_data = await asyncio.to_thread(_fetch_all_yf_data, symbols, "6mo", "1d")
    log.info("yf_download_complete", fetched=len(all_data), total=len(symbols))

    pipe = redis.pipeline()
    for sym in symbols:
        df = all_data.get(sym)
        if df is None or df.empty:
            failed.append(sym)
            continue

        indicators = compute_indicators_from_df(df)
        if not indicators:
            failed.append(sym)
            continue

        # Store indicators in Redis (1 hour TTL)
        ind_key = f"indicators:{sym}:daily"
        pipe.setex(ind_key, 3600, json.dumps(indicators))

        # Also store as 15min indicators (for intraday scans — use daily as approximation)
        ind_key_15m = f"indicators:{sym}:15min"
        pipe.setex(ind_key_15m, 3600, json.dumps(indicators))

        # Store as 5min indicators too
        ind_key_5m = f"indicators:{sym}:5min"
        pipe.setex(ind_key_5m, 3600, json.dumps(indicators))

        # Store LTP
        ltp = indicators.get("close", [0])[0]
        prev_close = indicators.get("prev_day_close", indicators.get("close", [0, 0]))
        prev = prev_close[0] if prev_close else ltp
        change_pct = ((ltp - prev) / prev * 100) if prev and prev > 0 else 0
        volume = indicators.get("volume", [0])[0] or 0

        ltp_data = {
            "ltp": round(ltp, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(volume),
            "open": indicators.get("open", [0])[0],
            "high": indicators.get("high", [0])[0],
            "low": indicators.get("low", [0])[0],
            "prev_close": prev,
        }
        pipe.setex(f"ltp:{sym}", 3600, json.dumps(ltp_data))

        # Store OHLCV bars for charting
        bars = []
        for i in range(len(df)):
            row = df.iloc[i]
            ts = row.get("timestamp")
            ts_str = str(ts) if ts is not None else ""
            bars.append({
                "ts": ts_str,
                "open": _safe(row["open"], 0),
                "high": _safe(row["high"], 0),
                "low": _safe(row["low"], 0),
                "close": _safe(row["close"], 0),
                "volume": int(_safe(row["volume"], 0)),
            })
        pipe.setex(f"ohlcv:{sym}:daily", 3600, json.dumps(bars))

        success_count += 1

    try:
        await pipe.execute()
    except Exception as e:
        log.error("redis_pipeline_error", error=str(e))

    # Populate universe set
    await redis.delete("universe:nse_all")
    if success_count > 0:
        successful_syms = [s for s in symbols if s not in failed]
        if successful_syms:
            await redis.sadd("universe:nse_all", *successful_syms)
            await redis.delete("universe:NSE_ALL")
            await redis.sadd("universe:NSE_ALL", *successful_syms)

    elapsed = int((time.monotonic() - start) * 1000)
    log.info("data_init_complete", success=success_count, failed=len(failed),
             failed_symbols=failed[:10], elapsed_ms=elapsed)

    return success_count, failed


async def fetch_intraday_data(redis: aioredis.Redis, symbols: list[str] = None):
    """Fetch intraday (15min) data for charting — uses batch download."""
    if symbols is None:
        symbols = NSE_UNIVERSE[:20]  # Limit to top 20 for intraday

    log.info("intraday_fetch_starting", symbols=len(symbols))

    all_data = await asyncio.to_thread(_fetch_all_yf_data, symbols, "5d", "15m")
    log.info("intraday_download_complete", fetched=len(all_data))

    pipe = redis.pipeline()
    for sym in symbols:
        df = all_data.get(sym)
        if df is None or df.empty:
            continue
        bars = []
        for i in range(len(df)):
            row = df.iloc[i]
            ts = row.get("timestamp")
            ts_str = str(ts) if ts is not None else ""
            bars.append({
                "ts": ts_str,
                "open": _safe(row["open"], 0),
                "high": _safe(row["high"], 0),
                "low": _safe(row["low"], 0),
                "close": _safe(row["close"], 0),
                "volume": int(_safe(row["volume"], 0)),
            })
        if bars:
            pipe.setex(f"ohlcv:{sym}:15min", 3600, json.dumps(bars))
            pipe.setex(f"ohlcv:{sym}:5min", 3600, json.dumps(bars))

    try:
        await pipe.execute()
    except Exception as e:
        log.error("intraday_redis_error", error=str(e))

    log.info("intraday_fetch_complete")


async def periodic_refresh(redis: aioredis.Redis, interval_seconds: int = 300):
    """Background task to refresh data every N seconds."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            log.info("periodic_data_refresh_starting")
            await initialize_market_data(redis)
            await fetch_intraday_data(redis)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("periodic_refresh_error", error=str(e))
            await asyncio.sleep(60)

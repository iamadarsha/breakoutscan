"""
Screener Engine — Core evaluate_scan function.
Evaluates conditions against pre-computed indicator values from Redis.
Target: scan 2000 symbols in < 2 seconds.
"""
from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
import structlog

from data.indicator_engine import IndicatorEngine
from screener.conditions import evaluate_all_conditions
from screener.prebuilt_scans import get_prebuilt_scan, list_prebuilt_scans, PREBUILT_SCANS
from data.upstox_instruments import get_universe_symbols
from data.data_initializer import COMPANY_NAMES as _REAL_COMPANY_NAMES, SECTOR_MAP as _REAL_SECTOR_MAP, NSE_UNIVERSE

log = structlog.get_logger(__name__)


class ScanResult:
    def __init__(self, symbol: str, ltp: float, change_pct: float, volume: int,
                 volume_ratio: Optional[float], rsi_14: Optional[float],
                 ema_status: Optional[str], matched_conditions: list[str],
                 company_name: Optional[str], sector: Optional[str],
                 market_cap: Optional[int]):
        self.symbol = symbol
        self.ltp = ltp
        self.change_pct = change_pct
        self.volume = volume
        self.volume_ratio = volume_ratio
        self.rsi_14 = rsi_14
        self.ema_status = ema_status
        self.matched_conditions = matched_conditions
        self.company_name = company_name
        self.sector = sector
        self.market_cap = market_cap
        self.scan_triggered_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "ltp": self.ltp,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "volume_ratio": self.volume_ratio,
            "rsi_14": self.rsi_14,
            "ema_status": self.ema_status,
            "matched_conditions": self.matched_conditions,
            "scan_triggered_at": self.scan_triggered_at.isoformat(),
            "sector": self.sector,
            "market_cap": self.market_cap,
        }


async def evaluate_scan(
    conditions: list[dict],
    filters: dict,
    timeframe: str,
    universe: str,
    redis: aioredis.Redis,
    indicator_engine: IndicatorEngine,
    logic: str = "AND",
    max_results: int = 200,
) -> tuple[list[ScanResult], int]:
    """
    Main screener evaluation function.
    
    Returns (results, duration_ms).
    
    Performance target: 2000 symbols in < 2s using Redis pipeline batch fetching.
    """
    start_time = time.monotonic()

    # 1. Get symbol universe
    symbols = await get_universe_symbols(redis, universe)
    if not symbols:
        # Fallback: use real NSE universe
        symbols = NSE_UNIVERSE

    # 2. Apply basic filters (price, market cap, exchange) from Redis metadata
    # For now, we'll apply filters post-scan for simplicity
    
    # 3. Batch fetch all indicator data + LTP from Redis
    pipe = redis.pipeline()
    for symbol in symbols:
        pipe.get(f"indicators:{symbol}:{timeframe}")
        pipe.get(f"ltp:{symbol}")
    
    try:
        raw_results = await pipe.execute()
    except Exception as e:
        log.error("screener_redis_fetch_error", error=str(e))
        raw_results = [None] * (len(symbols) * 2)

    # 4. Evaluate conditions for each symbol
    results = []
    import json

    for i, symbol in enumerate(symbols):
        raw_indicators = raw_results[i * 2]
        raw_ltp = raw_results[i * 2 + 1]

        indicators = json.loads(raw_indicators) if raw_indicators else {}
        ltp_data = json.loads(raw_ltp) if raw_ltp else {}

        # Use mock data if no real data available (development mode)
        if not indicators and symbol in _DEMO_STOCK_DATA:
            indicators = _DEMO_STOCK_DATA[symbol]
        if not ltp_data and symbol in _DEMO_LTP_DATA:
            ltp_data = _DEMO_LTP_DATA[symbol]

        if not indicators:
            continue

        ltp = ltp_data.get("ltp", indicators.get("close", [0])[0] if indicators.get("close") else 0)
        volume = ltp_data.get("volume", indicators.get("volume", [0])[0] if indicators.get("volume") else 0)
        
        if not ltp:
            continue

        # Apply price filter
        min_price = filters.get("min_price")
        max_price = filters.get("max_price")
        if min_price and ltp < min_price:
            continue
        if max_price and ltp > max_price:
            continue

        # Evaluate conditions
        passed, matched = evaluate_all_conditions(conditions, indicators, logic)
        if not passed:
            continue

        # Build result
        close_vals = indicators.get("close", [ltp])
        prev_close = close_vals[1] if len(close_vals) > 1 else ltp
        change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0

        vol_sma = (indicators.get("volume_sma_20") or [0])[0]
        volume_ratio = (volume / vol_sma) if vol_sma > 0 else None

        rsi_vals = indicators.get("rsi_14") or []
        rsi_14 = rsi_vals[0] if rsi_vals else None

        ema_status = _compute_ema_status(ltp, indicators)

        result = ScanResult(
            symbol=symbol,
            ltp=round(ltp, 2),
            change_pct=round(change_pct, 2),
            volume=int(volume),
            volume_ratio=round(volume_ratio, 2) if volume_ratio else None,
            rsi_14=round(rsi_14, 1) if rsi_14 else None,
            ema_status=ema_status,
            matched_conditions=matched,
            company_name=_REAL_COMPANY_NAMES.get(symbol, _COMPANY_NAMES.get(symbol)),
            sector=_REAL_SECTOR_MAP.get(symbol, _SECTOR_MAP.get(symbol)),
            market_cap=None,  # Would be fetched from stocks table in production
        )
        results.append(result)

        if len(results) >= max_results:
            break

    duration_ms = int((time.monotonic() - start_time) * 1000)
    log.info("scan_completed", symbols=len(symbols), results=len(results), duration_ms=duration_ms)
    return results, duration_ms


def _compute_ema_status(ltp: float, indicators: dict) -> Optional[str]:
    """Determine EMA status label for display."""
    ema20 = (indicators.get("ema_20") or [None])[0]
    ema50 = (indicators.get("ema_50") or [None])[0]
    ema200 = (indicators.get("ema_200") or [None])[0]

    if ema200 and abs(ltp - ema200) / ema200 < 0.005:
        return "At EMA200"
    if ema50 and ltp < ema50:
        return "Below EMA50"
    if ema20 and ltp < ema20:
        return "Below EMA20"
    if ema20 and ltp > ema20:
        return "Above EMA20"
    return None


async def run_prebuilt_scan(
    scan_id: str,
    redis: aioredis.Redis,
    indicator_engine: IndicatorEngine,
) -> tuple[list[ScanResult], int]:
    """Run a specific pre-built scan by ID."""
    scan_def = get_prebuilt_scan(scan_id)
    if not scan_def:
        raise ValueError(f"Unknown prebuilt scan: {scan_id}")

    return await evaluate_scan(
        conditions=scan_def["conditions"],
        filters=scan_def.get("filters", {}),
        timeframe=scan_def["timeframe"],
        universe=scan_def.get("universe", "NSE_ALL"),
        redis=redis,
        indicator_engine=indicator_engine,
    )


# ── Demo data for development (no Upstox connection) ──────────────────────

_DEMO_STOCK_DATA = {
    "RELIANCE": {
        "close": [2847.50, 2813.0], "open": [2813.0], "high": [2854.7], "low": [2808.5], "volume": [4200000],
        "rsi_14": [62.4, 58.2, 54.1], "ema_9": [2840.0, 2830.0], "ema_20": [2810.0, 2800.0],
        "ema_50": [2750.0], "ema_200": [2620.0], "vwap": [2830.0], "volume_sma_20": [3100000],
        "volume_ratio": [1.35], "macd_line": [12.4, 9.8], "macd_signal": [8.2, 9.1],
        "macd_histogram": [4.2, 0.7], "bb_upper": [2870.0], "bb_lower": [2750.0],
        "week_high_52": [3217.0], "week_low_52": [2180.0],
        "prev_day_high": [2820.0], "prev_day_low": [2780.0], "prev_day_close": [2812.0],
    },
    "HDFCBANK": {
        "close": [1678.90, 1664.0], "open": [1664.0], "high": [1685.0], "low": [1660.0], "volume": [8100000],
        "rsi_14": [58.7, 55.4, 52.3], "ema_9": [1675.0, 1668.0], "ema_20": [1650.0, 1642.0],
        "ema_50": [1610.0], "ema_200": [1550.0], "vwap": [1670.0], "volume_sma_20": [6500000],
        "volume_ratio": [1.25], "macd_line": [8.2, 6.4], "macd_signal": [5.8, 5.2],
        "macd_histogram": [2.4, 1.2], "bb_upper": [1710.0], "bb_lower": [1600.0],
        "week_high_52": [1810.0], "week_low_52": [1420.0],
        "prev_day_high": [1665.0], "prev_day_low": [1640.0], "prev_day_close": [1664.0],
    },
    "TATAMOTORS": {
        "close": [924.35, 893.0], "open": [893.0], "high": [928.5], "low": [890.0], "volume": [12300000],
        "rsi_14": [67.2, 62.1, 58.8], "ema_9": [915.0, 900.0], "ema_20": [885.0, 875.0],
        "ema_50": [840.0], "ema_200": [780.0], "vwap": [908.0], "volume_sma_20": [8400000],
        "volume_ratio": [1.46], "macd_line": [18.4, 14.2], "macd_signal": [12.8, 11.4],
        "macd_histogram": [5.6, 2.8], "bb_upper": [940.0], "bb_lower": [840.0],
        "week_high_52": [1070.0], "week_low_52": [640.0],
        "supertrend_direction": [1, -1],  # Just turned BUY
        "prev_day_high": [900.0], "prev_day_low": [870.0], "prev_day_close": [892.0],
    },
    "WIPRO": {
        "close": [489.60, 500.0], "open": [500.0], "high": [502.0], "low": [487.0], "volume": [5800000],
        "rsi_14": [38.4, 42.1, 46.8], "ema_9": [495.0, 498.0], "ema_20": [505.0, 508.0],
        "ema_50": [520.0], "ema_200": [540.0], "vwap": [496.0], "volume_sma_20": [4200000],
        "volume_ratio": [1.38], "macd_line": [-4.2, -2.1], "macd_signal": [-1.8, -0.9],
        "macd_histogram": [-2.4, -1.2], "bb_upper": [530.0], "bb_lower": [470.0],
        "week_high_52": [580.0], "week_low_52": [390.0],
        "prev_day_high": [505.0], "prev_day_low": [485.0], "prev_day_close": [500.0],
    },
    "ICICIBANK": {
        "close": [1124.75, 1119.0], "open": [1115.0], "high": [1128.0], "low": [1112.0], "volume": [9200000],
        "rsi_14": [55.1, 52.4, 50.8], "ema_9": [1120.0, 1114.0], "ema_20": [1100.0, 1092.0],
        "ema_50": [1070.0], "ema_200": [1010.0], "vwap": [1118.0], "volume_sma_20": [7800000],
        "volume_ratio": [1.18], "macd_line": [6.8, 5.4], "macd_signal": [4.9, 4.2],
        "macd_histogram": [1.9, 1.2], "bb_upper": [1150.0], "bb_lower": [1060.0],
        "week_high_52": [1240.0], "week_low_52": [870.0],
        "prev_day_high": [1125.0], "prev_day_low": [1105.0], "prev_day_close": [1119.0],
    },
}

_COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries Ltd.",
    "HDFCBANK": "HDFC Bank Ltd.",
    "TATAMOTORS": "Tata Motors Ltd.",
    "WIPRO": "Wipro Ltd.",
    "ICICIBANK": "ICICI Bank Ltd.",
    "INFY": "Infosys Ltd.",
    "TCS": "Tata Consultancy Services",
    "SBIN": "State Bank of India",
    "BAJFINANCE": "Bajaj Finance Ltd.",
    "LT": "Larsen & Toubro Ltd.",
}

_SECTOR_MAP = {
    "RELIANCE": "Energy",
    "HDFCBANK": "Banking",
    "TATAMOTORS": "Automobile",
    "WIPRO": "IT",
    "ICICIBANK": "Banking",
    "INFY": "IT",
    "TCS": "IT",
    "SBIN": "Banking",
    "BAJFINANCE": "NBFC",
    "LT": "Infrastructure",
}

_DEMO_LTP_DATA = {
    sym: {"ltp": data["close"][0], "volume": data["volume"][0]}
    for sym, data in _DEMO_STOCK_DATA.items()
}

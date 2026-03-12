"""
Technical Indicator Engine.
Computes indicators using pandas-ta and caches results in Redis.
Pre-computes: RSI, EMA, SMA, MACD, VWAP, Bollinger Bands, ATR, Supertrend, Volume SMA.
"""
from __future__ import annotations
import json
import asyncio
from typing import Optional
import numpy as np
import pandas as pd
import pandas_ta as ta
import redis.asyncio as aioredis
import structlog

from config import settings
from data.candle_builder import CandleBuilder, Candle

log = structlog.get_logger(__name__)

# Redis key pattern: indicators:{symbol}:{timeframe}
INDICATOR_TTL = 300  # 5 minutes TTL


class IndicatorEngine:
    """
    Computes and caches technical indicators for all symbols.
    Called after every candle close via CandleBuilder callback.
    """

    def __init__(self, redis: aioredis.Redis, candle_builder: CandleBuilder):
        self.redis = redis
        self.candle_builder = candle_builder

    # ── Main compute entry ──────────────────────────────────────────────────

    async def recompute(self, symbol: str, timeframe: str, candle: Candle):
        """Called when a candle closes — recompute all indicators for that symbol+tf."""
        candles = self.candle_builder.snapshot_for_screener(symbol, timeframe, n=300)
        if len(candles) < 20:
            return  # Not enough data yet

        df = pd.DataFrame([
            {"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in candles
        ]).astype(float)

        indicators = self._compute_indicators(df, timeframe)
        await self._cache_indicators(symbol, timeframe, indicators)

    def _compute_indicators(self, df: pd.DataFrame, timeframe: str) -> dict:
        """Compute all indicators from a OHLCV DataFrame. Returns dict of latest values."""
        results = {}

        # ── RSI ─────────────────────────────────────────────────────────────
        for period in [9, 14, 21]:
            rsi = ta.rsi(df["close"], length=period)
            if rsi is not None and len(rsi) >= 3:
                results[f"rsi_{period}"] = [
                    self._safe(rsi.iloc[-1]),
                    self._safe(rsi.iloc[-2]),
                    self._safe(rsi.iloc[-3]),
                ]

        # ── EMA ─────────────────────────────────────────────────────────────
        for period in [9, 20, 50, 200]:
            ema = ta.ema(df["close"], length=period)
            if ema is not None and len(ema) >= 2:
                results[f"ema_{period}"] = [
                    self._safe(ema.iloc[-1]),
                    self._safe(ema.iloc[-2]),
                ]

        # ── SMA ─────────────────────────────────────────────────────────────
        for period in [20, 50, 200]:
            sma = ta.sma(df["close"], length=period)
            if sma is not None and len(sma) >= 2:
                results[f"sma_{period}"] = [
                    self._safe(sma.iloc[-1]),
                    self._safe(sma.iloc[-2]),
                ]

        # ── MACD ─────────────────────────────────────────────────────────────
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd is not None and len(macd) >= 2:
            results["macd_line"] = [self._safe(macd["MACD_12_26_9"].iloc[-1]), self._safe(macd["MACD_12_26_9"].iloc[-2])]
            results["macd_signal"] = [self._safe(macd["MACDs_12_26_9"].iloc[-1]), self._safe(macd["MACDs_12_26_9"].iloc[-2])]
            results["macd_histogram"] = [self._safe(macd["MACDh_12_26_9"].iloc[-1]), self._safe(macd["MACDh_12_26_9"].iloc[-2])]

        # ── Bollinger Bands ──────────────────────────────────────────────────
        bb = ta.bbands(df["close"], length=20, std=2)
        if bb is not None and len(bb) >= 2:
            results["bb_upper"] = [self._safe(bb["BBU_20_2.0"].iloc[-1]), self._safe(bb["BBU_20_2.0"].iloc[-2])]
            results["bb_middle"] = [self._safe(bb["BBM_20_2.0"].iloc[-1]), self._safe(bb["BBM_20_2.0"].iloc[-2])]
            results["bb_lower"] = [self._safe(bb["BBL_20_2.0"].iloc[-1]), self._safe(bb["BBL_20_2.0"].iloc[-2])]
            results["bb_width"] = [
                self._safe(bb["BBU_20_2.0"].iloc[-1] - bb["BBL_20_2.0"].iloc[-1]),
                self._safe(bb["BBU_20_2.0"].iloc[-2] - bb["BBL_20_2.0"].iloc[-2]),
            ]

        # ── ATR ──────────────────────────────────────────────────────────────
        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr is not None and len(atr) >= 1:
            results["atr_14"] = [self._safe(atr.iloc[-1])]

        # ── Supertrend ───────────────────────────────────────────────────────
        st = ta.supertrend(df["high"], df["low"], df["close"], length=10, multiplier=3)
        if st is not None and len(st) >= 2:
            dir_col = [c for c in st.columns if "SUPERTd" in c]
            if dir_col:
                results["supertrend_direction"] = [
                    int(self._safe(st[dir_col[0]].iloc[-1], 0)),
                    int(self._safe(st[dir_col[0]].iloc[-2], 0)),
                ]

        # ── VWAP (intraday only — reset at 9:15 AM) ─────────────────────────
        if timeframe in ["1min", "5min", "15min", "30min"] and len(df) >= 1:
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
            cumulative_vol = df["volume"].cumsum()
            vwap = cumulative_tp_vol / cumulative_vol
            results["vwap"] = [self._safe(vwap.iloc[-1]), self._safe(vwap.iloc[-2]) if len(vwap) >= 2 else None]

        # ── Volume SMA ───────────────────────────────────────────────────────
        vol_sma = ta.sma(df["volume"], length=20)
        if vol_sma is not None and len(vol_sma) >= 1:
            results["volume_sma_20"] = [self._safe(vol_sma.iloc[-1])]

        # ── Volume Ratio ─────────────────────────────────────────────────────
        if "volume_sma_20" in results and results["volume_sma_20"][0] and results["volume_sma_20"][0] > 0:
            results["volume_ratio"] = [df["volume"].iloc[-1] / results["volume_sma_20"][0]]

        # ── Current OHLCV ─────────────────────────────────────────────────────
        results["close"] = [self._safe(df["close"].iloc[-1]), self._safe(df["close"].iloc[-2]) if len(df) >= 2 else None]
        results["open"] = [self._safe(df["open"].iloc[-1])]
        results["high"] = [self._safe(df["high"].iloc[-1])]
        results["low"] = [self._safe(df["low"].iloc[-1])]
        results["volume"] = [int(df["volume"].iloc[-1])]

        return results

    def _safe(self, val, default=None):
        """Convert NaN/None to default safely."""
        if val is None:
            return default
        try:
            if pd.isna(val):
                return default
            return float(val)
        except Exception:
            return default

    async def _cache_indicators(self, symbol: str, timeframe: str, indicators: dict):
        """Store computed indicators in Redis with TTL."""
        key = f"indicators:{symbol}:{timeframe}"
        await self.redis.setex(key, INDICATOR_TTL, json.dumps(indicators))

    async def get_indicators(self, symbol: str, timeframe: str) -> Optional[dict]:
        """Retrieve cached indicators from Redis."""
        key = f"indicators:{symbol}:{timeframe}"
        data = await self.redis.get(key)
        if not data:
            return None
        return json.loads(data)

    # ── LTP cache ─────────────────────────────────────────────────────────

    async def update_ltp(self, symbol: str, ltp: float, change_pct: float, volume: int):
        """Update live price in Redis for screener and WebSocket broadcast."""
        key = f"ltp:{symbol}"
        await self.redis.setex(key, 3600, json.dumps({
            "ltp": ltp,
            "change_pct": change_pct,
            "volume": volume,
        }))

    async def get_ltp(self, symbol: str) -> Optional[dict]:
        """Get live price from Redis."""
        data = await self.redis.get(f"ltp:{symbol}")
        return json.loads(data) if data else None

    async def get_all_ltps(self, symbols: list[str]) -> dict[str, dict]:
        """Batch-fetch live prices for multiple symbols."""
        pipe = self.redis.pipeline()
        for s in symbols:
            pipe.get(f"ltp:{s}")
        results = await pipe.execute()
        return {
            s: json.loads(r) if r else {}
            for s, r in zip(symbols, results)
        }


# ── Singleton factory ──────────────────────────────────────────────────────

_indicator_engine: Optional[IndicatorEngine] = None


def get_indicator_engine() -> Optional[IndicatorEngine]:
    return _indicator_engine


def init_indicator_engine(redis: aioredis.Redis, candle_builder: CandleBuilder) -> IndicatorEngine:
    global _indicator_engine
    _indicator_engine = IndicatorEngine(redis, candle_builder)
    return _indicator_engine

"""Yahoo Finance data provider for historical OHLCV and technical indicators."""

from __future__ import annotations

import asyncio
import math
from typing import Any

import pandas as pd
import structlog
import yfinance as yf

from app.services.redis_cache import hset_dict
from app.utils.redis_keys import indicator_key

log = structlog.get_logger(__name__)

# Rate-limit: short pause between successive yfinance downloads to avoid
# getting throttled by Yahoo.
_RATE_LIMIT_DELAY = 0.5  # seconds


def _safe_str(value: Any) -> str:
    """Convert a value to string, replacing NaN / None with empty string."""
    if value is None:
        return ""
    try:
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _fetch_history(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Daily OHLCV for one ticker.

    Deliberately `Ticker.history`, never `yf.download`: download() stores
    results in a module-level dict, so the concurrent worker-thread calls
    made by bulk_compute overwrite each other and hand several symbols the
    same (wrong) series. Ticker instances share no such state.
    """
    return yf.Ticker(ticker).history(
        period=period, interval=interval, auto_adjust=True
    )


def _nse_ticker(symbol: str) -> str:
    """Append ``.NS`` suffix for NSE stocks if not already present."""
    symbol = symbol.strip().upper()
    if not symbol.endswith(".NS"):
        return f"{symbol}.NS"
    return symbol


class YFinanceProvider:
    """Fetches historical data via *yfinance* and computes technical indicators
    using *pandas-ta*, storing the results in Redis.
    """

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    @staticmethod
    def get_historical(
        symbol: str,
        period: str = "6mo",
        interval: str = "1d",
    ) -> list[dict[str, Any]]:
        """Download OHLCV history for *symbol* and return as a list of dicts.

        This is a **synchronous** call because ``yfinance`` uses ``requests``
        under the hood.  Callers should run it inside
        ``asyncio.to_thread()`` when used from async code.
        """
        ticker = _nse_ticker(symbol)
        try:
            df = _fetch_history(ticker, period, interval)
            if df.empty:
                log.warning("yfinance_empty_data", symbol=ticker)
                return []

            # Flatten MultiIndex columns if present (yfinance >= 0.2.31)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated(keep="first")]

            records: list[dict[str, Any]] = []
            for idx, row in df.iterrows():
                records.append(
                    {
                        "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                        "open": float(row.get("Open", 0)),
                        "high": float(row.get("High", 0)),
                        "low": float(row.get("Low", 0)),
                        "close": float(row.get("Close", 0)),
                        "volume": int(row.get("Volume", 0)),
                    }
                )
            return records
        except Exception as exc:
            log.warning("yfinance_download_error", symbol=ticker, error=str(exc))
            return []

    # ------------------------------------------------------------------
    # Indicator computation + Redis storage
    # ------------------------------------------------------------------

    @staticmethod
    async def compute_and_store_indicators(symbol: str) -> bool:
        """Fetch 1-year history, compute indicators, and store in Redis.

        Returns ``True`` on success, ``False`` on failure.

        The download AND the pandas-ta indicator math both run via
        ``asyncio.to_thread()`` — not just the download. pandas-ta's ~10
        indicator calls per symbol are genuine synchronous CPU work; left on
        the event loop directly, 500 symbols' worth (run in this process's
        single asyncio event loop alongside the Upstox WebSocket) measured a
        17.5s event-loop stall during a live bulk-compute pass (2026-09-15),
        which is long enough to miss Upstox's keepalive pings and trigger a
        reconnect. Only the two Redis writes stay on the event loop, since
        those are genuine async I/O.
        """
        try:
            ticker = _nse_ticker(symbol)
            df = await asyncio.to_thread(_fetch_history, ticker, "1y", "1d")

            if df.empty:
                log.warning("yfinance_no_data_for_indicators", symbol=symbol)
                return False

            computed = await asyncio.to_thread(
                YFinanceProvider._compute_indicator_mapping, df, symbol
            )
            if computed is None:
                return False
            mapping, ohlcv_records = computed

            await hset_dict(indicator_key(symbol, "1d"), mapping, ttl=14400)

            if ohlcv_records:
                try:
                    from app.services.redis_cache import set_json as _set_json

                    await _set_json(f"ohlcv:{symbol}:daily", ohlcv_records, ttl=14400)
                except Exception as ohlcv_exc:
                    log.warning("ohlcv_store_error", symbol=symbol, error=str(ohlcv_exc))

            log.info("indicators_stored", symbol=symbol)
            return True

        except Exception as exc:
            log.warning("indicator_compute_error", symbol=symbol, error=str(exc))
            return False

    @staticmethod
    def _compute_indicator_mapping(
        df: pd.DataFrame, symbol: str
    ) -> tuple[dict[str, str], list[dict[str, Any]]] | None:
        """Pure, synchronous CPU work — safe to run via ``asyncio.to_thread``.

        Returns ``None`` when there's no usable numeric data after cleaning
        (caller treats this the same as an empty download), otherwise the
        Redis-ready indicator mapping plus daily OHLCV records for charting.
        """
        import pandas_ta as ta  # noqa: F811 – local import to isolate dep

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Ensure columns are simple strings
        df.columns = [str(c) for c in df.columns]

        # Drop duplicate columns: yfinance can produce two 'Close' columns after
        # MultiIndex flattening for certain single-ticker downloads. When that
        # happens df["Close"] returns a 2-D DataFrame, and pandas-ta crashes with
        # "arg must be a list, tuple, 1-d array, or Series".
        df = df.loc[:, ~df.columns.duplicated(keep="first")]

        # Coerce OHLCV columns to numeric — yfinance can return mixed types
        # for newly-listed or recently-split stocks (e.g. object dtype columns).
        for _col in ["Open", "High", "Low", "Close", "Volume"]:
            if _col in df.columns:
                df[_col] = pd.to_numeric(df[_col], errors="coerce")
        df = df.dropna(subset=["Close", "High", "Low", "Open"])
        df["Volume"] = df["Volume"].fillna(0)

        if df.empty:
            log.warning("yfinance_no_numeric_data", symbol=symbol)
            return None

        # --- Compute indicators ----------------------------------------
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Helper: get current and previous value from a series
        def _cur_prev(series):
            if series is None or len(series) < 2:
                cur = series.iloc[-1] if series is not None and len(series) else None
                return cur, None
            return series.iloc[-1], series.iloc[-2]

        # RSI
        rsi_series = ta.rsi(close, length=14)
        rsi, prev_rsi = _cur_prev(rsi_series)

        # EMAs
        ema9_series = ta.ema(close, length=9)
        ema9, prev_ema9 = _cur_prev(ema9_series)

        ema21_series = ta.ema(close, length=21)
        ema21, prev_ema21 = _cur_prev(ema21_series)

        # SMAs
        sma20_series = ta.sma(close, length=20)
        sma20, prev_sma20 = _cur_prev(sma20_series)

        sma50_series = ta.sma(close, length=50)
        sma50, prev_sma50 = _cur_prev(sma50_series)

        sma200_series = ta.sma(close, length=200)
        sma200, prev_sma200 = _cur_prev(sma200_series)

        # MACD
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        macd_val = None
        macd_signal = None
        prev_macd_val = None
        prev_macd_signal = None
        if macd_df is not None and not macd_df.empty:
            macd_cols = macd_df.columns.tolist()
            for col in macd_cols:
                if col.startswith("MACD_"):
                    macd_val = macd_df[col].iloc[-1]
                    prev_macd_val = macd_df[col].iloc[-2] if len(macd_df[col]) >= 2 else None
                elif col.startswith("MACDs_"):
                    macd_signal = macd_df[col].iloc[-1]
                    prev_macd_signal = macd_df[col].iloc[-2] if len(macd_df[col]) >= 2 else None

        # Bollinger Bands
        bb_df = ta.bbands(close, length=20, std=2)
        bb_upper = None
        bb_lower = None
        bb_mid = None
        if bb_df is not None and not bb_df.empty:
            bb_cols = bb_df.columns.tolist()
            for col in bb_cols:
                if col.startswith("BBU_"):
                    bb_upper = bb_df[col].iloc[-1]
                elif col.startswith("BBL_"):
                    bb_lower = bb_df[col].iloc[-1]
                elif col.startswith("BBM_"):
                    bb_mid = bb_df[col].iloc[-1]

        # ATR
        atr_series = ta.atr(high, low, close, length=14)
        atr = atr_series.iloc[-1] if atr_series is not None and len(atr_series) else None

        # ADX
        adx_df = ta.adx(high, low, close, length=14)
        adx_val = None
        if adx_df is not None and not adx_df.empty:
            adx_cols = adx_df.columns.tolist()
            for col in adx_cols:
                if col.startswith("ADX_"):
                    adx_val = adx_df[col].iloc[-1]

        # VWAP (only meaningful for intraday but we compute a rolling proxy)
        vwap_series = ta.vwap(high, low, close, volume)
        vwap = vwap_series.iloc[-1] if vwap_series is not None and len(vwap_series) else None

        # Volume SMA(20) — volume already coerced to numeric above
        vol_sma20_series = ta.sma(volume, length=20)
        vol_sma20 = (
            vol_sma20_series.iloc[-1]
            if vol_sma20_series is not None and len(vol_sma20_series)
            else None
        )

        # --- Latest and previous OHLCV -----------------------------------
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        latest_close = float(latest["Close"])
        prev_close_val = float(prev["Close"])
        change_pct = (
            round(((latest_close - prev_close_val) / prev_close_val) * 100, 2)
            if prev_close_val
            else 0.0
        )

        # 52-week high / low
        high_52w = float(high.tail(252).max()) if len(high) >= 252 else float(high.max())
        low_52w = float(low.tail(252).min()) if len(low) >= 252 else float(low.min())

        # --- Build mapping -----------------------------------------------
        mapping = {
            "open": _safe_str(latest.get("Open")),
            "high": _safe_str(latest.get("High")),
            "low": _safe_str(latest.get("Low")),
            "close": _safe_str(latest.get("Close")),
            "volume": _safe_str(latest.get("Volume")),
            "prev_open": _safe_str(prev.get("Open")),
            "prev_high": _safe_str(prev.get("High")),
            "prev_low": _safe_str(prev.get("Low")),
            "prev_close": _safe_str(prev.get("Close")),
            "prev_volume": _safe_str(prev.get("Volume")),
            "rsi_14": _safe_str(rsi),
            "prev_rsi_14": _safe_str(prev_rsi),
            "ema_9": _safe_str(ema9),
            "prev_ema_9": _safe_str(prev_ema9),
            "ema_21": _safe_str(ema21),
            "prev_ema_21": _safe_str(prev_ema21),
            "sma_20": _safe_str(sma20),
            "prev_sma_20": _safe_str(prev_sma20),
            "sma_50": _safe_str(sma50),
            "prev_sma_50": _safe_str(prev_sma50),
            "sma_200": _safe_str(sma200),
            "prev_sma_200": _safe_str(prev_sma200),
            "macd": _safe_str(macd_val),
            "prev_macd": _safe_str(prev_macd_val),
            "macd_signal": _safe_str(macd_signal),
            "prev_macd_signal": _safe_str(prev_macd_signal),
            "atr_14": _safe_str(atr),
            "adx_14": _safe_str(adx_val),
            "vwap": _safe_str(vwap),
            "bollinger_upper": _safe_str(bb_upper),
            "bollinger_lower": _safe_str(bb_lower),
            "bollinger_mid": _safe_str(bb_mid),
            "sma_20_volume": _safe_str(vol_sma20),
            "change_pct": _safe_str(change_pct),
            "high_52w": _safe_str(high_52w),
            "low_52w": _safe_str(low_52w),
        }

        # --- Daily OHLCV records for chart rendering (avoids DB dependency) ---
        ohlcv_records: list[dict[str, Any]] = []
        for ts_idx, row in df.iterrows():
            epoch = int(ts_idx.timestamp()) if hasattr(ts_idx, "timestamp") else 0
            ohlcv_records.append({
                "time": epoch,
                "open": round(float(row.get("Open", 0)), 2),
                "high": round(float(row.get("High", 0)), 2),
                "low": round(float(row.get("Low", 0)), 2),
                "close": round(float(row.get("Close", 0)), 2),
                "volume": int(row.get("Volume", 0)),
            })

        return mapping, ohlcv_records

    # ------------------------------------------------------------------
    # Bulk compute
    # ------------------------------------------------------------------

    @staticmethod
    async def bulk_compute(symbols: list[str]) -> dict[str, bool]:
        """Compute and store indicators for all *symbols* in parallel batches.

        Runs BATCH_SIZE symbols concurrently, then waits briefly between
        batches to avoid Yahoo Finance rate-limiting.  For 50 symbols this
        cuts wall-clock time from ~75 s (sequential) to ~15 s (5 × batches).

        Returns a dict mapping symbol to success boolean.
        """
        # Batch size 3 (down from 5): lower peak RAM per batch (~120 MB vs ~200 MB).
        # Inter-batch delay 2 s (up from 1 s): lets GC reclaim memory between batches.
        _BATCH_SIZE = 3
        results: dict[str, bool] = {}
        total = len(symbols)

        for batch_start in range(0, total, _BATCH_SIZE):
            batch = symbols[batch_start : batch_start + _BATCH_SIZE]
            log.info(
                "bulk_compute_batch",
                start=batch_start + 1,
                end=batch_start + len(batch),
                total=total,
            )
            batch_results = await asyncio.gather(
                *[YFinanceProvider.compute_and_store_indicators(s) for s in batch],
                return_exceptions=True,
            )
            for symbol, result in zip(batch, batch_results):
                results[symbol] = result is True

            # Pause between batches — avoids Yahoo throttle and lets GC run
            if batch_start + _BATCH_SIZE < total:
                await asyncio.sleep(_RATE_LIMIT_DELAY * 4)  # 2 s between batches

        succeeded = sum(1 for v in results.values() if v)
        log.info("bulk_compute_done", total=total, succeeded=succeeded, failed=total - succeeded)
        return results

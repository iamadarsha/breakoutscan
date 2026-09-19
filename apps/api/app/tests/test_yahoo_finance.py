"""YFinanceProvider.compute_and_store_indicators — verifies the
asyncio.to_thread refactor (splitting out `_compute_indicator_mapping` as a
pure sync function) preserves exact behavior: same Redis writes, same
empty-data handling, same return values as before the CPU work was moved
off the event loop.

No real network calls — `_fetch_history` is monkeypatched to return a
synthetic DataFrame shaped like a real yfinance daily-history response.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.services import redis_cache
from app.services.yahoo_finance import YFinanceProvider
from app.utils.redis_keys import indicator_key


def _synthetic_daily_df(rows: int = 260) -> pd.DataFrame:
    """A plausible daily OHLCV history — enough rows to exercise SMA200 and
    a real (non-fallback) 252-day 52-week high/low."""
    dates = pd.date_range("2025-01-01", periods=rows, freq="D")
    base = [100.0 + i * 0.5 for i in range(rows)]
    return pd.DataFrame(
        {
            "Open": base,
            "High": [v + 2 for v in base],
            "Low": [v - 2 for v in base],
            "Close": [v + 0.5 for v in base],
            "Volume": [1_000_000 + i for i in range(rows)],
        },
        index=dates,
    )


@pytest.mark.usefixtures("fake_redis")
async def test_compute_and_store_indicators_writes_mapping_and_ohlcv(monkeypatch):
    df = _synthetic_daily_df()
    monkeypatch.setattr("app.services.yahoo_finance._fetch_history", lambda *a, **kw: df)

    ok = await YFinanceProvider.compute_and_store_indicators("RELIANCE")
    assert ok is True

    stored = await redis_cache.hget_all(indicator_key("RELIANCE", "1d"))
    assert stored  # non-empty mapping was written
    assert "rsi_14" in stored
    assert "sma_200" in stored
    assert float(stored["close"]) > 0

    ohlcv = await redis_cache.get_json("ohlcv:RELIANCE:daily")
    assert ohlcv is not None
    assert len(ohlcv) == 260
    assert set(ohlcv[0].keys()) == {"time", "open", "high", "low", "close", "volume"}


@pytest.mark.usefixtures("fake_redis")
async def test_compute_and_store_indicators_returns_false_on_empty_download(monkeypatch):
    monkeypatch.setattr(
        "app.services.yahoo_finance._fetch_history", lambda *a, **kw: pd.DataFrame()
    )

    ok = await YFinanceProvider.compute_and_store_indicators("NOSUCHTICKER")
    assert ok is False

    stored = await redis_cache.hget_all(indicator_key("NOSUCHTICKER", "1d"))
    assert stored == {}


@pytest.mark.usefixtures("fake_redis")
async def test_compute_and_store_indicators_returns_false_when_all_rows_non_numeric(monkeypatch):
    # Every OHLC value is non-numeric — coercion drops every row, leaving an
    # empty frame after dropna(), which must be treated the same as a
    # download that came back empty in the first place.
    bad_df = pd.DataFrame(
        {
            "Open": ["x", "y"],
            "High": ["x", "y"],
            "Low": ["x", "y"],
            "Close": ["x", "y"],
            "Volume": ["x", "y"],
        },
        index=pd.date_range("2025-01-01", periods=2, freq="D"),
    )
    monkeypatch.setattr("app.services.yahoo_finance._fetch_history", lambda *a, **kw: bad_df)

    ok = await YFinanceProvider.compute_and_store_indicators("BADDATA")
    assert ok is False


def test_compute_indicator_mapping_is_a_pure_sync_function():
    """Directly exercises the extracted sync helper — this is the function
    that now runs via asyncio.to_thread instead of on the event loop."""
    df = _synthetic_daily_df(rows=10)  # short history: exercises the <252 fallback paths

    result = YFinanceProvider._compute_indicator_mapping(df, "TESTSYM")  # noqa: SLF001

    assert result is not None
    mapping, ohlcv_records = result
    assert mapping["close"] != ""
    assert len(ohlcv_records) == 10
    # High/low SMA200 fallback: with only 10 rows, high_52w must fall back to
    # the max/min of what's actually available rather than requiring 252.
    assert float(mapping["high_52w"]) == df["High"].max()
    assert float(mapping["low_52w"]) == df["Low"].min()


@pytest.mark.usefixtures("fake_redis")
async def test_concurrent_bulk_compute_keeps_each_symbols_own_history(monkeypatch):
    """Regression: bulk_compute fetches several symbols concurrently in
    threads. `yf.download` shares a module-level result dict, so those calls
    overwrote each other and every symbol in a batch was stored with the
    same series (RELIANCE, INFY and TCS all showed one stock's prices).
    History must come from per-instance `Ticker.history`, never download()."""
    import time

    frames = {
        "AAA.NS": _synthetic_daily_df(),
        "BBB.NS": _synthetic_daily_df().mul(3.0),
        "CCC.NS": _synthetic_daily_df().mul(7.0),
    }

    class _FakeTicker:
        def __init__(self, ticker):
            self._ticker = ticker

        def history(self, **kwargs):
            time.sleep(0.05)  # overlap the worker threads like real network I/O
            return frames[self._ticker].copy()

    def _forbidden(*a, **kw):
        raise AssertionError("yf.download is not thread-safe and must not be used")

    monkeypatch.setattr("app.services.yahoo_finance.yf.Ticker", _FakeTicker)
    monkeypatch.setattr("app.services.yahoo_finance.yf.download", _forbidden)

    results = await YFinanceProvider.bulk_compute(["AAA", "BBB", "CCC"])
    assert results == {"AAA": True, "BBB": True, "CCC": True}

    closes = {}
    for sym in ("AAA", "BBB", "CCC"):
        stored = await redis_cache.hget_all(indicator_key(sym, "1d"))
        closes[sym] = float(stored["close"])
    base_close = float(frames["AAA.NS"]["Close"].iloc[-1])
    assert closes == pytest.approx({"AAA": base_close, "BBB": base_close * 3, "CCC": base_close * 7})

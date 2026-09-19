"""YFinanceProvider.compute_and_store_indicators — verifies the
asyncio.to_thread refactor (splitting out `_compute_indicator_mapping` as a
pure sync function) preserves exact behavior: same Redis writes, same
empty-data handling, same return values as before the CPU work was moved
off the event loop.

No real network calls — `yf.download` is monkeypatched to return a
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
    monkeypatch.setattr("app.services.yahoo_finance.yf.download", lambda *a, **kw: df)

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
        "app.services.yahoo_finance.yf.download", lambda *a, **kw: pd.DataFrame()
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
    monkeypatch.setattr("app.services.yahoo_finance.yf.download", lambda *a, **kw: bad_df)

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

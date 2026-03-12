"""
Historical data loader using yfinance.
Fetches historical daily/weekly OHLCV data for backfilling and long-term indicator calculation.
"""
from __future__ import annotations
import asyncio
import yfinance as yf
import pandas as pd
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)

async def fetch_historical_data(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical data for a given symbol from Yahoo Finance.
    Symbol should ideally be mapped to the Yahoo Finance ticker format (e.g., RELIANCE.NS)
    """
    yf_symbol = f"{symbol}.NS"
    try:
        # Run synchronous yfinance call in an executor
        df = await asyncio.to_thread(
            yf.download, yf_symbol, period=period, interval=interval, progress=False
        )
        
        if df.empty:
            logger.warning("no_historical_data_returned", symbol=symbol, yf_symbol=yf_symbol)
            return pd.DataFrame()
            
        # Clean column names
        df.reset_index(inplace=True)
        df.rename(columns={
            "Date": "timestamp",
            "Datetime": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)
        
        logger.info("historical_data_fetched", symbol=symbol, rows=len(df), period=period, interval=interval)
        return df
        
    except Exception as e:
        logger.error("error_fetching_historical_data", symbol=symbol, yf_symbol=yf_symbol, error=str(e))
        return pd.DataFrame()

async def backfill_symbols(symbols: list[str]):
    """
    Backfill multiple symbols concurrently.
    """
    tasks = [fetch_historical_data(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

"""Populate stocks.pe/pb/roe/debt_equity/div_yield/market_cap from Yahoo Finance.

Nothing else in the app writes these columns, so without this job every
Fundamentals filter and preset returns an empty table. Deliberately
sequential and throttled: ~500 symbols take roughly ten minutes, which is
fine for a once-a-day refresh and keeps memory/CPU flat on a small box.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import func, select, update

from app.db.models.stock import Stock
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 24 * 60 * 60
STARTUP_DELAY_SECONDS = 180
REQUEST_DELAY_SECONDS = 0.6
COMMIT_EVERY = 25
MAX_DIV_YIELD_PCT = 50.0


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num != num or num in (float("inf"), float("-inf")):
        return None
    return num


def normalize_yahoo_info(info: dict[str, Any]) -> dict[str, float | None]:
    """Map Yahoo's `Ticker.info` onto this app's units.

    pe/pb: raw ratios; negative P/E (loss-making) is stored as NULL, as
    screeners do, so "PE below 15" never matches a company with losses.
    roe: percent (Yahoo gives a fraction). debt_equity: plain ratio (Yahoo
    gives percent). div_yield: percent (Yahoo's dividendYield is already
    percent; the trailing annual figure is a fraction and is the fallback).
    market_cap: rupees.
    """
    pe = _num(info.get("trailingPE"))
    if pe is not None and pe <= 0:
        pe = None

    pb = _num(info.get("priceToBook"))
    if pb is not None and pb <= 0:
        pb = None

    roe_frac = _num(info.get("returnOnEquity"))
    roe = round(roe_frac * 100, 2) if roe_frac is not None else None

    de_pct = _num(info.get("debtToEquity"))
    debt_equity = round(de_pct / 100, 4) if de_pct is not None else None

    div_yield = _num(info.get("dividendYield"))
    if div_yield is None:
        trailing = _num(info.get("trailingAnnualDividendYield"))
        div_yield = round(trailing * 100, 2) if trailing is not None else None
    if div_yield is not None and not (0 <= div_yield <= MAX_DIV_YIELD_PCT):
        div_yield = None

    market_cap = _num(info.get("marketCap"))
    if market_cap is not None and market_cap <= 0:
        market_cap = None

    return {
        "pe": pe,
        "pb": pb,
        "roe": roe,
        "debt_equity": debt_equity,
        "div_yield": div_yield,
        "market_cap": market_cap,
    }


def _fetch_info(symbol: str) -> dict[str, Any]:
    import yfinance as yf

    return yf.Ticker(f"{symbol}.NS").info or {}


async def refresh_fundamentals(symbols: list[str] | None = None) -> dict[str, int]:
    """Refresh the given symbols (default: every active NIFTY 500 stock)."""
    if symbols is None:
        async with SessionLocal() as session:
            symbols = list(
                (
                    await session.execute(
                        select(Stock.symbol).where(
                            Stock.is_active.is_(True), Stock.is_nifty500.is_(True)
                        )
                    )
                ).scalars()
            )

    updated = failed = 0
    session = SessionLocal()
    try:
        for i, symbol in enumerate(symbols, start=1):
            try:
                info = await asyncio.to_thread(_fetch_info, symbol)
                values = {k: v for k, v in normalize_yahoo_info(info).items() if v is not None}
                if values:
                    await session.execute(
                        update(Stock).where(Stock.symbol == symbol).values(**values)
                    )
                    updated += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                logger.debug("fundamentals refresh failed for %s: %s", symbol, exc)
            if i % COMMIT_EVERY == 0:
                await session.commit()
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
        await session.commit()
    finally:
        await session.close()

    logger.info("fundamentals_refresh done updated=%d failed=%d", updated, failed)
    return {"updated": updated, "failed": failed, "total": len(symbols)}


async def _count_populated() -> int:
    async with SessionLocal() as session:
        return (
            await session.execute(
                select(func.count()).select_from(Stock).where(Stock.pe.isnot(None))
            )
        ).scalar_one()


async def fundamentals_refresh_loop() -> None:
    """Refresh once shortly after boot if the table is mostly empty, then daily."""
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    first = True
    while True:
        try:
            if not first or await _count_populated() < 100:
                logger.info("fundamentals_refresh starting")
                await refresh_fundamentals()
            else:
                logger.info("fundamentals_refresh skipped at boot: table already populated")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("fundamentals_refresh cycle failed")
        first = False
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

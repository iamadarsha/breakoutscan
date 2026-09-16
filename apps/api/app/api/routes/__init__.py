"""HTTP route modules for BreakoutScan."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    ai_suggestions,
    alerts,
    auth,
    breakouts,
    company_info,
    fundamentals,
    indices,
    market,
    prices,
    screener,
    stock_analysis,
    stocks,
    watchlist,
)

api_router = APIRouter()

# Auth routes (no /api prefix - lives at /auth/*)
api_router.include_router(auth.router)

# API routes
api_router.include_router(stocks.router)
api_router.include_router(screener.router)
api_router.include_router(prices.router)
api_router.include_router(market.router)
api_router.include_router(watchlist.router)
api_router.include_router(alerts.router)
api_router.include_router(fundamentals.router)
api_router.include_router(indices.router)
api_router.include_router(ai_suggestions.router)
api_router.include_router(company_info.router)
api_router.include_router(stock_analysis.router)
api_router.include_router(breakouts.router)

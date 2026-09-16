"""Per-symbol BUY/SELL/HOLD AI analysis, shown below the chart."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.services.stock_analysis import get_or_generate_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stocks", tags=["stock-analysis"])


@router.get("/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """BUY/SELL/HOLD call for one symbol: Groq + targeted news, falling back
    to deterministic technical scoring if no AI provider is available."""
    try:
        return await get_or_generate_analysis(symbol.upper())
    except Exception as e:
        logger.error("stock_analysis_route_failed symbol=%s error=%s", symbol, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate stock analysis") from e

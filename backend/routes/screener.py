"""
Screener API routes.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import redis.asyncio as aioredis
import structlog

from schemas import ScanRunRequest, ScanRunResponse, ScanResult as ScanResultSchema, PrebuiltScan
from screener.engine import evaluate_scan, run_prebuilt_scan, _DEMO_LTP_DATA
from screener.prebuilt_scans import list_prebuilt_scans, get_prebuilt_scan
from data.indicator_engine import get_indicator_engine

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/screener", tags=["screener"])


def get_redis() -> aioredis.Redis:
    from main import get_redis_client
    return get_redis_client()


@router.get("/prebuilt", response_model=list[PrebuiltScan])
async def get_prebuilt_scans():
    """List all pre-built scan definitions."""
    return list_prebuilt_scans()


@router.post("/run")
async def run_scan(request: ScanRunRequest):
    """
    Execute a scan against the screener universe.
    Returns matched stocks with indicators.
    """
    redis = get_redis()
    ie = get_indicator_engine()

    # Convert schema to dict
    conditions = [c.model_dump() for c in request.conditions]
    filters = request.filters.model_dump() if request.filters else {}

    results, duration_ms = await evaluate_scan(
        conditions=conditions,
        filters=filters,
        timeframe=request.timeframe,
        universe=request.universe,
        redis=redis,
        indicator_engine=ie,
    )

    return {
        "scan_name": request.scan_name or "Custom Scan",
        "timeframe": request.timeframe,
        "universe": request.universe,
        "results": [r.to_dict() for r in results],
        "result_count": len(results),
        "duration_ms": duration_ms,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/prebuilt/{scan_id}/run")
async def run_prebuilt_scan_endpoint(scan_id: str):
    """Run a specific pre-built scan by ID."""
    scan_def = get_prebuilt_scan(scan_id)
    if not scan_def:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")

    redis = get_redis()
    ie = get_indicator_engine()

    try:
        results, duration_ms = await run_prebuilt_scan(scan_id, redis, ie)
        return {
            "scan_name": scan_def["name"],
            "timeframe": scan_def["timeframe"],
            "universe": "NSE_ALL",
            "results": [r.to_dict() for r in results],
            "result_count": len(results),
            "duration_ms": duration_ms,
            "run_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.error("prebuilt_scan_error", scan_id=scan_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/latest")
async def get_latest_results():
    """Get latest scan results from real scans."""
    redis = get_redis()
    ie = get_indicator_engine()

    results = []
    scan_ids = ["ema_921_crossover", "macd_bullish_cross", "volume_surge_breakout", "orb_breakout"]

    for scan_id in scan_ids:
        try:
            scan_results, _ = await run_prebuilt_scan(scan_id, redis, ie)
            scan_def = get_prebuilt_scan(scan_id)
            for r in scan_results[:3]:
                results.append({
                    "symbol": r.symbol,
                    "scan_name": scan_def["name"] if scan_def else scan_id,
                    "scan_id": scan_id,
                    "ltp": r.ltp,
                    "change_pct": r.change_pct,
                    "volume": r.volume,
                    "rsi_14": r.rsi_14,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception:
            pass

    return {"results": results[:15], "total": len(results)}

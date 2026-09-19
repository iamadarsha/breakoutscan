from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.common import ErrorResponse
from app.services.stock_names import company_name_for
from app.schemas.screener import (
    CustomScanRequest,
    PrebuiltScanOut,
    ScanRequest,
    ScanResult,
)
from app.utils.redis_keys import scan_result_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["screener"])


async def _enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    """Enrich a scan result item with indicator data from Redis."""
    from app.services.redis_cache import hget_all
    from app.utils.redis_keys import indicator_key

    symbol = item.get("symbol", "")
    if not symbol:
        return item

    try:
        ind_key = indicator_key(symbol, "1d")
        indicators = await hget_all(ind_key)
        if not indicators:
            return item

        # RSI 14
        rsi_raw = indicators.get("rsi_14")
        if rsi_raw is not None:
            try:
                item["rsi_14"] = round(float(rsi_raw), 2)
            except (ValueError, TypeError):
                pass

        # EMA status: bullish if ema_9 > ema_21
        ema_9_raw = indicators.get("ema_9")
        ema_21_raw = indicators.get("ema_21")
        if ema_9_raw is not None and ema_21_raw is not None:
            try:
                ema_9 = float(ema_9_raw)
                ema_21 = float(ema_21_raw)
                item["ema_status"] = "Bullish" if ema_9 > ema_21 else "Bearish"
            except (ValueError, TypeError):
                pass

        # Volume
        vol_raw = indicators.get("volume")
        if vol_raw is not None:
            try:
                item["volume"] = float(vol_raw)
            except (ValueError, TypeError):
                pass

        # Signal strength from score if available in engine data
        if item.get("score") is not None:
            item["signal_strength"] = item["score"]

    except Exception as e:
        logger.debug("enrich_item_failed symbol=%s error=%s", symbol, e)

    return item


async def _enrich_items(items: list[dict[str, Any]], conditions: list[str] | None = None) -> list[dict[str, Any]]:
    """Enrich a list of scan result items with indicator data."""
    enriched = []
    for item in items:
        item = await _enrich_item(item)
        if conditions:
            item["matched_conditions"] = conditions
        enriched.append(item)
    return enriched


@router.get("/prebuilt", response_model=list[PrebuiltScanOut])
@limiter.limit(get_settings().rate_limit_default)
async def list_prebuilt_scans(request: Request):
    """Return all available prebuilt scans."""
    try:
        from app.services.prebuilt_scans import get_prebuilt_scans

        scans = get_prebuilt_scans()
        out = []
        for s in scans:
            # Convert Condition dataclasses to dicts for Pydantic serialization
            s_copy = dict(s)
            if "conditions" in s_copy and s_copy["conditions"]:
                from dataclasses import asdict, fields

                s_copy["conditions"] = [
                    asdict(c) if hasattr(c, "__dataclass_fields__") else c
                    for c in s_copy["conditions"]
                ]
            out.append(PrebuiltScanOut(**s_copy))
        return out
    except Exception as exc:
        logger.exception("Failed to load prebuilt scans")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/run", response_model=ScanResult)
@limiter.limit(get_settings().rate_limit_screener)
async def run_prebuilt_scan(request: Request, req: ScanRequest):
    """Run a prebuilt scan by ID and return matching symbols."""
    try:
        from app.services.prebuilt_scans import get_scan_by_id
        from app.services.screener_engine import ScreenerEngine

        scan_def = get_scan_by_id(req.scan_id)
        if not scan_def:
            raise HTTPException(
                status_code=404, detail=f"Scan '{req.scan_id}' not found"
            )

        engine = ScreenerEngine()
        results = await engine.run_prebuilt_scan(
            scan_id=req.scan_id,
            universe=req.universe,
        )

        # Extract condition names from scan definition (Condition dataclasses)
        condition_names = []
        for c in (scan_def.get("conditions") or []):
            if hasattr(c, "left") and hasattr(c.left, "name"):
                condition_names.append(c.left.name)
            elif isinstance(c, dict):
                condition_names.append(c.get("indicator", c.get("name", "")))

        # Transform engine results to ScanResultItem format
        items = []
        for r in results:
            data = r.get("data", {})
            items.append({
                "symbol": r.get("symbol", ""),
                "company_name": company_name_for(r.get("symbol", "")),
                "ltp": float(data.get("close", 0) or 0),
                "change_pct": float(data.get("change_pct", 0) or 0),
                "sector": data.get("sector", ""),
                "matched_conditions": condition_names if condition_names else [],
                "score": float(data.get("score", 0) or 0) if data.get("score") else None,
            })

        # Enrich with indicator data from Redis
        items = await _enrich_items(items)

        result = ScanResult(
            scan_id=req.scan_id,
            scan_name=scan_def.get("name", req.scan_id),
            description=scan_def.get("description"),
            run_at=datetime.now(timezone.utc),
            total_matches=len(items),
            items=items,
        )
        await _cache_scan_result(req.scan_id, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Scan run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/custom", response_model=ScanResult)
@limiter.limit(get_settings().rate_limit_screener)
async def run_custom_scan(request: Request, req: CustomScanRequest):
    """Run a custom scan with user-defined conditions.

    Accepts either the legacy flat `conditions` shape (unchanged, still
    the 5-operator gt/lt/eq/cross_above/cross_below format) or the new
    nested `dsl` shape (real AND/OR/NOT, historical offsets, rolling
    functions — see app.screener.dsl). `dsl` takes precedence when both
    are somehow present.
    """
    try:
        from app.services.screener_engine import ScreenerEngine

        engine = ScreenerEngine()
        scan_id = f"custom-{uuid.uuid4().hex[:12]}"

        if req.dsl is not None:
            from app.screener.dsl.parser import DslParseError, parse_scan
            from app.screener.dsl.validator import DslValidationError, validate

            try:
                dsl_root = parse_scan(req.dsl)
                validate(dsl_root, timeframe=req.timeframe)
            except (DslParseError, DslValidationError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

            results = await engine.run_custom_scan(
                conditions=[],
                universe=req.universe,
                timeframe=req.timeframe,
                dsl_root=dsl_root,
            )
            condition_names: list[str] = []
        else:
            conditions_raw = [c.model_dump() for c in req.conditions]
            results = await engine.run_custom_scan(
                conditions=conditions_raw,
                universe=req.universe,
                timeframe=req.timeframe,
            )
            condition_names = [
                c.get("indicator", "")
                for c in conditions_raw
                if c.get("indicator")
            ]

        # Transform engine results to ScanResultItem format
        items = []
        for r in results:
            data = r.get("data", {})
            items.append({
                "symbol": r.get("symbol", ""),
                "company_name": company_name_for(r.get("symbol", "")),
                "ltp": float(data.get("close", 0) or 0),
                "change_pct": float(data.get("change_pct", 0) or 0),
                "sector": data.get("sector", ""),
                "matched_conditions": condition_names if condition_names else [],
                "score": float(data.get("score", 0) or 0) if data.get("score") else None,
            })

        # Enrich with indicator data from Redis
        items = await _enrich_items(items)

        result = ScanResult(
            scan_id=scan_id,
            scan_name=req.name or "Custom Scan",
            run_at=datetime.now(timezone.utc),
            total_matches=len(items),
            items=items,
        )
        await _cache_scan_result(scan_id, result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Custom scan failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _cache_scan_result(scan_id: str, result: ScanResult) -> None:
    """Store a finished ScanResult so `/results/{scan_id}` can retrieve it.

    Uses `scan_result_key()` — previously this route read from a different,
    literal `f"scan_result:{scan_id}"` key that nothing ever wrote to
    (found during the Phase 3.1 audit), so `/results/{scan_id}` was dead on
    arrival regardless of what scan_id was passed. Fixed by having both the
    writer (here) and the reader (`get_cached_results` below) agree on the
    same key helper.
    """
    from app.services.redis_cache import set_json

    await set_json(scan_result_key(scan_id), result.model_dump(mode="json"), ttl=3600)


@router.get("/results/{scan_id}", response_model=ScanResult)
@limiter.limit(get_settings().rate_limit_default)
async def get_cached_results(request: Request, scan_id: str):
    """Get cached scan results by scan ID."""
    try:
        from app.services.redis_cache import get_json

        cached = await get_json(scan_result_key(scan_id))
        if not cached:
            raise HTTPException(
                status_code=404, detail=f"No cached results for scan '{scan_id}'"
            )
        return ScanResult(**cached)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch cached results")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

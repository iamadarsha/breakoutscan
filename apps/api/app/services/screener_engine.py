"""Main screener execution engine.

Loads universe symbols from Redis, batch-fetches indicator hashes via
pipeline, evaluates conditions, and returns matches -- optimised for
sub-1.5 s on 500 symbols.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from decimal import Decimal
from typing import Any

import structlog

from app.screener.dsl.ast import BoolNode
from app.screener.dsl.compiler import compile_scan
from app.screener.dsl.evaluator import EvalContext
from app.screener.dsl.evaluator import evaluate as dsl_evaluate
from app.services.condition_evaluator import (
    Condition,
    Operand,
    evaluate_conditions,
)
from app.patterns.pattern_detector import detect_patterns
from app.patterns.types import PatternMatch
from app.services.orb import ORBDetector
from app.services.prebuilt_scans import ScanDefinition, get_scan_by_id
from app.services.redis_cache import get_redis
from app.utils.decimals import safe_decimal
from app.utils.redis_keys import (
    indicator_key,
    ltp_symbol_key,
    orb_range_key,
    scan_result_key,
    universe_key,
)

log = structlog.get_logger(__name__)

_SCAN_RESULT_TTL: int = 30  # seconds

# NOTE: the CPU-bound evaluation loop below (`_evaluate_matches`) was briefly
# run via `asyncio.to_thread` on 2026-09-15 to keep it off the event loop,
# the same fix that worked well for yfinance's indicator math. It made
# things *worse* here: this VM was found to be actively thrashing on swap
# (498MB RAM, ~372MB swap in use, continuous swap I/O) at the time, and
# extra OS threads add memory overhead with no CPU-parallelism benefit for
# pure-Python (non-numpy) work under GIL contention on a 1-2 vCPU box.
# Reverted to a plain synchronous call — kept as its own function for
# readability, not for threading.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan_hash(scan_def: ScanDefinition, universe: str) -> str:
    """Deterministic hash of a scan definition for cache keying."""
    payload = json.dumps(
        {
            "id": scan_def.get("id", ""),
            "conditions": str(scan_def.get("conditions", [])),
            "dsl_root": str(scan_def.get("dsl_root", "")),
            "pattern": scan_def.get("pattern", ""),
            "universe": universe,
            "timeframe": scan_def.get("timeframe", "1d"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _enrich_symbol_data(
    data: dict[str, str | None],
    orb_data: dict[str, str] | None = None,
) -> dict[str, str | None]:
    """Inject synthetic / derived fields that prebuilt scans expect.

    Mutations are applied **in-place** for performance (called per symbol).
    """
    # -- bollinger_width_pct ---------------------------------------------------
    bb_upper = safe_decimal(data.get("bollinger_upper"))
    bb_lower = safe_decimal(data.get("bollinger_lower"))
    sma_20 = safe_decimal(data.get("sma_20"))  # used as BB mid approximation
    if bb_upper is not None and bb_lower is not None and sma_20 and sma_20 != 0:
        data["bollinger_mid"] = str(sma_20)
        data["bollinger_width_pct"] = str((bb_upper - bb_lower) / sma_20)

    # -- volume_sma_20 (2x threshold) -----------------------------------------
    vol_sma = safe_decimal(data.get("sma_20_volume"))
    if vol_sma is not None:
        data["volume_sma_20"] = str(vol_sma * 2)

    # -- high_52w_95 -----------------------------------------------------------
    high_52w = safe_decimal(data.get("high_52w"))
    if high_52w is not None:
        data["high_52w_95"] = str(high_52w * Decimal("0.95"))

    # -- ORB range fields ------------------------------------------------------
    if orb_data:
        data["orb_high"] = orb_data.get("high")
        data["orb_low"] = orb_data.get("low")

    return data


def _evaluate_matches(
    symbol_list: list[str],
    indicator_results: list[dict[str, str]],
    orb_map: dict[str, dict[str, str]],
    dsl_root: BoolNode | None,
    candle_histories: dict[str, list[dict[str, Any]]],
    conditions: list[Condition],
    pattern_name: str | None,
) -> list[dict[str, Any]]:
    """Pure, synchronous CPU work — safe to run via ``asyncio.to_thread``.

    Everything this needs (indicator hashes, candle histories, ORB ranges)
    is already fetched into plain dicts/lists by the caller; no I/O happens
    in here.
    """
    matches: list[dict[str, Any]] = []

    for sym, raw_data in zip(symbol_list, indicator_results):
        if not raw_data:
            continue

        data = _enrich_symbol_data(raw_data, orb_map.get(sym))

        # DSL-based matching (new nested AND/OR/NOT + historical offsets
        # + rolling functions — see app.screener.dsl)
        if dsl_root is not None:
            eval_ctx = EvalContext(
                indicator_data=data, candles=candle_histories.get(sym, [])
            )
            if not dsl_evaluate(dsl_root, eval_ctx):
                continue

        # condition-based matching (existing flat AND-only path,
        # unchanged — still used by all 13 prebuilt scans)
        if conditions:
            if not evaluate_conditions(conditions, data, logic="AND"):
                continue

        # pattern-based matching -- real chronological candle history
        # (Postgres-backed, oldest-first) rather than the indicator
        # hash's single now+prev-bar pair, so 3-candle candlestick
        # patterns and structural (pivot-based) patterns can actually
        # fire.
        detected_patterns: list[PatternMatch] = []
        if pattern_name:
            detected_patterns = detect_patterns(candle_histories.get(sym, []))
            if not any(p.name == pattern_name for p in detected_patterns):
                continue

        # A scan must have at least one filter.
        if not conditions and not pattern_name and dsl_root is None:
            continue

        matches.append(
            {
                "symbol": sym,
                "data": {k: v for k, v in data.items() if v is not None},
                "patterns": [
                    {
                        "name": p.name,
                        "confidence": p.confidence,
                        "direction": p.direction.value,
                        "support": str(p.support) if p.support is not None else None,
                        "resistance": (
                            str(p.resistance) if p.resistance is not None else None
                        ),
                    }
                    for p in detected_patterns
                ],
            }
        )

    # --- sort by relevance (RSI distance from extreme, volume ratio, etc.)
    matches.sort(key=lambda m: m["symbol"])
    return matches


# ---------------------------------------------------------------------------
# ScreenerEngine
# ---------------------------------------------------------------------------

class ScreenerEngine:
    """Execute scans against the live indicator store in Redis."""

    def __init__(self) -> None:
        self._redis = None
        self._orb = ORBDetector()

    async def _get_redis(self):
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    # ------------------------------------------------------------------
    # Core scan runner
    # ------------------------------------------------------------------

    async def run_scan(
        self,
        scan_definition: ScanDefinition,
        universe: str = "nifty500",
    ) -> list[dict[str, Any]]:
        """Execute a scan and return matching symbols with their data.

        Parameters
        ----------
        scan_definition:
            A dict with at least ``conditions`` (list of
            :class:`Condition`) and optionally ``pattern``, ``timeframe``,
            ``meta``.
        universe:
            Redis set name (without prefix) -- ``"nifty50"`` or
            ``"nifty500"``.

        Returns
        -------
        list[dict]
            Each entry: ``{"symbol": str, "data": dict, "patterns": list}``.
        """
        t0 = time.perf_counter()
        redis = await self._get_redis()

        # --- check cache ------------------------------------------------------
        cache_key = scan_result_key(_scan_hash(scan_definition, universe))
        cached = await redis.get(cache_key)
        if cached:
            log.info("scan_cache_hit", cache_key=cache_key)
            return json.loads(cached)

        # --- load universe ----------------------------------------------------
        symbols: set[str] = await redis.smembers(universe_key(universe))
        if not symbols:
            log.warning("scan_empty_universe", universe=universe)
            return []

        symbol_list = sorted(symbols)
        timeframe: str = scan_definition.get("timeframe", "1d")
        conditions: list[Condition] = scan_definition.get("conditions", [])
        pattern_name: str | None = scan_definition.get("pattern")
        dsl_root: BoolNode | None = scan_definition.get("dsl_root")

        # --- batch fetch indicators (pipeline) --------------------------------
        pipe = redis.pipeline(transaction=False)
        for sym in symbol_list:
            pipe.hgetall(indicator_key(sym, timeframe))
        indicator_results: list[dict[str, str]] = await pipe.execute()

        # --- DSL scans: fetch candle history only if the compiled scan
        # actually needs it (historical offsets / rolling functions) ----------
        candle_histories: dict[str, list[dict[str, Any]]] = {}
        if dsl_root is not None:
            compiled_dsl = compile_scan(dsl_root)
            if any(r.needs_history for r in compiled_dsl.requirements):
                candle_histories = await _fetch_candle_histories(symbol_list, timeframe)

        # --- pattern scans: real chronological multi-candle history is
        # required for 3-candle candlestick patterns and every structural
        # (pivot-based) pattern -- reuse the DSL fetch above when it already
        # ran, otherwise fetch it now (Postgres-backed, up to 210 candles). --
        if pattern_name and not candle_histories:
            candle_histories = await _fetch_candle_histories(symbol_list, timeframe)

        # --- optionally fetch ORB data (only for ORB scans) -------------------
        orb_map: dict[str, dict[str, str]] = {}
        needs_orb = any(
            (
                getattr(c.left, "name", "") in ("orb_high", "orb_low")
                or getattr(c.right, "name", "") in ("orb_high", "orb_low")
            )
            for c in conditions
        )
        if needs_orb:
            orb_pipe = redis.pipeline(transaction=False)
            for sym in symbol_list:
                orb_pipe.hgetall(orb_range_key(sym))
            orb_results: list[dict[str, str]] = await orb_pipe.execute()
            for sym, orb_data in zip(symbol_list, orb_results):
                if orb_data:
                    orb_map[sym] = orb_data

        # --- evaluate -----------------------------------------------------
        matches = _evaluate_matches(
            symbol_list,
            indicator_results,
            orb_map,
            dsl_root,
            candle_histories,
            conditions,
            pattern_name,
        )

        # --- cache results ----------------------------------------------------
        await redis.set(
            cache_key,
            json.dumps(matches),
            ex=_SCAN_RESULT_TTL,
        )

        elapsed = time.perf_counter() - t0
        log.info(
            "scan_complete",
            scan_id=scan_definition.get("id", "custom"),
            universe=universe,
            symbols_checked=len(symbol_list),
            matches=len(matches),
            elapsed_ms=round(elapsed * 1000, 1),
        )

        return matches

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    async def run_prebuilt_scan(
        self,
        scan_id: str,
        universe: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run one of the 12 prebuilt scans by its id.

        Raises ``ValueError`` if *scan_id* is unknown.
        """
        scan_def = get_scan_by_id(scan_id)
        if scan_def is None:
            raise ValueError(f"Unknown prebuilt scan: {scan_id!r}")
        univ = universe or scan_def.get("universe", "nifty500")
        return await self.run_scan(scan_def, universe=univ)

    async def run_custom_scan(
        self,
        conditions: list[Condition | dict],
        universe: str = "nifty500",
        timeframe: str = "1d",
        pattern: str | None = None,
        dsl_root: BoolNode | None = None,
    ) -> list[dict[str, Any]]:
        """Build an ad-hoc scan definition and execute it.

        If `dsl_root` is given (an already-parsed-and-validated tree from
        `app.screener.dsl`), it's evaluated via the new DSL engine and
        `conditions` is ignored — see the route layer
        (`app/api/routes/screener.py`) for where the `dsl` vs `conditions`
        request fields are dispatched.
        """
        if dsl_root is not None:
            scan_def: ScanDefinition = {
                "id": "custom",
                "dsl_root": dsl_root,
                "timeframe": timeframe,
            }
            if pattern:
                scan_def["pattern"] = pattern
            return await self.run_scan(scan_def, universe=universe)

        from app.services.condition_evaluator import (
            ConditionOperator,
            IndicatorRef,
            INDICATOR_NAMES,
            NumericLiteral,
        )

        # Convert dict conditions to Condition objects if needed
        parsed_conditions: list[Condition] = []
        for c in conditions:
            if isinstance(c, Condition):
                parsed_conditions.append(c)
            elif isinstance(c, dict):
                left = IndicatorRef(name=c.get("indicator", "close"))
                op_str = c.get("operator", "gt")
                op_map = {
                    "gt": ConditionOperator.GREATER_THAN,
                    "lt": ConditionOperator.LESS_THAN,
                    "eq": ConditionOperator.EQUALS,
                    "cross_above": ConditionOperator.CROSSES_ABOVE,
                    "cross_below": ConditionOperator.CROSSES_BELOW,
                }
                operator = op_map.get(op_str, ConditionOperator.GREATER_THAN)
                val = c.get("value", 0)
                if isinstance(val, str) and val in INDICATOR_NAMES:
                    right: Operand = IndicatorRef(name=val)
                else:
                    from decimal import Decimal as _Decimal

                    right = NumericLiteral(value=_Decimal(str(val)))
                parsed_conditions.append(
                    Condition(left=left, operator=operator, right=right)
                )

        scan_def: ScanDefinition = {
            "id": "custom",
            "conditions": parsed_conditions,
            "timeframe": timeframe,
        }
        if pattern:
            scan_def["pattern"] = pattern
        return await self.run_scan(scan_def, universe=universe)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _fetch_candle_histories(
    symbols: list[str], timeframe: str
) -> dict[str, list[dict[str, Any]]]:
    """Batch-fetch recent candle history for DSL scans that need historical
    offsets or rolling functions — reuses indicator_engine's per-symbol
    Postgres query (same table/limit conventions), run concurrently rather
    than sequentially to keep an N-symbol scan from serializing N round
    trips to the database.
    """
    from app.market.candles import fetch_candle_history

    results = await asyncio.gather(*(fetch_candle_history(sym, timeframe) for sym in symbols))
    return {sym: candles for sym, candles in zip(symbols, results) if candles}

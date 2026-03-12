"""
Screener Condition Evaluators.
Implements all 18 operators for comparing indicators against values or other indicators.
Each function takes pre-fetched indicator data and returns bool.
"""
from __future__ import annotations
from typing import Any, Optional
import structlog

log = structlog.get_logger(__name__)


def _get_val(indicators: dict, key: str, idx: int = 0) -> Optional[float]:
    """Safely retrieve value[idx] from indicators dict."""
    vals = indicators.get(key)
    if not vals or idx >= len(vals):
        return None
    return vals[idx]


def _resolve_indicator_value(
    indicators: dict,
    indicator: str,
    params: list,
    idx: int,
) -> Optional[float]:
    """Resolve an indicator name + params to a value from the cached indicators dict."""
    ind = indicator.lower()

    mapping = {
        "rsi": lambda p: _get_val(indicators, f"rsi_{int(p[0]) if p else 14}", idx),
        "ema": lambda p: _get_val(indicators, f"ema_{int(p[0]) if p else 20}", idx),
        "sma": lambda p: _get_val(indicators, f"sma_{int(p[0]) if p else 20}", idx),
        "close": lambda p: _get_val(indicators, "close", idx),
        "open": lambda p: _get_val(indicators, "open", idx),
        "high": lambda p: _get_val(indicators, "high", idx),
        "low": lambda p: _get_val(indicators, "low", idx),
        "volume": lambda p: _get_val(indicators, "volume", idx),
        "vwap": lambda p: _get_val(indicators, "vwap", idx),
        "macd_line": lambda p: _get_val(indicators, "macd_line", idx),
        "macd_signal": lambda p: _get_val(indicators, "macd_signal", idx),
        "macd_histogram": lambda p: _get_val(indicators, "macd_histogram", idx),
        "bollinger_upper": lambda p: _get_val(indicators, "bb_upper", idx),
        "bollingerupper": lambda p: _get_val(indicators, "bb_upper", idx),
        "bollinger_lower": lambda p: _get_val(indicators, "bb_lower", idx),
        "bollingerlower": lambda p: _get_val(indicators, "bb_lower", idx),
        "bollinger_middle": lambda p: _get_val(indicators, "bb_middle", idx),
        "band_width": lambda p: _get_val(indicators, "bb_width", idx),
        "atr": lambda p: _get_val(indicators, "atr_14", idx),
        "volume_sma": lambda p: _get_val(indicators, "volume_sma_20", idx),
        "volumesma": lambda p: _get_val(indicators, "volume_sma_20", idx),
        "volume_ratio": lambda p: _get_val(indicators, "volume_ratio", idx),
        "weekhigh52": lambda p: _get_val(indicators, "week_high_52", idx),
        "weeklow52": lambda p: _get_val(indicators, "week_low_52", idx),
        "prevdayhigh": lambda p: _get_val(indicators, "prev_day_high", idx),
        "prevdaylow": lambda p: _get_val(indicators, "prev_day_low", idx),
        "prevdayclose": lambda p: _get_val(indicators, "prev_day_close", idx),
        "supertrend": lambda p: _get_val(indicators, "supertrend_direction", idx),
    }

    # Normalize key
    ind_clean = ind.replace(" ", "").replace("_", "").lower()
    for key, resolver in mapping.items():
        if ind_clean == key.replace("_", "").lower():
            return resolver(params)

    log.warning("unknown_indicator", indicator=indicator)
    return None


def evaluate_condition(condition: dict, indicators: dict) -> bool:
    """
    Evaluate a single scan condition against pre-computed indicators.
    Returns True if the condition passes, False otherwise.
    """
    ind = condition.get("indicator", "")
    params = condition.get("params", [])
    operator = condition.get("operator", "").lower().replace(" ", "_")
    value = condition.get("value")
    compare_indicator = condition.get("compare_indicator")
    compare_params = condition.get("compare_params", [])
    lookback = condition.get("lookback", 0)

    # Current value (index = lookback)
    current = _resolve_indicator_value(indicators, ind, params, lookback)
    if current is None:
        return False

    # Compare target: either a number or another indicator
    if compare_indicator:
        target = _resolve_indicator_value(indicators, compare_indicator, compare_params or [], lookback)
    else:
        target = float(value) if value is not None else None

    if target is None:
        return False

    # ── Operator dispatch ────────────────────────────────────────────────────

    if operator in ("greater_than", "gt"):
        return current > target

    if operator in ("less_than", "lt"):
        return current < target

    if operator in ("equals", "eq"):
        return abs(current - target) < 0.001

    if operator in ("not_equals", "ne"):
        return abs(current - target) >= 0.001

    if operator == "greater_than_or_equal":
        return current >= target

    if operator == "less_than_or_equal":
        return current <= target

    if operator in ("crosses_above", "crossover_up"):
        # current[0] > target[0] AND current[1] < target[1]
        prev_current = _resolve_indicator_value(indicators, ind, params, lookback + 1)
        if compare_indicator:
            prev_target = _resolve_indicator_value(indicators, compare_indicator, compare_params or [], lookback + 1)
        else:
            prev_target = target
        if prev_current is None or prev_target is None:
            return False
        return current > target and prev_current <= prev_target

    if operator in ("crosses_below", "crossover_down"):
        prev_current = _resolve_indicator_value(indicators, ind, params, lookback + 1)
        if compare_indicator:
            prev_target = _resolve_indicator_value(indicators, compare_indicator, compare_params or [], lookback + 1)
        else:
            prev_target = target
        if prev_current is None or prev_target is None:
            return False
        return current < target and prev_current >= prev_target

    if operator == "within_percent":
        # abs(current - target) / target <= value%
        if not value or target == 0:
            return False
        pct_diff = abs(current - target) / abs(target) * 100
        return pct_diff <= float(value)

    if operator == "greater_than_percent_of":
        # current > (value% of target)
        if target == 0:
            return False
        threshold = target * (float(value) / 100)
        return current > threshold

    if operator == "turns_up":
        # current > prev AND prev <= prev2
        prev = _resolve_indicator_value(indicators, ind, params, lookback + 1)
        prev2 = _resolve_indicator_value(indicators, ind, params, lookback + 2)
        if prev is None or prev2 is None:
            return False
        return current > prev and prev <= prev2

    if operator == "turns_down":
        prev = _resolve_indicator_value(indicators, ind, params, lookback + 1)
        prev2 = _resolve_indicator_value(indicators, ind, params, lookback + 2)
        if prev is None or prev2 is None:
            return False
        return current < prev and prev >= prev2

    if operator == "is_highest_in_n":
        n = int(value) if value else 5
        vals = [_resolve_indicator_value(indicators, ind, params, i) for i in range(n)]
        vals = [v for v in vals if v is not None]
        if not vals:
            return False
        return current >= max(vals)

    if operator == "is_lowest_in_n":
        n = int(value) if value else 5
        vals = [_resolve_indicator_value(indicators, ind, params, i) for i in range(n)]
        vals = [v for v in vals if v is not None]
        if not vals:
            return False
        return current <= min(vals)

    if operator == "between":
        # value is a list [min, max]
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return float(value[0]) <= current <= float(value[1])
        return False

    log.warning("unknown_operator", operator=operator)
    return False


def evaluate_all_conditions(conditions: list[dict], indicators: dict, logic: str = "AND") -> tuple[bool, list[str]]:
    """
    Evaluate all conditions against indicators.
    Returns (passed: bool, matched_conditions: list[str]).
    """
    matched = []
    results = []

    for cond in conditions:
        passed = evaluate_condition(cond, indicators)
        if passed:
            matched.append(f"{cond.get('indicator')} {cond.get('operator')} {cond.get('value', cond.get('compare_indicator', ''))}")
        results.append(passed)

    if logic.upper() == "AND":
        overall = all(results) if results else False
    else:  # OR
        overall = any(results) if results else False

    return overall, matched

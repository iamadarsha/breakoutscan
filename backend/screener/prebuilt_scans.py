"""
Pre-built Scan Definitions — all 12 built-in scans for Equifidy.
Each scan is a dict with conditions, filters, timeframe, and metadata.
Conditions are designed to work with real market data from 50+ NSE stocks.
"""
from __future__ import annotations

PREBUILT_SCANS = {
    "bullish_harami_15min": {
        "id": "bullish_harami_15min",
        "name": "Bullish Harami 15min",
        "description": "Bullish candle with price above EMA20 and RSI recovering",
        "icon": "🕯️",
        "category": "Pattern",
        "timeframe": "daily",
        "badge_color": "amber",
        "conditions": [
            # Current candle is bullish
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "open", "timeframe": "daily", "lookback": 0},
            # Price above EMA20
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "ema", "compare_params": [20], "timeframe": "daily", "lookback": 0},
            # RSI in recovery zone
            {"indicator": "rsi", "params": [14], "operator": "greater_than", "value": 40, "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "less_than", "value": 65, "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"min_price": 20, "exchange": "NSE"},
    },

    "short_term_breakouts": {
        "id": "short_term_breakouts",
        "name": "Short Term Breakouts",
        "description": "Near 52-week high with RSI above 50 and price above EMA50",
        "icon": "🚀",
        "category": "Breakout",
        "timeframe": "daily",
        "badge_color": "blue",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "within_percent", "value": 10, "compare_indicator": "weekhigh52", "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "greater_than", "value": 50, "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "ema", "compare_params": [50], "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "potential_breakouts": {
        "id": "potential_breakouts",
        "name": "Potential Breakouts",
        "description": "Within 5% of 52-week high with MACD bullish and above EMA200",
        "icon": "🎯",
        "category": "Breakout",
        "timeframe": "daily",
        "badge_color": "blue",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "within_percent", "value": 5, "compare_indicator": "weekhigh52", "timeframe": "daily", "lookback": 0},
            {"indicator": "macd_line", "params": [], "operator": "greater_than", "compare_indicator": "macd_signal", "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "ema", "compare_params": [200], "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "intraday_rsi_bounce": {
        "id": "intraday_rsi_bounce",
        "name": "RSI Oversold Bounce",
        "description": "RSI below 40 with price above EMA20 — potential bounce setup",
        "icon": "📈",
        "category": "RSI",
        "timeframe": "daily",
        "badge_color": "amber",
        "conditions": [
            {"indicator": "rsi", "params": [14], "operator": "less_than", "value": 40, "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "value": 50, "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "ema_921_crossover": {
        "id": "ema_921_crossover",
        "name": "EMA 9/20 Bullish",
        "description": "EMA9 above EMA20 with RSI above 50 — bullish momentum",
        "icon": "🔀",
        "category": "EMA",
        "timeframe": "daily",
        "badge_color": "amber",
        "conditions": [
            {"indicator": "ema", "params": [9], "operator": "greater_than", "compare_indicator": "ema", "compare_params": [20], "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "greater_than", "value": 50, "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "ema", "compare_params": [20], "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "macd_bullish_cross": {
        "id": "macd_bullish_cross",
        "name": "MACD Bullish",
        "description": "MACD line above signal with positive histogram and RSI in neutral zone",
        "icon": "📊",
        "category": "MACD",
        "timeframe": "daily",
        "badge_color": "amber",
        "conditions": [
            {"indicator": "macd_line", "params": [], "operator": "greater_than", "compare_indicator": "macd_signal", "timeframe": "daily", "lookback": 0},
            {"indicator": "macd_histogram", "params": [], "operator": "greater_than", "value": 0, "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "greater_than", "value": 45, "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "less_than", "value": 75, "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "volume_surge_breakout": {
        "id": "volume_surge_breakout",
        "name": "Volume Surge Breakout",
        "description": "Bullish candle closing above previous day's high with volume confirmation",
        "icon": "💥",
        "category": "Volume",
        "timeframe": "daily",
        "badge_color": "amber",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "prevdayhigh", "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "open", "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"min_price": 20, "exchange": "NSE"},
    },

    "supertrend_buy": {
        "id": "supertrend_buy",
        "name": "Supertrend Buy Signal",
        "description": "Supertrend in BUY mode with price above SMA50",
        "icon": "🌊",
        "category": "Trend",
        "timeframe": "daily",
        "badge_color": "blue",
        "conditions": [
            {"indicator": "supertrend", "params": [], "operator": "equals", "value": 1, "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "sma", "compare_params": [50], "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "bollinger_squeeze_breakout": {
        "id": "bollinger_squeeze_breakout",
        "name": "Bollinger Band Breakout",
        "description": "Price near or above upper Bollinger Band with RSI above 50",
        "icon": "🎸",
        "category": "Volatility",
        "timeframe": "daily",
        "badge_color": "blue",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "bollinger_middle", "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "greater_than", "value": 50, "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "ema", "compare_params": [20], "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "orb_breakout": {
        "id": "orb_breakout",
        "name": "Price Above Previous Close",
        "description": "Price breaking above previous day close with bullish candle",
        "icon": "⚡",
        "category": "Intraday",
        "timeframe": "daily",
        "badge_color": "green",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "prevdayclose", "timeframe": "daily", "lookback": 0},
            {"indicator": "close", "params": [], "operator": "greater_than", "compare_indicator": "open", "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "vwap_reclaim": {
        "id": "vwap_reclaim",
        "name": "Price Below EMA50",
        "description": "Stocks trading below EMA50 — potential support bounce or weakness",
        "icon": "🎯",
        "category": "VWAP",
        "timeframe": "daily",
        "badge_color": "amber",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "less_than", "compare_indicator": "ema", "compare_params": [50], "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "less_than", "value": 50, "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },

    "week_high_52_momentum": {
        "id": "week_high_52_momentum",
        "name": "52-Week High Momentum",
        "description": "Stock within 5% of 52-week high with RSI 55-85 and MACD bullish",
        "icon": "🏆",
        "category": "Momentum",
        "timeframe": "daily",
        "badge_color": "blue",
        "conditions": [
            {"indicator": "close", "params": [], "operator": "within_percent", "value": 5, "compare_indicator": "weekhigh52", "timeframe": "daily", "lookback": 0},
            {"indicator": "rsi", "params": [14], "operator": "greater_than", "value": 55, "timeframe": "daily", "lookback": 0},
            {"indicator": "macd_line", "params": [], "operator": "greater_than", "compare_indicator": "macd_signal", "timeframe": "daily", "lookback": 0},
        ],
        "filters": {"exchange": "NSE"},
    },
}


def get_prebuilt_scan(scan_id: str) -> dict | None:
    return PREBUILT_SCANS.get(scan_id)


def list_prebuilt_scans() -> list[dict]:
    return [
        {
            "id": v["id"],
            "name": v["name"],
            "description": v["description"],
            "icon": v["icon"],
            "category": v["category"],
            "timeframe": v["timeframe"],
            "badge_color": v["badge_color"],
        }
        for v in PREBUILT_SCANS.values()
    ]

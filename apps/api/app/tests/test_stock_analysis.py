"""Tests for stock_analysis.py's pure functions: response parsing and the
deterministic technical fallback used when no AI provider is available.
"""

from __future__ import annotations

import app.services.stock_analysis as sa


def test_parse_stock_response_valid_json():
    text = '{"action": "BUY", "confidence": 8, "rationale": "Strong momentum", "catalyst": "Earnings beat", "target_pct": 5.0, "stop_loss_pct": 2.0, "tags": ["momentum"]}'
    parsed = sa._parse_stock_response(text)
    assert parsed is not None
    assert parsed["action"] == "BUY"
    assert parsed["confidence"] == 8
    assert parsed["target_pct"] == 5.0


def test_parse_stock_response_strips_markdown_fence():
    text = '```json\n{"action": "HOLD", "confidence": 5, "rationale": "Mixed signals", "catalyst": "", "target_pct": 0, "stop_loss_pct": 0, "tags": []}\n```'
    parsed = sa._parse_stock_response(text)
    assert parsed is not None
    assert parsed["action"] == "HOLD"


def test_parse_stock_response_rejects_invalid_action():
    text = '{"action": "MAYBE", "confidence": 5, "rationale": "x", "catalyst": "", "target_pct": 0, "stop_loss_pct": 0, "tags": []}'
    assert sa._parse_stock_response(text) is None


def test_parse_stock_response_rejects_malformed_json():
    assert sa._parse_stock_response("not json at all") is None


def test_parse_stock_response_clamps_confidence_out_of_range():
    text = '{"action": "SELL", "confidence": 99, "rationale": "x", "catalyst": "", "target_pct": 0, "stop_loss_pct": 0, "tags": []}'
    parsed = sa._parse_stock_response(text)
    assert parsed["confidence"] == 10


def test_technical_fallback_oversold_and_bullish_ema_is_buy():
    data = {"rsi_14": 25, "ema_9": 110, "ema_21": 100, "change_pct": 1.5}
    result = sa._technical_fallback("TESTSTOCK", data, [])
    assert result["action"] == "BUY"
    assert result["target_pct"] > 0


def test_technical_fallback_overbought_and_bearish_ema_is_sell():
    data = {"rsi_14": 80, "ema_9": 90, "ema_21": 100, "change_pct": -1.5}
    result = sa._technical_fallback("TESTSTOCK", data, [])
    assert result["action"] == "SELL"
    assert result["target_pct"] > 0


def test_technical_fallback_neutral_signals_is_hold():
    data = {"rsi_14": 50, "ema_9": 0, "ema_21": 0, "change_pct": 0.1}
    result = sa._technical_fallback("TESTSTOCK", data, [])
    assert result["action"] == "HOLD"
    assert result["target_pct"] == 0.0
    assert result["stop_loss_pct"] == 0.0


def test_technical_fallback_uses_headline_as_catalyst_when_available():
    headlines = [{"title": "Company wins big order", "url": "", "source": "Test", "published_at": ""}]
    data = {"rsi_14": 50, "ema_9": 0, "ema_21": 0, "change_pct": 0}
    result = sa._technical_fallback("TESTSTOCK", data, headlines)
    assert result["catalyst"] == "Company wins big order"


def test_technical_fallback_confidence_scales_with_signal_strength():
    strong = sa._technical_fallback("A", {"rsi_14": 20, "ema_9": 110, "ema_21": 100, "change_pct": 2}, [])
    weak = sa._technical_fallback("B", {"rsi_14": 50, "ema_9": 0, "ema_21": 0, "change_pct": 0}, [])
    assert strong["confidence"] > weak["confidence"]

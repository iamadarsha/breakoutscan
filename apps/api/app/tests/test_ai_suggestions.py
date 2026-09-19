"""Targeted tests for ai_suggestions.py's pure-function bug fixes.

These cover two concrete, previously-broken behaviors:
1. Company-name keyword matching must not silently misattribute a headline
   to the wrong stock when two companies share a common word.
2. Volume scoring must actually scale with volume, not return a constant.

No mocks needed — these are pure functions over plain dicts.
"""

from __future__ import annotations

import json

import app.services.ai_suggestions as ai


def _reset_symbol_lookup():
    ai._SYMBOL_META = {}
    ai._NAME_KEYWORDS = {}


def test_ambiguous_keyword_is_dropped_not_last_write_wins(tmp_path, monkeypatch):
    """Two companies sharing a keyword ('power') must not let one silently
    steal the other's headline — the shared keyword should be dropped
    entirely rather than resolved by whichever row loads last."""
    seed = [
        {"symbol": "TATAPOWER", "company_name": "Tata Power Company Limited", "sector": "Power"},
        {"symbol": "ADANIPOWER", "company_name": "Adani Power Limited", "sector": "Power"},
        {"symbol": "RELIANCE", "company_name": "Reliance Industries Limited", "sector": "Energy"},
    ]
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps(seed))

    _reset_symbol_lookup()
    monkeypatch.setattr(ai, "_SEED_PATH", seed_path)
    ai._ensure_symbol_lookup()

    # "POWER" is shared by two companies -> must not resolve to either.
    assert "POWER" not in ai._NAME_KEYWORDS
    # "TATA" and "ADANI" are unique -> should resolve correctly.
    assert ai._NAME_KEYWORDS.get("TATA") == "TATAPOWER"
    assert ai._NAME_KEYWORDS.get("ADANI") == "ADANIPOWER"
    # Unique multi-word names still resolve via their distinguishing word.
    assert ai._NAME_KEYWORDS.get("RELIANCE") == "RELIANCE"

    _reset_symbol_lookup()


def test_headline_with_ambiguous_word_matches_neither_company(tmp_path, monkeypatch):
    seed = [
        {"symbol": "TATAPOWER", "company_name": "Tata Power Company Limited", "sector": "Power"},
        {"symbol": "ADANIPOWER", "company_name": "Adani Power Limited", "sector": "Power"},
    ]
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps(seed))

    _reset_symbol_lookup()
    monkeypatch.setattr(ai, "_SEED_PATH", seed_path)

    headlines = [{"title": "Power sector stocks rally on policy news", "url": "", "source": "", "published_at": ""}]
    matches = ai._extract_headline_symbols(headlines)
    # A bare "Power" mention must not be attributed to either company.
    assert "TATAPOWER" not in matches
    assert "ADANIPOWER" not in matches

    # "Adani" (5 chars, unique to one company) is a real distinguishing
    # word, unlike the bare "Power" case above.
    headlines_specific = [{"title": "Adani wins new solar power contract", "url": "", "source": "", "published_at": ""}]
    matches_specific = ai._extract_headline_symbols(headlines_specific)
    assert "ADANIPOWER" in matches_specific
    assert "TATAPOWER" not in matches_specific

    _reset_symbol_lookup()


def test_volume_score_scales_with_relative_volume():
    base = {"ltp": 100, "change_pct": 0, "rsi_14": 50, "ema_9": 0, "ema_21": 0}

    low_volume_score = ai._score_stock("A", {**base, "volume": 10_000}, 0, "weekly", median_volume=100_000)
    high_volume_score = ai._score_stock("B", {**base, "volume": 500_000}, 0, "weekly", median_volume=100_000)
    at_median_score = ai._score_stock("C", {**base, "volume": 100_000}, 0, "weekly", median_volume=100_000)

    # A stock trading at 5x the universe median must score strictly higher
    # than one trading at 0.1x median or exactly at the median.
    assert high_volume_score > at_median_score > low_volume_score

    # Zero volume must never score higher than any nonzero-volume stock.
    zero_volume_score = ai._score_stock("D", {**base, "volume": 0}, 0, "weekly", median_volume=100_000)
    assert zero_volume_score < low_volume_score


def test_volume_score_without_universe_baseline_is_neutral_not_broken():
    """When no median is available (e.g. headline-only mode), volume
    scoring must fall back to a sane neutral value rather than crash."""
    base = {"ltp": 100, "change_pct": 0, "rsi_14": 50, "ema_9": 0, "ema_21": 0}
    score_with_volume = ai._score_stock("A", {**base, "volume": 5_000}, 0, "weekly", median_volume=0)
    score_without_volume = ai._score_stock("B", {**base, "volume": 0}, 0, "weekly", median_volume=0)
    assert score_with_volume > score_without_volume


def test_determine_action_returns_sell_for_genuinely_bearish_setup():
    """Overbought RSI + bearish EMA + falling price must reach SELL —
    previously this required change_pct < -1 AND ema_9 < ema_21 AND rsi > 60
    simultaneously, an overly narrow gate that almost never fired."""
    data = {"change_pct": -2.0, "ema_9": 90, "ema_21": 100, "rsi_14": 75}
    assert ai._determine_action(data) == "SELL"


def test_determine_action_returns_buy_for_genuinely_bullish_setup():
    data = {"change_pct": 2.0, "ema_9": 110, "ema_21": 100, "rsi_14": 55}
    assert ai._determine_action(data) == "BUY"


def test_determine_action_not_hardcoded_to_buy_for_mildly_bearish_data():
    """A stock that is merely down and bearish (without needing rsi > 60
    too) should already tip to SELL under the new weighted scoring."""
    data = {"change_pct": -1.5, "ema_9": 95, "ema_21": 100, "rsi_14": 50}
    assert ai._determine_action(data) == "SELL"


def test_rsi_score_rewards_overbought_same_as_oversold():
    """Overbought stocks (SELL candidates) must score as highly as oversold
    ones (BUY candidates) so they can actually reach the picks list —
    previously overbought scored 5 vs oversold's 20, so SELL-worthy stocks
    were filtered out before _determine_action ever saw them."""
    base = {"ltp": 100, "change_pct": 0, "ema_9": 0, "ema_21": 0, "volume": 0}
    oversold_score = ai._score_stock("A", {**base, "rsi_14": 20}, 0, "weekly")
    overbought_score = ai._score_stock("B", {**base, "rsi_14": 80}, 0, "weekly")
    assert oversold_score == overbought_score

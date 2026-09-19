from app.services.fundamentals_refresh import normalize_yahoo_info


def test_converts_yahoo_units_to_app_units():
    out = normalize_yahoo_info(
        {
            "trailingPE": 15.92,
            "priceToBook": 6.94,
            "returnOnEquity": 0.47743,  # fraction -> percent
            "debtToEquity": 10.211,  # percent -> ratio
            "dividendYield": 2.97,  # already percent
            "marketCap": 7_616_073_826_304,
        }
    )
    assert out["pe"] == 15.92
    assert out["pb"] == 6.94
    assert out["roe"] == 47.74
    assert out["debt_equity"] == 0.1021
    assert out["div_yield"] == 2.97
    assert out["market_cap"] == 7_616_073_826_304


def test_negative_pe_is_null_so_loss_makers_never_match_low_pe_screens():
    assert normalize_yahoo_info({"trailingPE": -12.0})["pe"] is None
    assert normalize_yahoo_info({"trailingPE": 0})["pe"] is None


def test_dividend_yield_falls_back_to_trailing_annual_fraction():
    out = normalize_yahoo_info({"trailingAnnualDividendYield": 0.0182})
    assert out["div_yield"] == 1.82


def test_implausible_dividend_yield_is_dropped():
    assert normalize_yahoo_info({"dividendYield": 480.0})["div_yield"] is None


def test_missing_and_junk_values_become_none_without_raising():
    out = normalize_yahoo_info(
        {"trailingPE": "n/a", "priceToBook": None, "returnOnEquity": float("nan"), "debtToEquity": True}
    )
    assert out == {
        "pe": None, "pb": None, "roe": None,
        "debt_equity": None, "div_yield": None, "market_cap": None,
    }


def test_empty_info_yields_all_none():
    assert set(normalize_yahoo_info({}).values()) == {None}

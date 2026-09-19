from app.services.stock_names import company_name_for


def test_known_symbols_resolve_to_company_names():
    assert company_name_for("TCS") != "TCS"
    assert "Tata Consultancy" in company_name_for("TCS")


def test_unknown_symbol_falls_back_to_itself():
    assert company_name_for("NOTASYMBOL123") == "NOTASYMBOL123"

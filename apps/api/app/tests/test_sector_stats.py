from app.services.sector_stats import compute_sector_performance


def test_aggregates_change_counts_and_top_movers():
    sectors = {"A": "IT", "B": "IT", "C": "IT", "D": "Banks", "E": "Banks", "F": "Banks"}
    changes = {"A": 2.0, "B": -1.0, "C": 0.0, "D": 1.0, "E": 1.0, "F": 4.0}
    result = compute_sector_performance(sectors, changes)

    assert [r["sector"] for r in result] == ["Banks", "IT"]  # strongest first
    banks, it = result
    assert banks["change_pct"] == 2.0 and banks["advances"] == 3 and banks["declines"] == 0
    assert banks["top_gainer"] == "F"
    assert it["change_pct"] == 0.33 and it["advances"] == 1 and it["declines"] == 1
    assert it["top_gainer"] == "A" and it["top_loser"] == "B"


def test_drops_thin_sectors_and_unpriced_symbols():
    sectors = {"A": "Tiny", "B": "Tiny", "C": "Big", "D": "Big", "E": "Big", "F": "Big"}
    changes = {"A": 5.0, "B": 5.0, "C": 1.0, "D": 1.0, "E": 1.0}  # F has no price
    result = compute_sector_performance(sectors, changes)
    assert [r["sector"] for r in result] == ["Big"]
    assert result[0]["advances"] == 3


def test_empty_inputs_return_empty_list():
    assert compute_sector_performance({}, {}) == []

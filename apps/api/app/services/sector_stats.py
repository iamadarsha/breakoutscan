from __future__ import annotations

from collections import defaultdict
from typing import Any

MIN_STOCKS_PER_SECTOR = 3


def compute_sector_performance(
    sector_by_symbol: dict[str, str],
    change_by_symbol: dict[str, float],
    min_stocks: int = MIN_STOCKS_PER_SECTOR,
) -> list[dict[str, Any]]:
    """Average day-change, advance/decline counts and top mover per sector.

    Only symbols with both a sector and a live change_pct count; sectors
    with fewer than `min_stocks` priced members are dropped as too thin to
    call a sector move. Result is sorted strongest to weakest.
    """
    members: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for symbol, sector in sector_by_symbol.items():
        change = change_by_symbol.get(symbol)
        if sector and change is not None:
            members[sector].append((symbol, change))

    results: list[dict[str, Any]] = []
    for sector, stocks in members.items():
        if len(stocks) < min_stocks:
            continue
        changes = [c for _, c in stocks]
        best = max(stocks, key=lambda s: s[1])
        worst = min(stocks, key=lambda s: s[1])
        results.append(
            {
                "sector": sector,
                "change_pct": round(sum(changes) / len(changes), 2),
                "advances": sum(1 for c in changes if c > 0),
                "declines": sum(1 for c in changes if c < 0),
                "top_gainer": best[0],
                "top_loser": worst[0],
            }
        )
    results.sort(key=lambda r: r["change_pct"], reverse=True)
    return results

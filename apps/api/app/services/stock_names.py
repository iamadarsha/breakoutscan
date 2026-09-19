"""Company names from the bundled NIFTY 500 seed (no database or network hit)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "nifty500_seed.json"


@lru_cache(maxsize=1)
def _names() -> dict[str, str]:
    try:
        entries = json.loads(_SEED_PATH.read_text())
    except (OSError, ValueError):
        return {}
    return {e["symbol"]: e["company_name"] for e in entries if e.get("symbol") and e.get("company_name")}


def company_name_for(symbol: str) -> str:
    """The company's name, or the symbol itself when it isn't in the seed."""
    return _names().get(symbol, symbol)

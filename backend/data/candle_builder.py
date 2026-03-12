"""
Candle Builder — converts individual ticks into OHLCV candles.
Maintains rolling in-memory candle buffers for multiple timeframes per symbol.
"""
from __future__ import annotations
import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable
import structlog

log = structlog.get_logger(__name__)

# IST timezone offset
IST = timezone(timedelta(hours=5, minutes=30))

# Timeframe definitions (minutes)
TIMEFRAMES = {
    "1min": 1,
    "5min": 5,
    "15min": 15,
    "30min": 30,
    "1hr": 60,
}

# Max candles to keep per symbol per timeframe
MAX_CANDLES = {
    "1min": 390,    # Full trading day
    "5min": 200,
    "15min": 100,
    "30min": 80,
    "1hr": 50,
}

# Market open time in IST
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15


@dataclass
class Candle:
    """Single OHLCV candle."""
    symbol: str
    timeframe: str
    ts: datetime          # candle open time (IST)
    open: float
    high: float
    low: float
    close: float
    volume: int
    is_complete: bool = False

    def update(self, price: float, volume: int = 0):
        """Update current forming candle with a new tick."""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "ts": self.ts.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass
class SymbolCandleState:
    """Tracks candle state for a single symbol across all timeframes."""
    symbol: str
    current_candles: dict[str, Optional[Candle]] = field(default_factory=dict)
    candle_history: dict[str, deque] = field(default_factory=dict)

    def __post_init__(self):
        for tf in TIMEFRAMES:
            self.current_candles[tf] = None
            self.candle_history[tf] = deque(maxlen=MAX_CANDLES[tf])


def get_candle_open_time(ts: datetime, tf_minutes: int) -> datetime:
    """Compute the open time of the candle containing ts."""
    # Align to tf_minutes boundary from market open
    market_open = ts.replace(
        hour=MARKET_OPEN_HOUR,
        minute=MARKET_OPEN_MINUTE,
        second=0,
        microsecond=0
    )
    delta = (ts - market_open).total_seconds() / 60
    candle_idx = int(delta // tf_minutes)
    candle_open = market_open + timedelta(minutes=candle_idx * tf_minutes)
    return candle_open


class CandleBuilder:
    """
    Converts live ticks into OHLCV candles for multiple timeframes.
    Triggers indicator recomputation on candle close via callbacks.
    """

    def __init__(self):
        self._states: dict[str, SymbolCandleState] = {}
        self._on_candle_close_callbacks: list[Callable] = []

    def register_on_candle_close(self, callback: Callable):
        """Register a callback to be called when a candle closes."""
        self._on_candle_close_callbacks.append(callback)

    def _get_state(self, symbol: str) -> SymbolCandleState:
        if symbol not in self._states:
            self._states[symbol] = SymbolCandleState(symbol=symbol)
        return self._states[symbol]

    async def on_tick(self, symbol: str, ltp: float, volume: int = 0, ts: Optional[datetime] = None):
        """
        Process a single price tick for a symbol.
        Updates current candles and closes them on time boundaries.
        """
        if ts is None:
            ts = datetime.now(tz=IST)
        elif ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)

        state = self._get_state(symbol)

        for tf, tf_minutes in TIMEFRAMES.items():
            candle_open_time = get_candle_open_time(ts, tf_minutes)
            current = state.current_candles[tf]

            if current is None or current.ts < candle_open_time:
                # New candle period started — close old candle if it exists
                if current is not None:
                    current.is_complete = True
                    state.candle_history[tf].append(current)
                    await self._notify_candle_close(symbol, tf, current)

                # Open new candle
                new_candle = Candle(
                    symbol=symbol,
                    timeframe=tf,
                    ts=candle_open_time,
                    open=ltp,
                    high=ltp,
                    low=ltp,
                    close=ltp,
                    volume=volume,
                )
                state.current_candles[tf] = new_candle
            else:
                # Update existing candle
                current.update(ltp, volume)

    async def _notify_candle_close(self, symbol: str, timeframe: str, candle: Candle):
        """Notify registered callbacks that a candle has closed."""
        for callback in self._on_candle_close_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(symbol, timeframe, candle)
                else:
                    callback(symbol, timeframe, candle)
            except Exception as e:
                log.error("candle_close_callback_error", symbol=symbol, tf=timeframe, error=str(e))

    def get_candles(self, symbol: str, timeframe: str, n: int = 200) -> list[dict]:
        """Get the last n completed candles for a symbol + timeframe."""
        state = self._get_state(symbol)
        history = state.candle_history.get(timeframe, deque())
        candles = list(history)[-n:]
        # Also append the current forming candle
        current = state.current_candles.get(timeframe)
        if current:
            candles.append(current)
        return [c.to_dict() for c in candles]

    def get_all_symbols(self) -> list[str]:
        """Return all symbols with active candle state."""
        return list(self._states.keys())

    def snapshot_for_screener(self, symbol: str, timeframe: str, n: int = 100) -> list[Candle]:
        """Return up to n recent completed candles as Candle objects (for screener use)."""
        state = self._get_state(symbol)
        history = state.candle_history.get(timeframe, deque())
        candles = list(history)[-n:]
        current = state.current_candles.get(timeframe)
        if current:
            candles.append(current)
        return candles


# ── Global singleton ───────────────────────────────────────────────────────

_candle_builder: Optional[CandleBuilder] = None


def get_candle_builder() -> CandleBuilder:
    global _candle_builder
    if _candle_builder is None:
        _candle_builder = CandleBuilder()
    return _candle_builder

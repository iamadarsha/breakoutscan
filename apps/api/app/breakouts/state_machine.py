"""The breakout lifecycle FSM — styled after `app.market.failover.FailoverController`
(dataclass config, an `evaluate()`-style advance method, injectable `now` for
testing) but tracking one symbol+trigger+direction's ARMED->TRIGGERED->
CONFIRMED->INVALIDATED/EXPIRED lifecycle instead of a single feed's health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from app.breakouts.types import (
    BreakoutSignal,
    BreakoutStatus,
    Direction,
    ExpiryPolicy,
    RawEvent,
    TriggerType,
)
from app.utils.time import MARKET_CLOSE

_TF_MINUTES: dict[str, int] = {"1min": 1, "5min": 5, "15min": 15, "1d": 1440}


def _bar_minutes(timeframe: str) -> int:
    return _TF_MINUTES.get(timeframe, 5)


@dataclass(frozen=True, slots=True)
class TriggerConfig:
    confirmation_bars: int = 1
    confirmation_timeframe: str = "5min"
    expiry: ExpiryPolicy = ExpiryPolicy.END_OF_DAY
    expiry_bars: int = 20  # only used when expiry is ROLLING_BARS


DEFAULT_CONFIGS: dict[TriggerType, TriggerConfig] = {
    TriggerType.ORB: TriggerConfig(1, "5min", ExpiryPolicy.END_OF_DAY),
    TriggerType.PDH_PDL: TriggerConfig(1, "5min", ExpiryPolicy.END_OF_DAY),
    TriggerType.NR4: TriggerConfig(1, "15min", ExpiryPolicy.END_OF_DAY),
    TriggerType.NR7: TriggerConfig(1, "15min", ExpiryPolicy.END_OF_DAY),
    TriggerType.INSIDE_BAR: TriggerConfig(1, "15min", ExpiryPolicy.END_OF_DAY),
    TriggerType.VOLUME_BREAKOUT: TriggerConfig(1, "5min", ExpiryPolicy.END_OF_DAY),
    TriggerType.VWAP: TriggerConfig(1, "5min", ExpiryPolicy.END_OF_DAY),
    TriggerType.FIFTY_TWO_WEEK: TriggerConfig(2, "15min", ExpiryPolicy.ROLLING_BARS, expiry_bars=20),
    TriggerType.DONCHIAN: TriggerConfig(2, "15min", ExpiryPolicy.ROLLING_BARS, expiry_bars=20),
    TriggerType.EMA_CROSS: TriggerConfig(1, "15min", ExpiryPolicy.ROLLING_BARS, expiry_bars=10),
    TriggerType.MACD_CROSS: TriggerConfig(1, "15min", ExpiryPolicy.ROLLING_BARS, expiry_bars=10),
    TriggerType.BOLLINGER_SQUEEZE: TriggerConfig(1, "15min", ExpiryPolicy.ROLLING_BARS, expiry_bars=10),
}


@dataclass
class BreakoutTracker:
    """One symbol+trigger_type+direction's lifecycle state.

    `evaluate()` advances the FSM by one scan cycle and returns a
    `BreakoutSignal` only on a transition worth surfacing (CONFIRMED /
    INVALIDATED / EXPIRED / FAILED) — ARMED-still-armed or
    HOLD-not-yet-confirmed cycles return `None`.
    """

    symbol: str
    trigger_type: TriggerType
    direction: Direction
    config: TriggerConfig
    status: BreakoutStatus = BreakoutStatus.ARMED
    level: Decimal | None = None
    triggered_at: datetime | None = None
    last_bar_ts: str | None = None
    bars_confirmed: int = 0
    last_price: Decimal | None = None
    # Real traded price for display. last_price doubles as the previous
    # compared value, which is a volume count for volume triggers.
    display_price: Decimal | None = None
    last_updated: datetime | None = None
    confirmed_at: datetime | None = None
    confirmation_price: Decimal | None = None

    def evaluate(
        self,
        event: RawEvent,
        level: Decimal,
        price: Decimal,
        now: datetime,
        bar_ts: str | None,
        volume_ratio: float | None = None,
        extra: dict[str, Any] | None = None,
    ) -> BreakoutSignal | None:
        self.level = level
        self.last_price = price
        self.last_updated = now
        extra = extra or {}

        if self.status in (BreakoutStatus.ARMED, BreakoutStatus.INVALIDATED, BreakoutStatus.EXPIRED):
            if event in (RawEvent.CROSS_UP, RawEvent.CROSS_DOWN):
                self.status = BreakoutStatus.TRIGGERED
                self.triggered_at = now
                self.bars_confirmed = 0
                self.last_bar_ts = bar_ts
            return None  # first cross is recorded, not yet alertable

        if self.status == BreakoutStatus.TRIGGERED:
            if event is RawEvent.REVERSE:
                self.status = BreakoutStatus.INVALIDATED
                return self._signal(BreakoutStatus.INVALIDATED, level, price, now)
            if self._is_expired(now):
                self.status = BreakoutStatus.EXPIRED
                return self._signal(BreakoutStatus.EXPIRED, level, price, now)
            if event is RawEvent.HOLD and bar_ts is not None and bar_ts != self.last_bar_ts:
                self.bars_confirmed += 1
                self.last_bar_ts = bar_ts
                if self.bars_confirmed >= self.config.confirmation_bars:
                    self.status = BreakoutStatus.CONFIRMED
                    self.confirmed_at = now
                    self.confirmation_price = price
                    return self._signal(
                        BreakoutStatus.CONFIRMED, level, price, now,
                        volume_ratio=volume_ratio, extra=extra,
                    )
            return None

        if self.status == BreakoutStatus.CONFIRMED:
            # Stays CONFIRMED (no re-fire) until price reverses, at which
            # point it re-arms for the next approach of the same level. A
            # reversal here is a *false breakout* (it already confirmed) —
            # distinct from INVALIDATED (a pre-confirmation reversal) — so it
            # gets its own FAILED signal surfaced alongside the re-arm,
            # rather than being silently swallowed.
            if event is RawEvent.REVERSE:
                failed_signal = BreakoutSignal(
                    symbol=self.symbol,
                    trigger_type=self.trigger_type,
                    direction=self.direction,
                    status=BreakoutStatus.FAILED,
                    reference_level=level,
                    trigger_price=price,
                    confirmation_price=self.confirmation_price,
                    triggered_at=self.triggered_at or now,
                    confirmed_at=self.confirmed_at,
                    bars_confirmed=self.bars_confirmed,
                    volume_ratio=volume_ratio,
                    extra=extra,
                )
                self.status = BreakoutStatus.ARMED
                self.bars_confirmed = 0
                self.confirmed_at = None
                self.confirmation_price = None
                return failed_signal
            return None

        return None

    def _is_expired(self, now: datetime) -> bool:
        if self.config.expiry is ExpiryPolicy.END_OF_DAY:
            # Derive close-of-day from *now*'s own date, never the real
            # system clock's date — this is what actually makes `now`
            # injectable/testable (matching FailoverController's convention).
            close_today = datetime.combine(now.date(), MARKET_CLOSE, tzinfo=now.tzinfo)
            return now >= close_today
        if self.triggered_at is None:
            return False
        window = timedelta(minutes=_bar_minutes(self.config.confirmation_timeframe) * self.config.expiry_bars)
        return self.bars_confirmed == 0 and (now - self.triggered_at) > window

    def _signal(
        self,
        status: BreakoutStatus,
        level: Decimal,
        price: Decimal,
        now: datetime,
        volume_ratio: float | None = None,
        extra: dict[str, Any] | None = None,
    ) -> BreakoutSignal:
        return BreakoutSignal(
            symbol=self.symbol,
            trigger_type=self.trigger_type,
            direction=self.direction,
            status=status,
            reference_level=level,
            trigger_price=price,
            confirmation_price=price if status is BreakoutStatus.CONFIRMED else None,
            triggered_at=self.triggered_at or now,
            confirmed_at=now if status is BreakoutStatus.CONFIRMED else None,
            bars_confirmed=self.bars_confirmed,
            volume_ratio=volume_ratio,
            extra=extra or {},
        )


class BreakoutStateStore:
    """In-memory registry, keyed like `app.market.state.MarketState` — no
    Redis. A restart loses in-flight ARMED/TRIGGERED progress, which
    rebuilds within one confirmation window from unaffected underlying
    data; every CONFIRMED signal is separately persisted to Postgres
    (`persistence.py`) so no actual event is ever lost to a restart.
    """

    def __init__(self) -> None:
        self._trackers: dict[tuple[str, TriggerType, Direction], BreakoutTracker] = {}

    def get_or_create(
        self, symbol: str, trigger_type: TriggerType, direction: Direction, config: TriggerConfig,
    ) -> BreakoutTracker:
        key = (symbol, trigger_type, direction)
        tracker = self._trackers.get(key)
        if tracker is None:
            tracker = BreakoutTracker(symbol=symbol, trigger_type=trigger_type, direction=direction, config=config)
            self._trackers[key] = tracker
        return tracker

    def all_active(self) -> list[BreakoutTracker]:
        """Trackers currently TRIGGERED or CONFIRMED — i.e. worth surfacing
        via `GET /api/breakouts/active`."""
        return [
            t for t in self._trackers.values()
            if t.status in (BreakoutStatus.TRIGGERED, BreakoutStatus.CONFIRMED)
        ]

    def for_symbol(self, symbol: str) -> list[BreakoutTracker]:
        return [t for t in self._trackers.values() if t.symbol == symbol]

    def purge_expired(self, now: datetime) -> int:
        """Drop trackers that have sat in ARMED with no recent update —
        pure memory hygiene, doesn't affect already-emitted signals."""
        stale_cutoff = now - timedelta(hours=24)
        stale_keys = [
            key for key, t in self._trackers.items()
            if t.status is BreakoutStatus.ARMED and t.last_updated is not None and t.last_updated < stale_cutoff
        ]
        for key in stale_keys:
            del self._trackers[key]
        return len(stale_keys)

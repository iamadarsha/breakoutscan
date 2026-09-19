from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.breakouts.engine import get_breakout_state_store
from app.breakouts.state_machine import BreakoutTracker
from app.breakouts.types import BreakoutStatus
from app.db.models.breakout_event import BreakoutEvent
from app.db.models.stock import Stock
from app.schemas.breakout import ActiveBreakoutOut, BreakoutEventOut, SymbolBreakoutsOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/breakouts", tags=["breakouts"])


def _to_active_out(tracker: BreakoutTracker) -> ActiveBreakoutOut:
    return ActiveBreakoutOut(
        symbol=tracker.symbol,
        trigger_type=tracker.trigger_type.value,
        direction=tracker.direction.value,
        status=tracker.status.value,
        reference_level=float(tracker.level) if tracker.level is not None else 0.0,
        last_price=float(tracker.last_price) if tracker.last_price is not None else None,
        triggered_at=tracker.triggered_at,
        bars_confirmed=tracker.bars_confirmed,
        score=None,
        is_live=True,
    )


def _db_event_to_active_out(row: BreakoutEvent, company_name: str | None) -> ActiveBreakoutOut:
    return ActiveBreakoutOut(
        symbol=row.symbol,
        company_name=company_name,
        trigger_type=row.trigger_type,
        direction=row.direction,
        status="CONFIRMED",
        reference_level=float(row.reference_level),
        last_price=float(row.confirmation_price) if row.confirmation_price is not None else float(row.trigger_price),
        triggered_at=row.triggered_at,
        bars_confirmed=0,
        score=float(row.score) if row.score is not None else None,
        is_live=False,
    )


async def _last_session_breakouts(
    db: AsyncSession, trigger_type: str | None, limit: int
) -> list[ActiveBreakoutOut]:
    """Fallback for a quiet in-memory tracker store (market closed, or no
    fresh signal since the last restart) — surfaces the most recent
    CONFIRMED breakouts from the durable table instead of an empty screen.
    """
    stmt = (
        select(BreakoutEvent, Stock.company_name)
        .join(Stock, Stock.symbol == BreakoutEvent.symbol, isouter=True)
        .where(BreakoutEvent.confirmed_at.is_not(None))
        .order_by(BreakoutEvent.confirmed_at.desc())
    )
    if trigger_type:
        stmt = stmt.where(BreakoutEvent.trigger_type == trigger_type)
    stmt = stmt.limit(limit)

    rows = (await db.execute(stmt)).all()
    return [_db_event_to_active_out(event, name) for event, name in rows]


@router.get("/active", response_model=list[ActiveBreakoutOut])
async def list_active_breakouts(
    trigger_type: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Currently TRIGGERED or CONFIRMED breakouts, in-memory (see
    `BreakoutStateStore` — restart resets ARMED/TRIGGERED progress, but
    every actual CONFIRMED event is separately durable via `/api/breakouts/{symbol}`).

    Falls back to the most recent CONFIRMED rows in `breakout_events` when
    the live tracker store has nothing to show (market closed, or a fresh
    restart with no signal yet) — so the dashboard shows the last known
    breakouts instead of a misleading zero.
    """
    store = get_breakout_state_store()
    trackers = store.all_active()
    if trigger_type:
        trackers = [t for t in trackers if t.trigger_type.value == trigger_type]
    trackers = trackers[:limit]

    if trackers:
        return [_to_active_out(t) for t in trackers]

    return await _last_session_breakouts(db, trigger_type, limit)


@router.get("/{symbol}", response_model=SymbolBreakoutsOut)
async def get_symbol_breakouts(symbol: str, db: AsyncSession = Depends(get_db)):
    sym = symbol.upper()
    store = get_breakout_state_store()
    active = [
        t for t in store.for_symbol(sym)
        if t.status in (BreakoutStatus.TRIGGERED, BreakoutStatus.CONFIRMED)
    ]

    rows = (
        await db.execute(
            select(BreakoutEvent)
            .where(BreakoutEvent.symbol == sym)
            .order_by(BreakoutEvent.confirmed_at.desc())
            .limit(20)
        )
    ).scalars().all()

    return SymbolBreakoutsOut(
        symbol=sym,
        active=[_to_active_out(t) for t in active],
        recent_events=[BreakoutEventOut.model_validate(r) for r in rows],
    )

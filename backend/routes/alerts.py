"""
Alerts API routes.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Header
import structlog

from schemas import AlertCreate, AlertResponse

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In-memory store for development
_ALERTS: dict[str, list[dict]] = {}
_ALERT_HISTORY: list[dict] = [
    {
        "id": str(uuid4()), "symbol": "TATAMOTORS", "scan_name": "EMA 9/21 Crossover",
        "trigger_price": 924.35, "triggered_at": "2026-03-12T11:34:00+05:30",
        "conditions_met": ["EMA9 > EMA21", "Close > VWAP"],
    },
    {
        "id": str(uuid4()), "symbol": "RELIANCE", "scan_name": "RSI Bounce",
        "trigger_price": 2831.20, "triggered_at": "2026-03-12T11:28:00+05:30",
        "conditions_met": ["RSI < 35", "RSI turning up", "Close > VWAP"],
    },
    {
        "id": str(uuid4()), "symbol": "HDFCBANK", "scan_name": "Volume Surge Breakout",
        "trigger_price": 1668.50, "triggered_at": "2026-03-12T11:15:00+05:30",
        "conditions_met": ["Volume > 3x Avg"],
    },
]

DEMO_USER = "demo-user"

def _get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    return x_user_id or DEMO_USER


@router.get("")
async def get_alerts(user_id: str = Depends(_get_user_id)):
    """Get all configured alerts for the user."""
    return _ALERTS.get(user_id, [
        {
            "id": str(uuid4()), "symbol": "RELIANCE",
            "scan_name": "EMA 9/21 Crossover", "notify_push": True, "is_active": True,
            "frequency": "once_per_day", "created_at": "2026-03-10T09:00:00Z",
        },
        {
            "id": str(uuid4()), "symbol": "TATAMOTORS",
            "scan_name": "RSI Bounce", "notify_push": True, "notify_telegram": True, "is_active": True,
            "frequency": "every_time", "created_at": "2026-03-10T09:00:00Z",
        },
    ])


@router.post("")
async def create_alert(alert: AlertCreate, user_id: str = Depends(_get_user_id)):
    """Create a new alert."""
    alert_dict = {
        "id": str(uuid4()),
        "user_id": user_id,
        **alert.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if user_id not in _ALERTS:
        _ALERTS[user_id] = []
    _ALERTS[user_id].append(alert_dict)
    return alert_dict


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, is_active: bool, user_id: str = Depends(_get_user_id)):
    """Toggle an alert on/off."""
    alerts = _ALERTS.get(user_id, [])
    for a in alerts:
        if a["id"] == alert_id:
            a["is_active"] = is_active
            return a
    raise HTTPException(status_code=404, detail="Alert not found")


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str, user_id: str = Depends(_get_user_id)):
    """Delete an alert."""
    if user_id in _ALERTS:
        _ALERTS[user_id] = [a for a in _ALERTS[user_id] if a["id"] != alert_id]
    return {"message": "Alert deleted"}


@router.get("/history")
async def get_alert_history(user_id: str = Depends(_get_user_id)):
    """Get alert trigger history."""
    return _ALERT_HISTORY

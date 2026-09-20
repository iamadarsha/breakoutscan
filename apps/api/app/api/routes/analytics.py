"""Usage analytics: a public collector plus owner-only metrics and exports."""

from __future__ import annotations

import hmac
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_user
from app.core.auth_tokens import verify_access_token
from app.core.config import Settings, get_settings
from app.services import analytics as svc
from app.services import analytics_report as report

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analytics"])


@router.post("/api/analytics/collect", status_code=202)
async def collect(
    batch: svc.BatchIn,
    request: Request,
    user_id: Optional[str] = Depends(get_optional_user),
) -> dict[str, int]:
    """Public, fire-and-forget. Never fails the page: bad payloads are rejected, the rest is queued."""
    ctx = svc.RequestContext(
        user_agent=request.headers.get("user-agent"),
        country=request.headers.get("x-vercel-ip-country"),
        user_id=user_id,
    )
    return {"accepted": svc.enqueue(batch, ctx)}


def _admin_emails(settings: Settings) -> set[str]:
    return {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}


async def require_admin(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
) -> str:
    """Owner-only. Either the secret export token (for Sheets) or a verified, allow-listed sign-in."""
    settings = get_settings()
    if token and settings.analytics_export_token and hmac.compare_digest(token, settings.analytics_export_token):
        return "export-token"
    if authorization and authorization.startswith("Bearer "):
        try:
            claims = await verify_access_token(authorization[7:], settings)
        except (jwt.InvalidTokenError, Exception):  # noqa: BLE001 - any verification failure is a 403
            raise HTTPException(status_code=403, detail="Forbidden") from None
        email = str(claims.get("email", "")).lower()
        if email and claims.get("email_verified") is True and email in _admin_emails(settings):
            return email
    raise HTTPException(status_code=403, detail="Forbidden")


def _csv_response(body: str, filename: str) -> Response:
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Cache-Control": "no-store", "Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/api/admin/analytics/summary")
async def analytics_summary(
    days: int = Query(30, ge=1, le=90),
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await report.summary(db, days=days)


@router.get("/api/admin/analytics/export/pm-report.csv")
async def export_pm_report(_admin: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return _csv_response(await report.pm_report_csv(db), "breakoutscan-pm-report.csv")


@router.get("/api/admin/analytics/export/summary.csv")
async def export_summary(
    days: int = Query(30, ge=1, le=90),
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return _csv_response(await report.summary_csv(db, days=days), "breakoutscan-summary.csv")


@router.get("/api/admin/analytics/export/daily.csv")
async def export_daily(_admin: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return _csv_response(await report.daily_csv(db), "breakoutscan-daily.csv")


@router.get("/api/admin/analytics/export/users.csv")
async def export_users(_admin: str = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return _csv_response(await report.users_csv(db), "breakoutscan-users.csv")


@router.get("/api/admin/analytics/export/events.csv")
async def export_events(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    limit: int = Query(50_000, ge=1, le=100_000),
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc).astimezone(svc.IST).date()
    end = end or today
    start = start or (end - timedelta(days=6))
    if start > end or (end - start).days > 92:
        raise HTTPException(status_code=422, detail="from/to must be a valid range of at most 92 days")
    return _csv_response(await report.events_csv(db, start, end, limit), f"breakoutscan-events-{start}-{end}.csv")

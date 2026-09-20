"""Access control on the owner-only analytics endpoints."""

from __future__ import annotations

import httpx
import pytest

from app.api.routes import analytics as routes
from app.core.config import get_settings
from app.main import app
from app.api.deps import get_db


@pytest.fixture(autouse=True)
def _stubs(monkeypatch):
    async def _db():
        yield object()

    async def _summary(_db, days=30, now=None):
        return {"ok": True, "days": days}

    async def _daily(_db, now=None):
        return "day,visitors\n2026-09-21,3\n"

    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(routes.report, "summary", _summary)
    monkeypatch.setattr(routes.report, "daily_csv", _daily)
    settings = get_settings()
    monkeypatch.setattr(settings, "analytics_export_token", "s3cret-token-value")
    monkeypatch.setattr(settings, "admin_emails", "Owner@Example.com, other@example.com")
    yield
    app.dependency_overrides.pop(get_db, None)


async def _get(path, **kw):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(path, **kw)


async def test_no_credentials_is_forbidden():
    assert (await _get("/api/admin/analytics/summary")).status_code == 403


async def test_wrong_token_is_forbidden():
    assert (await _get("/api/admin/analytics/summary?token=nope")).status_code == 403


async def test_token_grants_access_to_json_and_csv():
    r = await _get("/api/admin/analytics/summary?days=7&token=s3cret-token-value")
    assert r.status_code == 200 and r.json() == {"ok": True, "days": 7}
    r = await _get("/api/admin/analytics/export/daily.csv?token=s3cret-token-value")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.headers["cache-control"] == "no-store" and r.text.startswith("day,visitors")


async def test_token_access_is_off_when_no_token_configured(monkeypatch):
    monkeypatch.setattr(get_settings(), "analytics_export_token", "")
    assert (await _get("/api/admin/analytics/summary?token=")).status_code == 403


@pytest.mark.parametrize(
    "claims,expected",
    [
        ({"email": "owner@example.com", "email_verified": True}, 200),
        ({"email": "OTHER@example.com", "email_verified": True}, 200),
        ({"email": "owner@example.com", "email_verified": False}, 403),  # unverified email never counts
        ({"email": "stranger@example.com", "email_verified": True}, 403),
        ({"sub": "abc"}, 403),
    ],
)
async def test_signed_in_admin_must_be_allow_listed_and_verified(monkeypatch, claims, expected):
    async def _verify(_token, _settings):
        return claims

    monkeypatch.setattr(routes, "verify_access_token", _verify)
    r = await _get("/api/admin/analytics/summary", headers={"authorization": "Bearer x.y.z"})
    assert r.status_code == expected


async def test_invalid_bearer_token_is_forbidden(monkeypatch):
    async def _boom(_token, _settings):
        raise ValueError("bad token")

    monkeypatch.setattr(routes, "verify_access_token", _boom)
    assert (await _get("/api/admin/analytics/summary", headers={"authorization": "Bearer junk"})).status_code == 403

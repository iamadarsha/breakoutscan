from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalyticsEvent(Base):
    """One raw usage event. Append-only; every reported metric is derivable from these rows."""

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    client_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visitor_id: Mapped[str] = mapped_column(String(40), nullable=False)
    session_id: Mapped[str] = mapped_column(String(40), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    props: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    referrer: Mapped[str | None] = mapped_column(String(300), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    device: Mapped[str | None] = mapped_column(String(12), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(30), nullable=True)
    os: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    viewport_w: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)


class AnalyticsUser(Base):
    __tablename__ = "analytics_users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    visitors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    new_visitors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    returning_visitors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    pageviews: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    events: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    signed_in_users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    new_users: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    bounced_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    avg_session_seconds: Mapped[Decimal] = mapped_column(Numeric(10, 1), nullable=False, server_default=text("0"))
    scans_run: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    errors: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

"""
SQLAlchemy ORM models for BreakoutScan.
Mirrors the database schema defined in the implementation plan.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func
)
from sqlalchemy import JSON as JSONB, Uuid as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ── Stock Master ────────────────────────────────────────────────────────────

class Stock(Base):
    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12), unique=True, index=True)
    instrument_key: Mapped[Optional[str]] = mapped_column(String(50), unique=True)  # e.g. NSE_EQ|INE009A01021
    company_name: Mapped[Optional[str]] = mapped_column(Text)
    exchange: Mapped[str] = mapped_column(String(5), default="NSE")
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger)  # in INR
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    pb_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    roce: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    debt_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    div_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    profit_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    eps_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_nifty50: Mapped[bool] = mapped_column(Boolean, default=False)
    is_nifty500: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Time-Series OHLCV (extends TimescaleDB hypertable) ──────────────────────

class OHLCV1Min(Base):
    __tablename__ = "ohlcv_1min"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(5), primary_key=True, default="NSE")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    instrument_key: Mapped[Optional[str]] = mapped_column(String(50))


class OHLCVDaily(Base):
    __tablename__ = "ohlcv_daily"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, primary_key=True)
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    adj_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    week_high_52: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    week_low_52: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))


# ── User Scans ───────────────────────────────────────────────────────────────

class UserScan(Base):
    __tablename__ = "user_scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    filters: Mapped[Optional[dict]] = mapped_column(JSONB)
    timeframe: Mapped[str] = mapped_column(String(20), default="15min")
    universe: Mapped[str] = mapped_column(String(50), default="NSE_ALL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list["ScanRun"]] = relationship("ScanRun", back_populates="scan", lazy="noload")


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("user_scans.id", ondelete="SET NULL"))
    scan_name: Mapped[Optional[str]] = mapped_column(String(255))
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    result_count: Mapped[Optional[int]] = mapped_column(Integer)
    results: Mapped[Optional[dict]] = mapped_column(JSONB)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    scan: Mapped[Optional["UserScan"]] = relationship("UserScan", back_populates="runs")


# ── Watchlist ────────────────────────────────────────────────────────────────

class Watchlist(Base):
    __tablename__ = "watchlist"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Alerts ───────────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    scan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("user_scans.id", ondelete="SET NULL"))
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_push: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(100))
    frequency: Mapped[str] = mapped_column(String(30), default="once_per_day")  # once | every_time | once_per_day
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    history: Mapped[list["AlertHistory"]] = relationship("AlertHistory", back_populates="alert", lazy="noload")


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="SET NULL"))
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    scan_name: Mapped[Optional[str]] = mapped_column(String(255))
    trigger_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    conditions_met: Mapped[Optional[dict]] = mapped_column(JSONB)

    alert: Mapped[Optional["Alert"]] = relationship("Alert", back_populates="history")

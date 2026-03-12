"""
Pydantic v2 request/response schemas for Equifidy API.
"""
from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ── Shared ───────────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Stock ────────────────────────────────────────────────────────────────────

class StockBasic(OrmBase):
    symbol: str
    company_name: Optional[str] = None
    exchange: str = "NSE"
    sector: Optional[str] = None
    market_cap: Optional[int] = None


class StockDetail(StockBasic):
    isin: Optional[str] = None
    industry: Optional[str] = None
    pe_ratio: Optional[Decimal] = None
    pb_ratio: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    roce: Optional[Decimal] = None
    debt_equity: Optional[Decimal] = None
    div_yield: Optional[Decimal] = None
    revenue_growth: Optional[Decimal] = None
    profit_growth: Optional[Decimal] = None
    is_nifty50: bool = False
    is_nifty500: bool = False


class StockSearchResult(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: str = "NSE"
    instrument_key: Optional[str] = None


# ── OHLCV ────────────────────────────────────────────────────────────────────

class OHLCVBar(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVResponse(BaseModel):
    symbol: str
    timeframe: str
    bars: list[OHLCVBar]


# ── Live Price ────────────────────────────────────────────────────────────────

class LivePrice(BaseModel):
    symbol: str
    ltp: float                          # Last traded price
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None


class IndexData(BaseModel):
    name: str                           # e.g. "NIFTY 50"
    ltp: float
    change: float
    change_pct: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    advances: Optional[int] = None
    declines: Optional[int] = None


class MarketStatus(BaseModel):
    is_open: bool
    session: str                         # "pre_open" | "normal" | "closed"
    message: str
    next_open: Optional[str] = None


class MarketBreadth(BaseModel):
    advances: int
    declines: int
    unchanged: int
    advance_decline_ratio: float
    above_vwap: Optional[int] = None
    below_vwap: Optional[int] = None
    new_52w_highs: Optional[int] = None
    new_52w_lows: Optional[int] = None


# ── Screener ──────────────────────────────────────────────────────────────────

class ScanCondition(BaseModel):
    indicator: str                       # RSI, EMA, MACD_line, Close, etc.
    params: list[float] = []            # [14] for RSI(14), [9,26,9] for MACD
    operator: str                        # greater_than | less_than | crosses_above | etc.
    value: Optional[float] = None       # numeric threshold
    compare_indicator: Optional[str] = None  # compare to another indicator
    compare_params: Optional[list[float]] = None
    timeframe: str = "15min"
    lookback: int = 0                   # 0 = current candle, 1 = prev, etc.


class ScanFilters(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_market_cap: Optional[int] = None
    max_market_cap: Optional[int] = None
    sector: Optional[str] = None
    exchange: str = "NSE"               # NSE | BSE | BOTH


class ScanRunRequest(BaseModel):
    scan_id: Optional[UUID] = None      # if running a saved scan
    scan_name: Optional[str] = None
    conditions: list[ScanCondition]
    filters: Optional[ScanFilters] = None
    timeframe: str = "15min"
    universe: str = "NSE_ALL"           # NSE_ALL | NIFTY50 | NIFTY500 | NIFTY_MIDCAP150 | NIFTY_SMALLCAP250


class ScanResult(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    ltp: float
    change_pct: float
    volume: int
    volume_ratio: Optional[float] = None    # vol / vol_sma_20
    rsi_14: Optional[float] = None
    ema_status: Optional[str] = None        # "above_ema20" | "below_ema50" etc.
    matched_conditions: list[str] = []
    scan_triggered_at: datetime
    sector: Optional[str] = None
    market_cap: Optional[int] = None


class ScanRunResponse(BaseModel):
    scan_name: str
    timeframe: str
    universe: str
    results: list[ScanResult]
    result_count: int
    duration_ms: int
    run_at: datetime


class PrebuiltScan(BaseModel):
    id: str
    name: str
    description: str
    category: str                        # Pattern | Breakout | RSI | EMA | MACD | Volume | Trend | Intraday
    icon: str
    timeframe: str
    badge_color: str                     # amber | blue | green


# ── User Scans ────────────────────────────────────────────────────────────────

class UserScanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    conditions: list[ScanCondition]
    filters: Optional[ScanFilters] = None
    timeframe: str = "15min"
    universe: str = "NSE_ALL"


class UserScanResponse(OrmBase):
    id: UUID
    name: str
    description: Optional[str] = None
    conditions: Any
    filters: Optional[Any] = None
    timeframe: str
    universe: str
    is_active: bool
    run_count: int
    last_run_at: Optional[datetime] = None
    created_at: datetime


# ── Watchlist ─────────────────────────────────────────────────────────────────

class WatchlistItem(OrmBase):
    user_id: UUID
    symbol: str
    notes: Optional[str] = None
    added_at: datetime
    # Live data (injected at query time from Redis)
    ltp: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    rsi_14: Optional[float] = None
    ema20_status: Optional[str] = None
    scan_signal: Optional[str] = None
    company_name: Optional[str] = None
    sector: Optional[str] = None


class WatchlistAddRequest(BaseModel):
    notes: Optional[str] = None


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    symbol: Optional[str] = None
    scan_id: Optional[UUID] = None
    notify_email: bool = False
    notify_push: bool = True
    notify_telegram: bool = False
    telegram_chat_id: Optional[str] = None
    frequency: str = "once_per_day"     # once | every_time | once_per_day


class AlertResponse(OrmBase):
    id: UUID
    symbol: Optional[str] = None
    scan_id: Optional[UUID] = None
    notify_email: bool
    notify_push: bool
    notify_telegram: bool
    frequency: str
    is_active: bool
    last_triggered: Optional[datetime] = None
    created_at: datetime


class AlertHistoryItem(OrmBase):
    id: UUID
    alert_id: Optional[UUID] = None
    symbol: Optional[str] = None
    scan_name: Optional[str] = None
    trigger_price: Optional[Decimal] = None
    triggered_at: datetime
    conditions_met: Optional[Any] = None


# ── WebSocket Messages ────────────────────────────────────────────────────────

class WSPriceUpdate(BaseModel):
    type: str = "price_update"
    symbol: str
    ltp: float
    change_pct: float
    volume: int
    timestamp: float                    # Unix timestamp


class WSScanHit(BaseModel):
    type: str = "scan_hit"
    scan_id: str
    scan_name: str
    symbol: str
    ltp: float
    change_pct: float
    triggered_at: float
    matched_conditions: list[str]


class WSAlertTrigger(BaseModel):
    type: str = "alert_trigger"
    alert_id: str
    scan_name: str
    symbol: str
    trigger_price: float
    triggered_at: float


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    has_next: bool
    items: list[Any]

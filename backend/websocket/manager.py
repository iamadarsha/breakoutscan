"""
WebSocket Connection Manager.
Manages all connected WebSocket clients grouped by channel.
"""
from __future__ import annotations
import asyncio
import json
from typing import Optional

from fastapi import WebSocket
import structlog

log = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections organized by channel.
    Supports broadcasting to all, specific channels, or single connections.
    """

    def __init__(self):
        # channel → set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {
            "prices": set(),
            "scans": set(),
            "alerts": set(),
        }
        # Per-symbol subscriptions (for /ws/prices/{symbol})
        self._symbol_subs: dict[str, set[WebSocket]] = {}
        # Per-user alert subscriptions
        self._user_subs: dict[str, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel: str = "prices"):
        await ws.accept()
        if channel not in self._connections:
            self._connections[channel] = set()
        self._connections[channel].add(ws)
        log.info("ws_connected", channel=channel, total=len(self._connections[channel]))

    def disconnect(self, ws: WebSocket, channel: str = "prices"):
        self._connections.get(channel, set()).discard(ws)
        # Also remove from any symbol/user subs
        for subs in self._symbol_subs.values():
            subs.discard(ws)
        for subs in self._user_subs.values():
            subs.discard(ws)
        log.info("ws_disconnected", channel=channel)

    async def subscribe_to_symbol(self, ws: WebSocket, symbol: str):
        if symbol not in self._symbol_subs:
            self._symbol_subs[symbol] = set()
        self._symbol_subs[symbol].add(ws)

    async def subscribe_to_user_alerts(self, ws: WebSocket, user_id: str):
        if user_id not in self._user_subs:
            self._user_subs[user_id] = set()
        self._user_subs[user_id].add(ws)

    # ── Broadcasting ────────────────────────────────────────────────────────

    async def broadcast_price(self, symbol: str, ltp: float, change_pct: float, volume: int, ts: float):
        """Broadcast a price update to all price channel subscribers and symbol-specific subscribers."""
        msg = json.dumps({
            "type": "price_update",
            "symbol": symbol,
            "ltp": ltp,
            "change_pct": change_pct,
            "volume": volume,
            "ts": ts,
        })
        # Broadcast to general price channel
        await self._broadcast_to_channel("prices", msg)
        # Broadcast to symbol-specific subscribers
        await self._broadcast_to_set(self._symbol_subs.get(symbol, set()), msg)

    async def broadcast_scan_hit(self, scan_id: str, scan_name: str, symbol: str, ltp: float, matched: list, ts: float):
        """Broadcast a scan hit to all scan subscribers."""
        msg = json.dumps({
            "type": "scan_hit",
            "scan_id": scan_id,
            "scan_name": scan_name,
            "symbol": symbol,
            "ltp": ltp,
            "matched_conditions": matched,
            "ts": ts,
        })
        await self._broadcast_to_channel("scans", msg)

    async def broadcast_alert_trigger(self, user_id: str, alert_id: str, scan_name: str, symbol: str, trigger_price: float, ts: float):
        """Broadcast a personal alert trigger to a specific user."""
        msg = json.dumps({
            "type": "alert_trigger",
            "alert_id": alert_id,
            "scan_name": scan_name,
            "symbol": symbol,
            "trigger_price": trigger_price,
            "ts": ts,
        })
        await self._broadcast_to_set(self._user_subs.get(user_id, set()), msg)

    async def _broadcast_to_channel(self, channel: str, msg: str):
        await self._broadcast_to_set(self._connections.get(channel, set()), msg)

    async def _broadcast_to_set(self, connections: set, msg: str):
        """Send message to a set of WebSocket connections, removing dead ones."""
        if not connections:
            return
        dead = set()
        for ws in list(connections):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        connections -= dead

    def connection_count(self, channel: str = "prices") -> int:
        return len(self._connections.get(channel, set()))


# ── Global singleton ───────────────────────────────────────────────────────

_manager: Optional[ConnectionManager] = None


def get_ws_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager

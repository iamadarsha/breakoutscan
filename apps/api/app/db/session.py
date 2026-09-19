from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def _get_engine():
    """Lazily create the SQLAlchemy async engine on first use."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args: dict = {}
        if "localhost" not in settings.database_url and "127.0.0.1" not in settings.database_url:
            connect_args["ssl"] = "require"
        # Disable prepared statement caching for PgBouncer transaction-mode poolers
        # (Supabase port 6543 uses PgBouncer in transaction mode, which doesn't
        # support named prepared statements that asyncpg sends by default).
        if (
            ":6543" in settings.database_url
            or "-pooler" in settings.database_url
            or settings.db_disable_statement_cache
        ):
            connect_args["statement_cache_size"] = 0
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_timeout=15,
            pool_recycle=1800,
            # Kept well under Supabase's free-tier Session Pooler cap
            # (Supavisor: 15 concurrent connections, PROJECT-wide, not
            # per-process). 5+10=15 let this single process alone claim
            # the entire project quota (confirmed live 2026-09-15: one
            # `alembic upgrade` alongside the running app hit "max clients
            # reached in session mode" immediately). Widening the pool to
            # chase QueuePool timeouts (3+2, then 8+4) was the wrong axis
            # entirely — it treats Postgres as the app's concurrency
            # controller. The actual fix is work-shaping on the demand
            # side (breakout concurrency cut from 20 to 4, the 500-symbol
            # scan staggered in chunks instead of launched as one burst,
            # signal persistence consolidated onto one session instead of
            # 2-3 separate checkouts per symbol — see engine.py). With
            # demand shaped down, a small fixed pool and zero overflow is
            # both sufficient and leaves real headroom under the 15 cap.
            pool_size=settings.db_pool_size,
            max_overflow=0,
            connect_args=connect_args,
        )
        logger.info("Database engine created")
    return _engine


def _get_session_factory():
    """Lazily create the session factory on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = _get_session_factory()
    async with factory() as session:
        yield session


class _SessionLocalProxy:
    """Proxy so ``async with SessionLocal() as session:`` works lazily."""

    def __call__(self) -> AsyncSession:
        return _get_session_factory()()


SessionLocal = _SessionLocalProxy()


async def check_db_connectivity() -> bool:
    """``SELECT 1`` against the configured database. True on success.

    Never raises — callers (startup validation, /health/ready) treat any
    failure the same way: DB is not currently reachable.
    """
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database connectivity check failed")
        return False

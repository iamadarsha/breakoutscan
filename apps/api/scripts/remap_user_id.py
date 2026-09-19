#!/usr/bin/env python3
"""Move one user's watchlist/alerts/scans to a new user id.

Needed only when switching identity providers for a user who already has data:
their user id changes (Supabase UUID -> the uuid the new provider's subject
maps to; see app/core/auth_tokens.py). The new id is what the API logs or what
`user_id_from_claims({...})` returns.

    python scripts/remap_user_id.py --database "postgresql://..." --old <uuid> --new <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

import asyncpg

TABLES = ("watchlist", "alerts", "alert_history", "user_scans", "scan_runs")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    p.add_argument("--old", required=True, type=uuid.UUID)
    p.add_argument("--new", required=True, type=uuid.UUID)
    a = p.parse_args()
    url = a.database.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, statement_cache_size=0, ssl=None if "localhost" in url else "require")
    try:
        async with conn.transaction():
            for table in TABLES:
                has = await conn.fetchval(
                    "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                    "AND table_name=$1 AND column_name='user_id'", table)
                if not has:
                    continue
                result = await conn.execute(f'UPDATE "{table}" SET user_id=$1 WHERE user_id=$2', a.new, a.old)
                print(f"{table}: {result}")
    finally:
        await conn.close()


asyncio.run(main())

#!/usr/bin/env python3
"""Copy the BreakoutScan database between any two Postgres servers.

    python scripts/migrate_database.py \
        --source "postgresql://user:pass@old-host:5432/db" \
        --target "postgresql://user:pass@new-host/db?sslmode=require" \
        --create-schema --skip ohlcv_1min

--create-schema runs `alembic upgrade head` on the target first. Tables are
copied in dependency order (`stocks` first). A non-empty target table aborts
unless --truncate is given. Counts are verified at the end. The huge
1-minute candle table is disposable (it refills within a session), so skipping
it is the recommended way to move quickly onto a small free tier.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg

API_DIR = Path(__file__).resolve().parents[1]
CHUNK = 5000


def _normalize(url: str) -> str:
    # asyncpg wants a plain postgresql:// URL and takes SSL as a keyword.
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url.split("?", 1)[0]


def _connect_kwargs(url: str) -> dict:
    local = "localhost" in url or "127.0.0.1" in url
    kwargs: dict = {"statement_cache_size": 0, "timeout": 60}
    if not local:
        kwargs["ssl"] = "require"
    return kwargs


async def _tables(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name <> 'alembic_version'"
    )
    names = sorted(r["table_name"] for r in rows)
    return (["stocks"] if "stocks" in names else []) + [n for n in names if n != "stocks"]


async def _copy_table(src: asyncpg.Connection, dst: asyncpg.Connection, table: str, truncate: bool) -> int:
    existing = await dst.fetchval(f'SELECT count(*) FROM "{table}"')
    if existing and not truncate:
        raise SystemExit(f'target table "{table}" already has {existing} rows; pass --truncate to replace')
    if existing:
        await dst.execute(f'TRUNCATE "{table}" CASCADE')

    columns = [
        r["column_name"]
        for r in await src.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
            "AND table_name=$1 ORDER BY ordinal_position",
            table,
        )
    ]
    quoted = ", ".join(f'"{c}"' for c in columns)

    copied = 0
    async with src.transaction():
        batch: list[tuple] = []
        async for row in src.cursor(f'SELECT {quoted} FROM "{table}"', prefetch=CHUNK):
            batch.append(tuple(row))
            if len(batch) >= CHUNK:
                await dst.copy_records_to_table(table, records=batch, columns=columns)
                copied += len(batch)
                batch = []
        if batch:
            await dst.copy_records_to_table(table, records=batch, columns=columns)
            copied += len(batch)
    return copied


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--skip", default="", help="comma-separated tables to leave out (e.g. ohlcv_1min)")
    parser.add_argument("--create-schema", action="store_true", help="run alembic upgrade head on the target first")
    parser.add_argument("--truncate", action="store_true", help="replace rows already in target tables")
    args = parser.parse_args()

    source, target = _normalize(args.source), _normalize(args.target)
    skip = {t.strip() for t in args.skip.split(",") if t.strip()}

    if args.create_schema:
        env = {**os.environ, "DATABASE_URL": target.replace("postgresql://", "postgresql+asyncpg://", 1)}
        print("Creating schema on target (alembic upgrade head)...")
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=API_DIR, env=env, check=True)

    src = await asyncpg.connect(source, **_connect_kwargs(source))
    dst = await asyncpg.connect(target, **_connect_kwargs(target))
    try:
        mismatches = 0
        for table in await _tables(src):
            if table in skip:
                print(f"  skip     {table}")
                continue
            copied = await _copy_table(src, dst, table, args.truncate)
            expected = await src.fetchval(f'SELECT count(*) FROM "{table}"')
            actual = await dst.fetchval(f'SELECT count(*) FROM "{table}"')
            ok = actual == expected
            mismatches += not ok
            print(f"  {'ok      ' if ok else 'MISMATCH'} {table}: copied {copied}, source {expected}, target {actual}")
        return 1 if mismatches else 0
    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

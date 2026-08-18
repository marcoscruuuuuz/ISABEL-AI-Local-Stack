"""Camada de banco asyncpg com fallback in-memory quando Postgres estiver offline."""
from __future__ import annotations
import logging
from typing import Optional
import asyncpg
from app.core.config import settings

log = logging.getLogger("isabel.db")
_pool: Optional[asyncpg.Pool] = None
_db_ok: bool = False

async def get_pool() -> Optional[asyncpg.Pool]:
    global _pool, _db_ok
    if _pool is not None:
        return _pool
    try:
        dsn = settings.database_url
        if dsn.startswith("postgresql+asyncpg://"):
            dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=8, command_timeout=30)
        _db_ok = True
        log.info("Postgres pool ready")
        return _pool
    except Exception as e:
        log.warning(f"Postgres indisponivel, usando memoria: {e}")
        _db_ok = False
        _pool = None
        return None

async def close_pool():
    global _pool, _db_ok
    if _pool:
        await _pool.close()
        _pool = None
    _db_ok = False

def is_db_available() -> bool:
    return _db_ok

async def fetch(query: str, *args) -> list:
    pool = await get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]

async def fetchrow(query: str, *args) -> Optional[dict]:
    pool = await get_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None

async def execute(query: str, *args) -> str:
    pool = await get_pool()
    if not pool:
        return "NO_DB"
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

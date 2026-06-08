from __future__ import annotations

from ..core.response import ok
from ..database import get_pool


async def health_check() -> dict:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        db_status = "ok"
    except Exception:
        db_status = "unavailable"
    return ok({"status": "healthy", "database": db_status, "version": "0.1.0"})

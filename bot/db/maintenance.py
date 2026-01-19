from datetime import datetime
import db.pool as pool

async def set_maintenance(enabled: bool, message: str = None,
                          start: datetime = None, end: datetime = None):
    async with pool.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO bot_status (id, maintenance, maintenance_message, maintenance_start, maintenance_end)
            VALUES (1, $1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET
                maintenance = $1,
                maintenance_message = $2,
                maintenance_start = $3,
                maintenance_end = $4
        """, enabled, message, start, end)


async def get_maintenance_status():
    async with pool.db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM bot_status WHERE id = 1")


async def get_status_maintenance():
    async with pool.db_pool.acquire() as conn:
        status = await conn.fetchrow("SELECT maintenance_message FROM bot_status WHERE id = 1")
        return status
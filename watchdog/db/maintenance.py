import datetime
import logging
from watchdog_db import *


async def set_maintenance(
    start_time: datetime,
    end_time: datetime,
    reason: str = "Automatic system update"
) -> bool:
    """
    Struttura tabella (da bot/db/pool.py):
    CREATE TABLE IF NOT EXISTS maintenance (
        id INT PRIMARY KEY,
        maintenance_status TEXT,
        maintenance_message TEXT,
        maintenance_start timestamptz,
        maintenance_start timestamptz
    )
    """
    try:
        query = """
            INSERT INTO maintenance (maintenance_start, maintenance_start, maintenance_message)
            VALUES ($1, $2, $3)
            RETURNING id
        """
        result = await db_pool.fetchrow(query, start_time, end_time, reason)
        logging.info(f"Maintenance scheduled (ID: {result['id']}) from {start_time} to {end_time}")
        return True
    except Exception as e:
        logging.error(f"Failed to set maintenance: {e}")
        return False

async def clear_maintenance():
    try:
        query = "DELETE FROM maintenance WHERE end_time > NOW()"
        await db_pool.execute(query)
        logging.info("Maintenance records cleared")
    except Exception as e:
        logging.error(f"Failed to clear maintenance: {e}")

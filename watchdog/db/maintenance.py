import logging
from datetime import datetime, timezone
from typing import Optional
from .watchdog_db import db_pool


async def set_maintenance(
    status: str,                        # "inactive" | "scheduled" | "active"
    message: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> bool:
    """
    Scrive lo stato di manutenzione nella tabella bot_status (id=1).

    Schema (da bot/db/pool.py):
        CREATE TABLE IF NOT EXISTS bot_status (
            id INT PRIMARY KEY,
            maintenance_status TEXT,
            maintenance_message TEXT,
            maintenance_start timestamptz,
            maintenance_end timestamptz
        )
    """
    # Assicuriamoci che start/end siano UTC-aware
    if start and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    try:
        query = """
            INSERT INTO bot_status (id, maintenance_status, maintenance_message, maintenance_start, maintenance_end)
            VALUES (1, $1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET
                maintenance_status  = EXCLUDED.maintenance_status,
                maintenance_message = EXCLUDED.maintenance_message,
                maintenance_start   = EXCLUDED.maintenance_start,
                maintenance_end     = EXCLUDED.maintenance_end
        """
        await db_pool.execute(query, status, message, start, end)
        logging.info(f"Maintenance state set to '{status}' (start={start}, end={end})")
        return True
    except Exception as e:
        logging.error(f"Failed to set maintenance state: {e}")
        return False


async def clear_maintenance() -> bool:
    """Porta lo stato di manutenzione a 'inactive' (con start/end a None)."""
    return await set_maintenance(status="inactive", message=None, start=None, end=None)


async def get_maintenance_status() -> dict | None:
    """Ritorna il record bot_status (id=1) come dizionario, oppure None."""
    try:
        row = await db_pool.fetchrow("SELECT * FROM bot_status WHERE id = 1")
        if not row:
            return None
        status = dict(row)
        # Assicuriamoci che start/end siano UTC-aware
        for key in ("maintenance_start", "maintenance_end"):
            if status.get(key) and status[key].tzinfo is None:
                status[key] = status[key].replace(tzinfo=timezone.utc)
        return status
    except Exception as e:
        logging.error(f"Failed to get maintenance status: {e}")
        return None


async def is_in_maintenance() -> bool:
    """Restituisce True se siamo attualmente dentro la finestra di manutenzione."""
    try:
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM bot_status
                WHERE id = 1
                  AND maintenance_status = 'active'
                  AND NOW() BETWEEN maintenance_start AND maintenance_end
            ) AS in_maintenance
        """
        result = await db_pool.fetchrow(query)
        return result["in_maintenance"] if result else False
    except Exception as e:
        logging.error(f"Failed to check maintenance status: {e}")
        return False
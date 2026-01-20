from datetime import datetime, timezone
import db.pool as pool
import logging

# ================== MAINTENANCE ==================

async def set_maintenance(
    status: str,  # "inactive", "scheduled", "active"
    message: str = None,
    start: datetime = None,
    end: datetime = None
):
    # Assicuriamoci che start/end siano UTC-aware
    if start and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    async with pool.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO bot_status (id, maintenance_status, maintenance_message, maintenance_start, maintenance_end)
            VALUES (1, $1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET
                maintenance_status = $1,
                maintenance_message = $2,
                maintenance_start = $3,
                maintenance_end = $4
        """, status, message, start, end)


async def get_maintenance_status() -> dict | None:
    async with pool.db_pool.acquire() as conn:
        status = await conn.fetchrow("SELECT * FROM bot_status WHERE id = 1")

    if not status:
        return None

    status = dict(status)

    # Assicuriamoci che start/end siano UTC-aware
    for key in ["maintenance_start", "maintenance_end"]:
        if status.get(key) and status[key].tzinfo is None:
            status[key] = status[key].replace(tzinfo=timezone.utc)

    return status


async def update_maintenance_state_if_needed():
    """
    Controlla start/end e aggiorna lo stato automaticamente.
    Deve essere chiamata nel loop.
    """
    status = await get_maintenance_status()
    if not status:
        return "inactive", None

    now = datetime.now(timezone.utc)
    start = status.get("maintenance_start")
    end = status.get("maintenance_end")
    current_state = status.get("maintenance_status") or "inactive"

    new_state = current_state

    if end and now >= end:
        new_state = "inactive"
    elif start and now >= start:
        new_state = "active"
    elif start and now < start:
        new_state = "scheduled"
    else:
        new_state = "inactive"

    if new_state != current_state:
        await set_maintenance(
            status=new_state,
            message=status.get("maintenance_message"),
            start=start,
            end=end
        )

    return new_state, status


# ================== STATUS MESSAGE ==================

async def save_status_message(channel_id: int, message_id: int, lang: str):
    async with pool.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO status_message (id, channel_id, message_id, lang)
            VALUES (1, $1, $2, $3)
            ON CONFLICT (id) DO UPDATE
                SET channel_id = $1,
                    message_id = $2,
                    lang = $3
        """, channel_id, message_id,lang)


async def get_status_message():
    async with pool.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT channel_id, message_id, lang FROM status_message WHERE id = 1")
        if row:
            return row["channel_id"], row["message_id"], row["lang"]
        return None, None, None
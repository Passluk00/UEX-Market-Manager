import db.pool
import logging

# -------------------------------
# Controllo se un utente è bannato
# -------------------------------
async def is_banned(user_id: int) -> tuple[bool, str | None]:
    """
    Controlla se un utente è bannato.
    Restituisce:
        (True, reason) se bannato
        (False, None) se non bannato
    """
    user_id = str(user_id)
    try:
        async with db.pool.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, motivation FROM banned_users WHERE user_id=$1",
                user_id
            )
            if row:
                return True, row["motivation"] or None
            return False, None

    except Exception as e:
        logging.error(f"Error checking ban for user {user_id}: {e}")
        return False, None

# -------------------------------
# Bannare un utente
# -------------------------------
async def ban_user(user_id: int, reason: str):
    """
    Inserisce o aggiorna un utente nella tabella banned_users
    """
    user_id = str(user_id)
    try:
        async with db.pool.db_pool.acquire() as conn:
            # upsert: se esiste aggiorna, altrimenti inserisce
            await conn.execute(
                """
                INSERT INTO banned_users(user_id, motivation)
                VALUES($1, $2)
                ON CONFLICT(user_id) DO UPDATE SET motivation = EXCLUDED.motivation
                """,
                user_id, reason
            )
    except Exception as e:
        logging.error(f"Error banning user {user_id}: {e}")

# -------------------------------
# Rimuovere il ban da un utente
# -------------------------------
async def unban_user(user_id: int):
    """
    Rimuove un utente dalla tabella banned_users
    """
    user_id = str(user_id)
    try:
        async with db.pool.db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM banned_users WHERE user_id=$1",
                user_id
            )
    except Exception as e:
        logging.error(f"Error unbanning user {user_id}: {e}")

import discord
import logging
import db.pool
from utils.cryptography import encrypt,decrypt


async def save_user_session(
    user_id: str,
    thread_id: int | None = None,
    uex_username: str | None = None,
    bearer_token: str | None = None,
    secret_key: str | None = None,
    enable: bool | None = None,
    welcome_message: str | None = None,
    language: str | None = None,
):
    
    """
    Saves or updates a user session. Uses ON CONFLICT to update existing records.

    Args:
        user_id (str): The unique Discord user ID.
        thread_id (int | None): The Discord thread ID associated with the user.
        uex_username (str | None): The UEX platform username.
        bearer_token (str | None): API authentication bearer token.
        secret_key (str | None): API authentication secret key.
        enable (bool | None): Whether automated messages are enabled.
        welcome_message (str | None): The custom message sent to new buyers.
        language (str | None): The preferred language code (e.g., 'en', 'it').

    Returns:
        None
    """
    
    
    
    user_id = str(user_id)

    encrypted_bearer = encrypt(bearer_token) if bearer_token else None
    encrypted_secret = encrypt(secret_key) if secret_key else None



    async with db.pool.db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (
                user_id,
                thread_id,
                uex_username,
                bearer_token,
                secret_key,
                enable,
                welcome_message,
                language
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id)
            DO UPDATE SET
                thread_id = COALESCE(EXCLUDED.thread_id, sessions.thread_id),
                uex_username = COALESCE(EXCLUDED.uex_username, sessions.uex_username),
                bearer_token = COALESCE(EXCLUDED.bearer_token, sessions.bearer_token),
                secret_key = COALESCE(EXCLUDED.secret_key, sessions.secret_key),
                enable = COALESCE(EXCLUDED.enable, sessions.enable),
                welcome_message = COALESCE(EXCLUDED.welcome_message, sessions.welcome_message),
                language = COALESCE(EXCLUDED.language, sessions.language),
                last_update = NOW()
            """,
            user_id,
            thread_id,
            uex_username,
            encrypted_bearer,
            encrypted_secret,
            enable,
            welcome_message,
            language
        )

    logging.info(f"💾 Session saved for {user_id}")


async def get_user_session(user_id: str) -> dict | None:
   
    """
    Retrieves the complete session data for a specific user.

    Args:
        user_id (str): The unique Discord user ID.

    Returns:
        dict | None: A dictionary containing all session fields, or None if not found.
    """
    
    uid = str(user_id)
    async with db.pool.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE user_id = $1",
            uid
        )

    if row is None:
        return None
    
    data = dict(row)
    data["bearer_token"] = decrypt(data.get("bearer_token"))
    data["secret_key"] = decrypt(data.get("secret_key"))
    
    return data


async def remove_user_session(user_id: str):
    
    """
    Permanently deletes a user's session from the database.

    Args:
        user_id (str): The unique Discord user ID to remove.

    Returns:
        None
    """
    
    user_id = str(user_id)

    async with db.pool.db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM sessions WHERE user_id = $1",
            user_id
        )

    logging.info(f"🗑️ Sessione rimossa per {user_id}")


async def get_user_thread_id(user_id: str) -> int | None:
    
    """
    Retrieves only the Discord thread ID associated with a user.

    Args:
        user_id (str): The unique Discord user ID.

    Returns:
        int | None: The thread ID if it exists, otherwise None.
    """
    
    
    user_id = str(user_id)

    async with db.pool.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT thread_id FROM sessions WHERE user_id = $1",
            user_id
        )

    return row["thread_id"] if row and row["thread_id"] else None


async def get_user_keys(user_id: str) -> tuple[str, str]:
    
    """
    Retrieves the API credentials (bearer token and secret key) for a user.

    Args:
        user_id (str): The unique Discord user ID.

    Returns:
        tuple[str, str]: A tuple containing (bearer_token, secret_key). Returns empty strings if not found.
    """
    
    user_id = str(user_id)

    async with db.pool.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT bearer_token, secret_key
            FROM sessions
            WHERE user_id = $1
            """,
            user_id
        )

    if not row:
        return "", ""
    
    token = decrypt(row["bearer_token"]) or ""
    secret = decrypt(row["secret_key"]) or ""
    
    return token, secret


async def get_user_welcome_message(user_id: str) -> tuple[bool, str | None]:

    """
    Checks if the welcome message is enabled and retrieves its content.

    Args:
        user_id (str): The unique Discord user ID.

    Returns:
        tuple[bool, str | None]: A tuple containing (is_enabled, message_text).
    """


    user_id = str(user_id)

    async with db.pool.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT enable, welcome_message
            FROM sessions
            WHERE user_id = $1
            """,
            user_id
        )

    if not row:
        return False, None

    return bool(row["enable"]), row["welcome_message"] or None


async def find_session_by_username(uex_username: str) -> dict | None:
    
    """
    Searches for a user session using their UEX platform username instead of Discord ID.

    Args:
        uex_username (str): The UEX username to search for.

    Returns:
        dict | None: The session data as a dictionary, or None if no match is found.
    """
    
    async with db.pool.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT *
            FROM sessions
            WHERE uex_username = $1
            """,
            uex_username
        )

    if not row: 
        return None

    data = dict(row)
    data["bearer_token"] = decrypt(data.get("bearer_token"))
    data["secret_key"] = decrypt(data.get("secret_key"))
    return data


async def get_user_language(user_id):
    
    """
    Gets the preferred language for a user.

    Args:
        user_id (str/int): The unique Discord user ID.

    Returns:
        str | None: The language code (e.g., 'it') or None if an error occurs or user is not found.
    """
        
    try:
        async with db.pool.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT language FROM sessions WHERE user_id = $1",
                str(user_id)
            )
            return row['language'] if row else None
    except Exception as e:
        logging.error(f"❌ Errore query get_user_language: {e}")
        return None


async def resolve_and_store_language(interaction: discord.Interaction) -> str:
    
    """
    Determines the user's language based on existing session data or Discord locale.
    Automatically saves the detected language if no session exists.

    Args:
        interaction (discord.Interaction): The Discord interaction object.

    Returns:
        str: The resolved language code.
    """
    
    user_id = interaction.user.id
    
    lang = await get_user_language(user_id)
    if lang:
        return lang
    
    if interaction.locale:
        lang = interaction.locale.value.split("-")[0]
    else:
        lang = "en"

    await save_user_session(
        user_id=user_id, 
        language=lang)

    return lang


async def remove_sessions_by_thread(thread_id: int) -> int:

    """
    Removes all sessions associated with a specific Discord thread ID.

    Args:
        thread_id (int): The Discord thread ID.

    Returns:
        int: The number of sessions successfully removed.
    """

    removed_count = 0
    try:
        async with db.pool.db_pool.acquire() as conn:
            rows = await conn.fetchrow("SELECT user_id FROM sessions WHERE thread_id = $1", thread_id)
            
            if rows:
                await conn.execute("DELETE FROM sessions WHERE thread_id = $1", thread_id)
                removed_count = len(rows)
    except Exception as e:
        import logging
        logging.exception(f"💥 Error removing sessions by thread {thread_id}: {e}")
    
    return removed_count      

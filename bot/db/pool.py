import asyncpg
import logging
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

db_pool = None


async def init_db():
    
    """
    Initializes the PostgreSQL database connection pool and creates required tables.

    This function sets up a global asyncpg connection pool with a size between 1 and 10 
    connections. It ensures that the 'sessions' and 'negotiation_links' tables exist 
    in the database before the application starts.

    Returns:
        asyncpg.pool.Pool|None: The initialized database pool object, or None if initialization fails.

    Raises:
        Exception: If there is a connection error or a failure during table creation.
    """
    
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            min_size=1,
            max_size=10,
        )

        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    uex_username TEXT,
                    thread_id BIGINT,
                    bearer_token TEXT,
                    secret_key TEXT,
                    enable BOOLEAN DEFAULT FALSE,
                    welcome_message TEXT DEFAULT '',
                    language TEXT DEFAULT 'en',
                    last_update TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS negotiation_links (
                    negotiation_hash TEXT PRIMARY KEY,
                    buyer_id TEXT NOT NULL,
                    seller_id TEXT NOT NULL
                );
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id TEXT PRIMARY KEY,
                    motivation TEXT
                );
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS status_message (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT,
                    message_id BIGINT,
                    lang TEXT NOT NULL
                );             
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_status (
                    id INT PRIMARY KEY,
                    maintenance_status TEXT,
                    maintenance_message TEXT,
                    maintenance_start timestamptz,
                    maintenance_end timestamptz
                );
            """)

        logging.info("📦 Database initialized and ready")
        return db_pool

    except Exception as e:
        logging.exception(f"❌ Error initializing DB: {e}")
        db_pool = None
        raise

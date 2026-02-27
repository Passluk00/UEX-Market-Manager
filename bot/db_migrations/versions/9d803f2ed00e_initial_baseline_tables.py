"""Initial baseline tables

Revision ID: 9d803f2ed00e
Revises: 
Create Date: 2026-02-27 18:33:49.986134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d803f2ed00e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. sessions
    op.execute("""
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

    # 2. negotiation_links
    op.execute("""
        CREATE TABLE IF NOT EXISTS negotiation_links (
            negotiation_hash TEXT PRIMARY KEY,
            buyer_id TEXT NOT NULL,
            seller_id TEXT NOT NULL
        );
    """)

    # 3. banned_users
    op.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id TEXT PRIMARY KEY,
            motivation TEXT
        );
    """)

    # 4. status_message
    op.execute("""
        CREATE TABLE IF NOT EXISTS status_message (
            id SERIAL PRIMARY KEY,
            channel_id BIGINT,
            message_id BIGINT,
            lang TEXT NOT NULL
        );             
    """)

    # 5. bot_status
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_status (
            id INT PRIMARY KEY,
            maintenance_status TEXT,
            maintenance_message TEXT,
            maintenance_start timestamptz,
            maintenance_end timestamptz
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bot_status;")
    op.execute("DROP TABLE IF EXISTS status_message;")
    op.execute("DROP TABLE IF EXISTS banned_users;")
    op.execute("DROP TABLE IF EXISTS negotiation_links;")
    op.execute("DROP TABLE IF EXISTS sessions;")

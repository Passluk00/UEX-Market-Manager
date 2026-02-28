# bot/tests/test_bot_maintenance.py
"""
Tests per bot/db/maintenance.py

Il modulo usa `pool.db_pool` (importato come `import db.pool as pool`),
quindi il patch target è 'db.pool.db_pool'.

Copre:
- set_maintenance()               — scrittura OK, errore DB
- get_maintenance_status()        — trovato, assente, UTC-naivety fix
- update_maintenance_state_if_needed() — transizioni scheduled→active, active→inactive, nessun record
- save_status_message()           — scrittura OK
- get_status_message()            — trovato, assente
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


def _make_ctx(fetchrow_result=None):
    """Helper: crea un context manager per db_pool.acquire() con conn mockato."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return conn, ctx


def _make_pool(conn_ctx):
    pool = MagicMock()
    pool.acquire.return_value = conn_ctx
    return pool


# ---------------------------------------------------------------------------
# set_maintenance
# ---------------------------------------------------------------------------

class TestBotSetMaintenance:

    @pytest.mark.asyncio
    async def test_executes_upsert_on_bot_status(self):
        """set_maintenance esegue una INSERT ... ON CONFLICT nella tabella bot_status."""
        conn, ctx = _make_ctx()
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import set_maintenance
            await set_maintenance("scheduled", "Update", None, None)

        conn.execute.assert_awaited_once()
        query = conn.execute.call_args[0][0]
        assert "bot_status" in query

    @pytest.mark.asyncio
    async def test_passes_status_as_first_param(self):
        """Il primo parametro posizionale dopo la query è lo status."""
        conn, ctx = _make_ctx()
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import set_maintenance
            await set_maintenance("active", None, None, None)

        args = conn.execute.call_args[0]
        assert args[1] == "active"

    @pytest.mark.asyncio
    async def test_adds_utc_timezone_to_naive_datetimes(self):
        """Datetime naive viene reso UTC-aware prima dell'esecuzione."""
        conn, ctx = _make_ctx()
        pool = _make_pool(ctx)
        naive_start = datetime(2025, 1, 1, 3, 0, 0)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import set_maintenance
            await set_maintenance("scheduled", None, naive_start, None)

        args = conn.execute.call_args[0]
        passed_start = args[3]
        assert passed_start.tzinfo is not None

    @pytest.mark.asyncio
    async def test_propagates_db_exception(self):
        """Eccezione dal DB viene propagata (set_maintenance non la sopprime)."""
        conn, ctx = _make_ctx()
        conn.execute = AsyncMock(side_effect=Exception("DB error"))
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import set_maintenance
            with pytest.raises(Exception, match="DB error"):
                await set_maintenance("active", None, None, None)


# ---------------------------------------------------------------------------
# get_maintenance_status
# ---------------------------------------------------------------------------

class TestBotGetMaintenanceStatus:

    @pytest.mark.asyncio
    async def test_returns_dict_when_record_exists(self):
        now = datetime.now(timezone.utc)
        fake_row = {
            "id": 1,
            "maintenance_status": "active",
            "maintenance_message": "Update",
            "maintenance_start": now,
            "maintenance_end": now + timedelta(minutes=30),
        }
        conn, ctx = _make_ctx(fetchrow_result=fake_row)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result is not None
        assert result["maintenance_status"] == "active"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_record(self):
        conn, ctx = _make_ctx(fetchrow_result=None)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result is None

    @pytest.mark.asyncio
    async def test_makes_naive_datetimes_utc_aware(self):
        """Datetime naive nel DB → aggiunge timezone UTC."""
        naive = datetime(2025, 6, 1, 12, 0)
        fake_row = {
            "id": 1,
            "maintenance_status": "scheduled",
            "maintenance_message": None,
            "maintenance_start": naive,
            "maintenance_end": naive + timedelta(hours=1),
        }
        conn, ctx = _make_ctx(fetchrow_result=fake_row)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result["maintenance_start"].tzinfo is not None
        assert result["maintenance_end"].tzinfo is not None


# ---------------------------------------------------------------------------
# update_maintenance_state_if_needed
# ---------------------------------------------------------------------------

class TestUpdateMaintenanceStateIfNeeded:

    @pytest.mark.asyncio
    async def test_returns_inactive_when_no_record(self):
        conn, ctx = _make_ctx(fetchrow_result=None)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import update_maintenance_state_if_needed
            state, status = await update_maintenance_state_if_needed()

        assert state == "inactive"
        assert status is None

    @pytest.mark.asyncio
    async def test_transitions_scheduled_to_active_when_start_passed(self):
        """start passato + end futuro → state diventa 'active'."""
        now = datetime.now(timezone.utc)
        fake_row = {
            "id": 1,
            "maintenance_status": "scheduled",
            "maintenance_message": "Update",
            "maintenance_start": now - timedelta(minutes=5),
            "maintenance_end": now + timedelta(minutes=25),
        }
        conn, ctx = _make_ctx(fetchrow_result=fake_row)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import update_maintenance_state_if_needed
            state, _ = await update_maintenance_state_if_needed()

        assert state == "active"

    @pytest.mark.asyncio
    async def test_transitions_active_to_inactive_when_end_passed(self):
        """end passato → state diventa 'inactive'."""
        now = datetime.now(timezone.utc)
        fake_row = {
            "id": 1,
            "maintenance_status": "active",
            "maintenance_message": "Update",
            "maintenance_start": now - timedelta(hours=1),
            "maintenance_end": now - timedelta(minutes=1),
        }
        conn, ctx = _make_ctx(fetchrow_result=fake_row)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import update_maintenance_state_if_needed
            state, _ = await update_maintenance_state_if_needed()

        assert state == "inactive"

    @pytest.mark.asyncio
    async def test_stays_scheduled_when_start_is_future(self):
        """start futuro → rimane 'scheduled'."""
        now = datetime.now(timezone.utc)
        fake_row = {
            "id": 1,
            "maintenance_status": "scheduled",
            "maintenance_message": None,
            "maintenance_start": now + timedelta(minutes=20),
            "maintenance_end": now + timedelta(minutes=50),
        }
        conn, ctx = _make_ctx(fetchrow_result=fake_row)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import update_maintenance_state_if_needed
            state, _ = await update_maintenance_state_if_needed()

        assert state == "scheduled"


# ---------------------------------------------------------------------------
# save_status_message
# ---------------------------------------------------------------------------

class TestSaveStatusMessage:

    @pytest.mark.asyncio
    async def test_executes_upsert(self):
        conn, ctx = _make_ctx()
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import save_status_message
            await save_status_message(channel_id=111, message_id=222, lang="en")

        conn.execute.assert_awaited_once()
        query = conn.execute.call_args[0][0]
        assert "status_message" in query

    @pytest.mark.asyncio
    async def test_passes_correct_args(self):
        conn, ctx = _make_ctx()
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import save_status_message
            await save_status_message(channel_id=42, message_id=99, lang="it")

        args = conn.execute.call_args[0]
        assert 42 in args
        assert 99 in args
        assert "it" in args


# ---------------------------------------------------------------------------
# get_status_message
# ---------------------------------------------------------------------------

class TestGetStatusMessage:

    @pytest.mark.asyncio
    async def test_returns_tuple_when_found(self):
        fake_row = {"channel_id": 10, "message_id": 20, "lang": "en"}
        conn, ctx = _make_ctx(fetchrow_result=fake_row)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import get_status_message
            ch, msg, lang = await get_status_message()

        assert ch == 10
        assert msg == 20
        assert lang == "en"

    @pytest.mark.asyncio
    async def test_returns_none_tuple_when_not_found(self):
        conn, ctx = _make_ctx(fetchrow_result=None)
        pool = _make_pool(ctx)

        with patch('db.pool.db_pool', pool):
            from db.maintenance import get_status_message
            ch, msg, lang = await get_status_message()

        assert ch is None
        assert msg is None
        assert lang is None

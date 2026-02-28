# watchdog/tests/test_maintenance.py
"""
Tests per watchdog/db/maintenance.py

Copre:
- set_maintenance()       — scrittura OK, errore DB, UTC-naivety fix
- clear_maintenance()     — delega corretta a set_maintenance inactive
- get_maintenance_status()— record trovato, assente, UTC-naivety fix
- is_in_maintenance()     — query True/False, eccezione DB
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


def _make_db_pool_mock(fetchrow_return=None, execute_return=None):
    pool = MagicMock()
    pool.execute = AsyncMock(return_value=execute_return)
    pool.fetchrow = AsyncMock(return_value=fetchrow_return)
    return pool


# ---------------------------------------------------------------------------
# set_maintenance
# ---------------------------------------------------------------------------

class TestSetMaintenance:

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        """set_maintenance ritorna True quando execute non solleva."""
        mock_pool = _make_db_pool_mock()

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import set_maintenance
            result = await set_maintenance(status="scheduled", message="Update incoming")

        assert result is True
        mock_pool.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_db_error(self):
        """Eccezione DB → ritorna False senza propagare."""
        mock_pool = _make_db_pool_mock()
        mock_pool.execute = AsyncMock(side_effect=Exception("DB connection lost"))

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import set_maintenance
            result = await set_maintenance(status="active")

        assert result is False

    @pytest.mark.asyncio
    async def test_adds_utc_timezone_to_naive_datetimes(self):
        """Datetime naive → viene arricchito con timezone UTC prima di eseguire."""
        mock_pool = _make_db_pool_mock()
        naive_start = datetime(2025, 1, 1, 3, 0, 0)
        naive_end = datetime(2025, 1, 1, 3, 30, 0)

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import set_maintenance
            await set_maintenance(status="scheduled", start=naive_start, end=naive_end)

        # Recupera args passati a execute
        args = mock_pool.execute.call_args[0]
        # $3 = start, $4 = end (dopo query string)
        passed_start = args[3]
        passed_end = args[4]
        assert passed_start.tzinfo is not None
        assert passed_end.tzinfo is not None

    @pytest.mark.asyncio
    async def test_accepts_none_start_and_end(self):
        """None per start/end è accettato senza errori."""
        mock_pool = _make_db_pool_mock()

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import set_maintenance
            result = await set_maintenance(status="inactive", start=None, end=None)

        assert result is True


# ---------------------------------------------------------------------------
# clear_maintenance
# ---------------------------------------------------------------------------

class TestClearMaintenance:

    @pytest.mark.asyncio
    async def test_sets_status_to_inactive(self):
        """clear_maintenance chiama set_maintenance con status='inactive'."""
        mock_pool = _make_db_pool_mock()

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import clear_maintenance
            result = await clear_maintenance()

        assert result is True
        args = mock_pool.execute.call_args[0]
        # Il primo parametro posizionale dopo la query è lo status
        assert args[1] == "inactive"

    @pytest.mark.asyncio
    async def test_sets_start_and_end_to_none(self):
        """clear_maintenance setta start e end a None."""
        mock_pool = _make_db_pool_mock()

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import clear_maintenance
            await clear_maintenance()

        args = mock_pool.execute.call_args[0]
        assert args[3] is None  # start
        assert args[4] is None  # end

    @pytest.mark.asyncio
    async def test_returns_false_if_underlying_fails(self):
        """Se il DB fallisce, clear_maintenance propaga il False."""
        mock_pool = _make_db_pool_mock()
        mock_pool.execute = AsyncMock(side_effect=Exception("DB error"))

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import clear_maintenance
            result = await clear_maintenance()

        assert result is False


# ---------------------------------------------------------------------------
# get_maintenance_status
# ---------------------------------------------------------------------------

class TestGetMaintenanceStatus:

    @pytest.mark.asyncio
    async def test_returns_dict_when_record_exists(self):
        """Record trovato → dizionario con maintenance_status."""
        fake_row = {
            "id": 1,
            "maintenance_status": "active",
            "maintenance_message": "Update",
            "maintenance_start": datetime(2025, 1, 1, 3, 0, tzinfo=timezone.utc),
            "maintenance_end": datetime(2025, 1, 1, 3, 30, tzinfo=timezone.utc)
        }
        mock_pool = _make_db_pool_mock(fetchrow_return=fake_row)

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result is not None
        assert result["maintenance_status"] == "active"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_record(self):
        """Nessun record → None."""
        mock_pool = _make_db_pool_mock(fetchrow_return=None)

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result is None

    @pytest.mark.asyncio
    async def test_makes_naive_datetimes_utc_aware(self):
        """Datetime naive nel DB → aggiunge timezone UTC."""
        naive_dt = datetime(2025, 6, 1, 12, 0)
        fake_row = {
            "id": 1,
            "maintenance_status": "scheduled",
            "maintenance_message": None,
            "maintenance_start": naive_dt,
            "maintenance_end": naive_dt
        }
        mock_pool = _make_db_pool_mock(fetchrow_return=fake_row)

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result["maintenance_start"].tzinfo is not None
        assert result["maintenance_end"].tzinfo is not None

    @pytest.mark.asyncio
    async def test_returns_none_on_db_error(self):
        """Eccezione DB → ritorna None."""
        mock_pool = _make_db_pool_mock()
        mock_pool.fetchrow = AsyncMock(side_effect=Exception("DB error"))

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import get_maintenance_status
            result = await get_maintenance_status()

        assert result is None


# ---------------------------------------------------------------------------
# is_in_maintenance
# ---------------------------------------------------------------------------

class TestIsInMaintenance:

    @pytest.mark.asyncio
    async def test_returns_true_when_in_maintenance(self):
        """Query ritorna in_maintenance=True → True."""
        mock_pool = _make_db_pool_mock(fetchrow_return={"in_maintenance": True})

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import is_in_maintenance
            result = await is_in_maintenance()

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_in_maintenance(self):
        """Query ritorna in_maintenance=False → False."""
        mock_pool = _make_db_pool_mock(fetchrow_return={"in_maintenance": False})

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import is_in_maintenance
            result = await is_in_maintenance()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_row(self):
        """fetchrow ritorna None → False."""
        mock_pool = _make_db_pool_mock(fetchrow_return=None)

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import is_in_maintenance
            result = await is_in_maintenance()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_db_error(self):
        """Eccezione DB → False (non propaga)."""
        mock_pool = _make_db_pool_mock()
        mock_pool.fetchrow = AsyncMock(side_effect=Exception("DB error"))

        with patch('db.maintenance.db_pool', mock_pool):
            from db.maintenance import is_in_maintenance
            result = await is_in_maintenance()

        assert result is False

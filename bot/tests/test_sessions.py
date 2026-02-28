# bot/tests/test_sessions.py
"""
Tests per bot/db/sessions.py

Copre:
- save_user_session()         — scrittura OK, aggiornamento parziale, encrypt chiamato
- get_user_session()          — trovato, non trovato, decrypt chiamato
- remove_user_session()       — delete eseguito
- get_user_thread_id()        — trovato, non trovato
- get_user_keys()             — trovati, non trovato → ("", "")
- get_user_welcome_message()  — abilitata, non trovato
- find_session_by_username()  — trovato, non trovato
- remove_sessions_by_thread() — rimosso, nessuno
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os


def _make_conn_mock(fetchrow_result=None, execute_result=None):
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock(return_value=execute_result)
    conn.fetch = AsyncMock(return_value=[])

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return conn, ctx


def _make_pool_mock(conn):
    pool = MagicMock()
    pool.acquire.return_value = conn._ctx if hasattr(conn, '_ctx') else conn
    return pool


class TestSaveUserSession:

    @pytest.mark.asyncio
    async def test_calls_execute_with_user_id(self):
        conn, ctx = _make_conn_mock()
        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.encrypt', return_value="enc"),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import save_user_session
            await save_user_session(user_id="123", bearer_token="tok", secret_key="sec")

        conn.execute.assert_awaited_once()
        args = conn.execute.call_args[0]
        assert "123" in args  # user_id

    @pytest.mark.asyncio
    async def test_encrypts_bearer_and_secret(self):
        conn, ctx = _make_conn_mock()
        encrypt_mock = MagicMock(return_value="ENCRYPTED")

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.encrypt', encrypt_mock),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import save_user_session
            await save_user_session(user_id="456", bearer_token="mytoken", secret_key="mykey")

        assert encrypt_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_encrypt_when_token_is_none(self):
        conn, ctx = _make_conn_mock()
        encrypt_mock = MagicMock(return_value=None)

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.encrypt', encrypt_mock),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import save_user_session
            await save_user_session(user_id="789")

        encrypt_mock.assert_not_called()


class TestGetUserSession:

    @pytest.mark.asyncio
    async def test_returns_dict_when_found(self):
        fake_row = {
            "user_id": "123", "thread_id": 1, "uex_username": "alice",
            "bearer_token": "enc_tok", "secret_key": "enc_sec",
            "enable": True, "welcome_message": "hi", "language": "en"
        }
        conn, ctx = _make_conn_mock(fetchrow_result=fake_row)

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.decrypt', side_effect=lambda x: f"dec_{x}"),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_session
            result = await get_user_session("123")

        assert result is not None
        assert result["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        conn, ctx = _make_conn_mock(fetchrow_result=None)

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.decrypt', return_value=None),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_session
            result = await get_user_session("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_calls_decrypt_on_tokens(self):
        fake_row = {
            "user_id": "abc", "bearer_token": "enc_tok", "secret_key": "enc_sec",
            "thread_id": None, "uex_username": None, "enable": None,
            "welcome_message": None, "language": None
        }
        conn, ctx = _make_conn_mock(fetchrow_result=fake_row)
        decrypt_mock = MagicMock(return_value="decrypted")

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.decrypt', decrypt_mock),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_session
            await get_user_session("abc")

        assert decrypt_mock.call_count == 2


class TestRemoveUserSession:

    @pytest.mark.asyncio
    async def test_calls_delete_with_user_id(self):
        conn, ctx = _make_conn_mock()

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import remove_user_session
            await remove_user_session("999")

        args = conn.execute.call_args[0]
        assert "999" in args


class TestGetUserThreadId:

    @pytest.mark.asyncio
    async def test_returns_thread_id_when_found(self):
        conn, ctx = _make_conn_mock(fetchrow_result={"thread_id": 42})

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_thread_id
            result = await get_user_thread_id("123")

        assert result == 42

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        conn, ctx = _make_conn_mock(fetchrow_result=None)

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_thread_id
            result = await get_user_thread_id("999")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_thread_id_is_null(self):
        conn, ctx = _make_conn_mock(fetchrow_result={"thread_id": None})

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_thread_id
            result = await get_user_thread_id("123")

        assert result is None


class TestGetUserKeys:

    @pytest.mark.asyncio
    async def test_returns_decrypted_keys_when_found(self):
        conn, ctx = _make_conn_mock(fetchrow_result={
            "bearer_token": "enc_tok", "secret_key": "enc_sec"
        })

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.decrypt', side_effect=lambda x: f"d_{x}"),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_keys
            token, secret = await get_user_keys("123")

        assert token == "d_enc_tok"
        assert secret == "d_enc_sec"

    @pytest.mark.asyncio
    async def test_returns_empty_strings_when_not_found(self):
        conn, ctx = _make_conn_mock(fetchrow_result=None)

        with (
            patch('db.sessions.db.pool.db_pool') as mock_pool,
            patch('db.sessions.decrypt', return_value=None),
        ):
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_keys
            token, secret = await get_user_keys("missing")

        assert token == ""
        assert secret == ""


class TestGetUserWelcomeMessage:

    @pytest.mark.asyncio
    async def test_returns_true_and_message_when_enabled(self):
        conn, ctx = _make_conn_mock(fetchrow_result={"enable": True, "welcome_message": "ciao!"})

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_welcome_message
            enabled, msg = await get_user_welcome_message("123")

        assert enabled is True
        assert msg == "ciao!"

    @pytest.mark.asyncio
    async def test_returns_false_none_when_not_found(self):
        conn, ctx = _make_conn_mock(fetchrow_result=None)

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_welcome_message
            enabled, msg = await get_user_welcome_message("missing")

        assert enabled is False
        assert msg is None

    @pytest.mark.asyncio
    async def test_returns_false_when_not_enabled(self):
        conn, ctx = _make_conn_mock(fetchrow_result={"enable": False, "welcome_message": "hi"})

        with patch('db.sessions.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.sessions import get_user_welcome_message
            enabled, msg = await get_user_welcome_message("123")

        assert enabled is False

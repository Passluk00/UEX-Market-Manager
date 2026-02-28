# bot/tests/test_uex_api.py
"""
Tests per bot/services/uex_api.py

Copre:
- fetch_and_store_uex_username() — successo con username, API 401, username mancante, eccezione rete
- send_uex_message()             — successo 200, errore 500, eccezione rete, payload corretto
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_http_mock(status=200, json_data=None, text=""):
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data or {})
    mock_response.text = AsyncMock(return_value=text)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_response)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestFetchAndStoreUexUsername:

    @pytest.mark.asyncio
    async def test_returns_username_on_200(self):
        """API restituisce 200 con username → ritorna lo username."""
        resp_ctx = _make_http_mock(200, {"data": {"username": "alice_uex"}})
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=resp_ctx)

        with patch('services.uex_api.save_user_session', new_callable=AsyncMock):
            from services.uex_api import fetch_and_store_uex_username
            result = await fetch_and_store_uex_username(
                user_id="123", secret_key="s", bearer_token="b",
                username_guess="alice", session=mock_session
            )

        assert result == "alice_uex"

    @pytest.mark.asyncio
    async def test_returns_none_on_401(self):
        """API restituisce 401 → None."""
        resp_ctx = _make_http_mock(401)
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=resp_ctx)

        with patch('services.uex_api.save_user_session', new_callable=AsyncMock):
            from services.uex_api import fetch_and_store_uex_username
            result = await fetch_and_store_uex_username(
                user_id="999", secret_key="s", bearer_token="b",
                username_guess="ghost", session=mock_session
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_username_missing_in_response(self):
        """API 200 ma username non nel payload → None."""
        resp_ctx = _make_http_mock(200, {"data": {}})
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=resp_ctx)

        with patch('services.uex_api.save_user_session', new_callable=AsyncMock):
            from services.uex_api import fetch_and_store_uex_username
            result = await fetch_and_store_uex_username(
                user_id="123", secret_key="s", bearer_token="b",
                username_guess="alice", session=mock_session
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_exception(self):
        """Eccezione di rete → None."""
        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("connection error"))

        with patch('services.uex_api.save_user_session', new_callable=AsyncMock):
            from services.uex_api import fetch_and_store_uex_username
            result = await fetch_and_store_uex_username(
                user_id="123", secret_key="s", bearer_token="b",
                username_guess="alice", session=mock_session
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_saves_username_to_db_on_success(self):
        """Dopo il fetch con successo, chiama save_user_session."""
        resp_ctx = _make_http_mock(200, {"data": {"username": "alice_uex"}})
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=resp_ctx)

        save_mock = AsyncMock()
        with patch('services.uex_api.save_user_session', save_mock):
            from services.uex_api import fetch_and_store_uex_username
            await fetch_and_store_uex_username(
                user_id="123", secret_key="s", bearer_token="b",
                username_guess="alice", session=mock_session
            )

        save_mock.assert_awaited_once()


class TestSendUexMessage:

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self):
        """Status 200 → (True, '')."""
        resp_ctx = _make_http_mock(200)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp_ctx)

        from services.uex_api import send_uex_message
        ok, err = await send_uex_message(
            session=mock_session, bearer_token="b", secret_key="s",
            notif_hash="hash123", message="ciao"
        )

        assert ok is True
        assert err == ""

    @pytest.mark.asyncio
    async def test_returns_false_on_500(self):
        """Status 500 → (False, '<status>: <text>')."""
        resp_ctx = _make_http_mock(500, text="Internal Server Error")
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp_ctx)

        from services.uex_api import send_uex_message
        ok, err = await send_uex_message(
            session=mock_session, bearer_token="b", secret_key="s",
            notif_hash="hash123", message="hi"
        )

        assert ok is False
        assert "500" in err

    @pytest.mark.asyncio
    async def test_returns_false_on_network_exception(self):
        """Eccezione di rete → (False, <str eccezione>)."""
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=Exception("timeout"))

        from services.uex_api import send_uex_message
        ok, err = await send_uex_message(
            session=mock_session, bearer_token="b", secret_key="s",
            notif_hash="hash123", message="hi"
        )

        assert ok is False
        assert "timeout" in err

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self):
        """Il payload inviato contiene hash e message."""
        resp_ctx = _make_http_mock(200)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp_ctx)

        from services.uex_api import send_uex_message
        await send_uex_message(
            session=mock_session, bearer_token="b", secret_key="s",
            notif_hash="myHash", message="my message"
        )

        call_kwargs = mock_session.post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert payload.get("hash") == "myHash"
        assert payload.get("message") == "my message"

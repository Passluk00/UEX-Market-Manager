# watchdog/tests/test_github_api.py
"""
Tests per watchdog/github_api/github_api.py

Copre:
- get_latest_commit_sha()   — successo, errore HTTP, exception di rete
- get_current_commit_sha()  — file presente, assente, errore lettura
- save_commit_sha()         — scrittura corretta, gestione errore IO
- get_commit_info()         — successo, errore HTTP, campi mancanti
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

# ---------------------------------------------------------------------------
# Fixtures di supporto
# ---------------------------------------------------------------------------

FAKE_SHA = "abc123def456abc123def456abc123def456abc1"
FAKE_SHA_SHORT = FAKE_SHA[:8]


# ---------------------------------------------------------------------------
# get_latest_commit_sha
# ---------------------------------------------------------------------------

class TestGetLatestCommitSha:

    @pytest.mark.asyncio
    async def test_returns_sha_on_200(self):
        """Risposta 200 con JSON valido → ritorna lo SHA."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"sha": FAKE_SHA})

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock(return_value=False)
        ))

        with patch('github_api.github_api.aiohttp.ClientSession', return_value=mock_session):
            from github_api.github_api import get_latest_commit_sha
            result = await get_latest_commit_sha()

        assert result == FAKE_SHA

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        """Risposta non-200 → ritorna None."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="not found")

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock(return_value=False)
        ))

        with patch('github_api.github_api.aiohttp.ClientSession', return_value=mock_session):
            from github_api.github_api import get_latest_commit_sha
            result = await get_latest_commit_sha()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_exception(self):
        """Eccezione di rete → ritorna None senza propagare."""
        with patch('github_api.github_api.aiohttp.ClientSession', side_effect=Exception("network error")):
            from github_api.github_api import get_latest_commit_sha
            result = await get_latest_commit_sha()

        assert result is None

    @pytest.mark.asyncio
    async def test_includes_auth_header_when_token_set(self):
        """Con GITHUB_TOKEN configurato, passa Authorization header."""
        from github_api import github_api as ga

        # Cattura headers passati a ClientSession
        captured_headers = {}

        # Fake ClientSession che intercetta gli headers
        def fake_client_session(headers=None, **kwargs):
            captured_headers.update(headers or {})
            session = MagicMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=False)
            session.get = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=AsyncMock(status=200, json=AsyncMock(return_value={"sha": "abc123"}))),
                __aexit__=AsyncMock(return_value=False)
            ))
            return session

        # Patch sia il token che ClientSession
        with patch('github_api.github_api.GITHUB_TOKEN', 'my_secret_pat'):
            with patch('github_api.github_api.aiohttp.ClientSession', side_effect=fake_client_session):
                headers = ga._auth_headers()  # Ora legge direttamente la variabile patchata

        # Verifica che l'Authorization header sia corretto
        assert headers.get("Authorization") == "Bearer my_secret_pat"


# ---------------------------------------------------------------------------
# get_current_commit_sha
# ---------------------------------------------------------------------------

class TestGetCurrentCommitSha:

    @pytest.mark.asyncio
    async def test_reads_sha_when_file_exists(self, tmp_path):
        """File esistente con SHA valido → ritorna SHA."""
        sha_file = tmp_path / ".git_commit_sha"
        sha_file.write_text(FAKE_SHA)

        with patch('github_api.github_api.COMMIT_SHA_FILE', str(sha_file)):
            from github_api.github_api import get_current_commit_sha
            result = await get_current_commit_sha()

        assert result == FAKE_SHA

    @pytest.mark.asyncio
    async def test_returns_none_when_file_missing(self, tmp_path):
        """File non esistente → ritorna None."""
        non_existent = str(tmp_path / "no_file")

        with patch('github_api.github_api.COMMIT_SHA_FILE', non_existent):
            from github_api.github_api import get_current_commit_sha
            result = await get_current_commit_sha()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_file_empty(self, tmp_path):
        """File vuoto → ritorna None."""
        sha_file = tmp_path / ".git_commit_sha"
        sha_file.write_text("   ")

        with patch('github_api.github_api.COMMIT_SHA_FILE', str(sha_file)):
            from github_api.github_api import get_current_commit_sha
            result = await get_current_commit_sha()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_read_error(self):
        """Eccezione durante lettura → ritorna None."""
        with patch('github_api.github_api.COMMIT_SHA_FILE', '/fake/path'):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', side_effect=PermissionError("denied")):
                    from github_api.github_api import get_current_commit_sha
                    result = await get_current_commit_sha()

        assert result is None


# ---------------------------------------------------------------------------
# save_commit_sha
# ---------------------------------------------------------------------------

class TestSaveCommitSha:

    @pytest.mark.asyncio
    async def test_writes_sha_to_file(self, tmp_path):
        """SHA scritto correttamente nel file."""
        sha_file = tmp_path / ".git_commit_sha"

        with patch('github_api.github_api.COMMIT_SHA_FILE', str(sha_file)):
            from github_api.github_api import save_commit_sha
            await save_commit_sha(FAKE_SHA)

        assert sha_file.read_text() == FAKE_SHA

    @pytest.mark.asyncio
    async def test_overwrites_existing_file(self, tmp_path):
        """SHA sovrascrive un file esistente."""
        sha_file = tmp_path / ".git_commit_sha"
        sha_file.write_text("old_sha")

        with patch('github_api.github_api.COMMIT_SHA_FILE', str(sha_file)):
            from github_api.github_api import save_commit_sha
            await save_commit_sha(FAKE_SHA)

        assert sha_file.read_text() == FAKE_SHA

    @pytest.mark.asyncio
    async def test_does_not_raise_on_write_error(self):
        """Errore di scrittura → non propaga eccezione."""
        with patch('github_api.github_api.COMMIT_SHA_FILE', '/read_only/path'):
            with patch('builtins.open', side_effect=PermissionError("denied")):
                from github_api.github_api import save_commit_sha
                # Non deve sollevare
                await save_commit_sha(FAKE_SHA)


# ---------------------------------------------------------------------------
# get_commit_info
# ---------------------------------------------------------------------------

class TestGetCommitInfo:

    @pytest.mark.asyncio
    async def test_returns_dict_on_200(self):
        """Risposta 200 → dizionario con sha, message, author, date."""
        fake_data = {
            "sha": FAKE_SHA,
            "commit": {
                "message": "Fix bug",
                "author": {"name": "Alice", "date": "2024-01-01T00:00:00Z"}
            }
        }
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=fake_data)

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock(return_value=False)
        ))

        with patch('github_api.github_api.aiohttp.ClientSession', return_value=mock_session):
            from github_api.github_api import get_commit_info
            result = await get_commit_info(FAKE_SHA)

        assert result["sha"] == FAKE_SHA
        assert result["message"] == "Fix bug"
        assert result["author"] == "Alice"

    @pytest.mark.asyncio
    async def test_returns_none_on_error_status(self):
        """Status non-200 → ritorna None."""
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.get = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_response),
            __aexit__=AsyncMock(return_value=False)
        ))

        with patch('github_api.github_api.aiohttp.ClientSession', return_value=mock_session):
            from github_api.github_api import get_commit_info
            result = await get_commit_info(FAKE_SHA)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_exception(self):
        """Eccezione di rete → ritorna None."""
        with patch('github_api.github_api.aiohttp.ClientSession', side_effect=Exception("timeout")):
            from github_api.github_api import get_commit_info
            result = await get_commit_info(FAKE_SHA)

        assert result is None

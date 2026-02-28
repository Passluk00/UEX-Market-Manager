# watchdog/tests/test_notifications.py
"""
Tests per watchdog/notification/notifications.py

Copre:
- send_discord_webhook()       — successo 204, errore HTTP, no URL, eccezione
- notify_update_success()      — chiamata con SHA corretti
- notify_update_failure()      — chiamata con errore e SHA
- notify_monitoring()          — colori corretti per ogni livello
- notify_update_started()      — campi embed corretti
- notify_container_restart()   — campi embed corretti
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


WEBHOOK_URL = "https://discord.com/api/webhooks/test/token"


def _make_session_mock(status=204):
    """Crea un mock aiohttp.ClientSession che risponde con lo status dato."""
    mock_response = MagicMock()
    mock_response.status = status

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post = MagicMock(return_value=mock_context)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


class TestSendDiscordWebhook:

    @pytest.mark.asyncio
    async def test_sends_embed_on_204(self):
        """Status 204 = successo → la chiamata viene effettuata."""
        mock_session = _make_session_mock(204)

        with patch('notification.notifications.aiohttp.ClientSession', return_value=mock_session):
            from notification.notifications import send_discord_webhook
            await send_discord_webhook(WEBHOOK_URL, {"title": "Test"})

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_error_on_non_204(self):
        """Status non-204 → non propaga eccezione ma logga l'errore."""
        mock_session = _make_session_mock(400)

        with patch('notification.notifications.aiohttp.ClientSession', return_value=mock_session):
            from notification.notifications import send_discord_webhook
            # Non deve sollevare
            await send_discord_webhook(WEBHOOK_URL, {"title": "Test"})

    @pytest.mark.asyncio
    async def test_skips_when_no_url(self):
        """URL vuota → non chiama il webhook."""
        with patch('notification.notifications.aiohttp.ClientSession') as mock_cls:
            from notification.notifications import send_discord_webhook
            await send_discord_webhook("", {"title": "Test"})

        mock_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_raise_on_exception(self):
        """Eccezione di rete → non propaga."""
        with patch('notification.notifications.aiohttp.ClientSession', side_effect=Exception("network")):
            from notification.notifications import send_discord_webhook
            await send_discord_webhook(WEBHOOK_URL, {"title": "Test"})


class TestNotifyUpdateSuccess:

    @pytest.mark.asyncio
    async def test_sends_webhook_with_shas(self):
        """Verifica che i due SHA vengano inclusi nell'embed."""
        sent_payload = {}

        async def fake_send(url, embed):
            sent_payload.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_update_success
            await notify_update_success("oldshaX", "newshaX")

        assert "oldshaX" in str(sent_payload)
        assert "newshaX" in str(sent_payload)

    @pytest.mark.asyncio
    async def test_uses_green_color(self):
        """La notifica di successo usa il colore verde (0x00FF00)."""
        sent_payload = {}

        async def fake_send(url, embed):
            sent_payload.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_update_success
            await notify_update_success("a" * 8, "b" * 8)

        assert sent_payload.get("color") == 0x00FF00

    @pytest.mark.asyncio
    async def test_sends_to_monitoring_webhook(self):
        """Chiama send_discord_webhook con WEBHOOK_MONITORING."""
        captured_url = []

        async def fake_send(url, embed):
            captured_url.append(url)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            with patch('notification.notifications.WEBHOOK_MONITORING', WEBHOOK_URL):
                from notification.notifications import notify_update_success
                await notify_update_success("aaa", "bbb")

        assert captured_url[0] == WEBHOOK_URL


class TestNotifyUpdateFailure:

    @pytest.mark.asyncio
    async def test_sends_red_embed_with_error(self):
        """Notifica fallimento: rosso, contiene l'errore."""
        sent_payload = {}

        async def fake_send(url, embed):
            sent_payload.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_update_failure
            await notify_update_failure("Container crashed", "abc12345")

        assert sent_payload.get("color") == 0xFF0000
        assert "Container crashed" in str(sent_payload)

    @pytest.mark.asyncio
    async def test_includes_rolled_back_sha(self):
        """L'embed include lo SHA a cui è stato fatto rollback."""
        sent_payload = {}

        async def fake_send(url, embed):
            sent_payload.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_update_failure
            await notify_update_failure("git pull error", "deadbeef")

        assert "deadbeef" in str(sent_payload)

    @pytest.mark.asyncio
    async def test_does_not_raise_on_send_error(self):
        """Se il webhook fallisce, la funzione non propaga."""
        with patch('notification.notifications.send_discord_webhook', side_effect=Exception("net")):
            from notification.notifications import notify_update_failure
            await notify_update_failure("error", "sha")


class TestNotifyMonitoring:

    @pytest.mark.asyncio
    async def test_info_level_uses_blue(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_monitoring
            await notify_monitoring("info message", "info")

        assert sent.get("color") == 0x0099FF

    @pytest.mark.asyncio
    async def test_error_level_uses_red(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_monitoring
            await notify_monitoring("error message", "error")

        assert sent.get("color") == 0xFF0000

    @pytest.mark.asyncio
    async def test_success_level_uses_green(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_monitoring
            await notify_monitoring("ok", "success")

        assert sent.get("color") == 0x00FF00

    @pytest.mark.asyncio
    async def test_unknown_level_defaults_to_blue(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_monitoring
            await notify_monitoring("msg", "unknown_level")

        assert sent.get("color") == 0x0099FF


class TestNotifyUpdateStarted:

    @pytest.mark.asyncio
    async def test_embed_contains_both_shas_and_minutes(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_update_started
            await notify_update_started("oldsha1", "newsha1", 30)

        payload_str = str(sent)
        assert "oldsha1" in payload_str
        assert "newsha1" in payload_str
        assert "30" in payload_str

    @pytest.mark.asyncio
    async def test_uses_orange_warning_color(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_update_started
            await notify_update_started("a", "b", 5)

        assert sent.get("color") == 0xFFAA00


class TestNotifyContainerRestart:

    @pytest.mark.asyncio
    async def test_embed_contains_container_name(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_container_restart
            await notify_container_restart("python", "health check failed")

        assert "python" in str(sent)

    @pytest.mark.asyncio
    async def test_embed_contains_reason(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_container_restart
            await notify_container_restart("python", "OOM killed")

        assert "OOM killed" in str(sent)

    @pytest.mark.asyncio
    async def test_uses_orange_color(self):
        sent = {}

        async def fake_send(url, embed): sent.update(embed)

        with patch('notification.notifications.send_discord_webhook', side_effect=fake_send):
            from notification.notifications import notify_container_restart
            await notify_container_restart("python")

        assert sent.get("color") == 0xFFAA00

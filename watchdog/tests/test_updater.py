# watchdog/tests/test_updater.py
"""
Tests per watchdog/updater/updater.py

Copre:
- pull_latest_code()        — successo, returncode != 0, timeout, git non trovato
- rollback_to_commit()      — successo, returncode != 0, eccezione
- verify_container_health() — sano al primo tentativo, sano dopo N, mai sano
- perform_update()          — flusso completo successo, fallimento git pull,
                              container unhealthy con rollback, maintenance scheduling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import subprocess


FAKE_OLD_SHA = "aaaaaaaabbbbbbbbcccccccc"
FAKE_NEW_SHA = "ddddddddeeeeeeeeffffffff"


# ---------------------------------------------------------------------------
# pull_latest_code
# ---------------------------------------------------------------------------

class TestPullLatestCode:

    @pytest.mark.asyncio
    async def test_returns_true_on_exit_code_0(self):
        """returncode 0 → True."""
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = "Already up to date."
        fake_result.stderr = ""

        with patch('updater.updater.subprocess.run', return_value=fake_result):
            from updater.updater import pull_latest_code
            result = await pull_latest_code()

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_nonzero_exit(self):
        """returncode != 0 → False."""
        fake_result = MagicMock()
        fake_result.returncode = 1
        fake_result.stdout = ""
        fake_result.stderr = "error: could not pull"

        with patch('updater.updater.subprocess.run', return_value=fake_result):
            from updater.updater import pull_latest_code
            result = await pull_latest_code()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self):
        """subprocess.TimeoutExpired → False."""
        with patch('updater.updater.subprocess.run', side_effect=subprocess.TimeoutExpired("git", 120)):
            from updater.updater import pull_latest_code
            result = await pull_latest_code()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_git_not_found(self):
        """FileNotFoundError (git non installato) → False."""
        with patch('updater.updater.subprocess.run', side_effect=FileNotFoundError("git not found")):
            from updater.updater import pull_latest_code
            result = await pull_latest_code()

        assert result is False


# ---------------------------------------------------------------------------
# rollback_to_commit
# ---------------------------------------------------------------------------

class TestRollbackToCommit:

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = f"HEAD is now at {FAKE_OLD_SHA[:7]}"
        fake_result.stderr = ""

        with patch('updater.updater.subprocess.run', return_value=fake_result):
            from updater.updater import rollback_to_commit
            result = await rollback_to_commit(FAKE_OLD_SHA)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_nonzero_exit(self):
        fake_result = MagicMock()
        fake_result.returncode = 128
        fake_result.stdout = ""
        fake_result.stderr = "fatal: unknown revision"

        with patch('updater.updater.subprocess.run', return_value=fake_result):
            from updater.updater import rollback_to_commit
            result = await rollback_to_commit("invalid_sha")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        with patch('updater.updater.subprocess.run', side_effect=Exception("unexpected")):
            from updater.updater import rollback_to_commit
            result = await rollback_to_commit(FAKE_OLD_SHA)

        assert result is False


# ---------------------------------------------------------------------------
# verify_container_health
# ---------------------------------------------------------------------------

class TestVerifyContainerHealth:

    @pytest.mark.asyncio
    async def test_returns_true_on_first_check(self):
        """Container sano subito → True al primo tentativo."""
        dm = MagicMock()
        dm.is_container_healthy.return_value = True

        from updater.updater import verify_container_health
        result = await verify_container_health(dm, max_checks=3)

        assert result is True
        assert dm.is_container_healthy.call_count == 1

    @pytest.mark.asyncio
    async def test_returns_true_after_retries(self):
        """Container sano al 3° check → True, 3 chiamate."""
        dm = MagicMock()
        dm.is_container_healthy.side_effect = [False, False, True]

        with patch('updater.updater.asyncio.sleep', new_callable=AsyncMock):
            from updater.updater import verify_container_health
            result = await verify_container_health(dm, max_checks=4)

        assert result is True
        assert dm.is_container_healthy.call_count == 3

    @pytest.mark.asyncio
    async def test_returns_false_when_never_healthy(self):
        """Mai sano → False dopo max_checks tentativi."""
        dm = MagicMock()
        dm.is_container_healthy.return_value = False

        with patch('updater.updater.asyncio.sleep', new_callable=AsyncMock):
            from updater.updater import verify_container_health
            result = await verify_container_health(dm, max_checks=3)

        assert result is False
        assert dm.is_container_healthy.call_count == 3


# ---------------------------------------------------------------------------
# perform_update — flusso principale
# ---------------------------------------------------------------------------

class TestPerformUpdate:

    def _build_mocks(
        self,
        pull_ok=True,
        start_ok=True,
        container_healthy=True,
        set_maintenance_ok=True,
    ):
        """Prepara tutti i mock per perform_update."""
        docker_patch = patch('updater.updater.DockerManager')
        pull_patch = patch('updater.updater.pull_latest_code', new_callable=AsyncMock)
        health_patch = patch('updater.updater.verify_container_health', new_callable=AsyncMock)
        set_maint_patch = patch('updater.updater.set_maintenance', new_callable=AsyncMock)
        clear_maint_patch = patch('updater.updater.clear_maintenance', new_callable=AsyncMock)
        save_sha_patch = patch('updater.updater.save_commit_sha', new_callable=AsyncMock)
        notify_started_patch = patch('updater.updater.notify_update_started', new_callable=AsyncMock)
        notify_success_patch = patch('updater.updater.notify_update_success', new_callable=AsyncMock)
        notify_failure_patch = patch('updater.updater.notify_update_failure', new_callable=AsyncMock)
        sleep_patch = patch('updater.updater.asyncio.sleep', new_callable=AsyncMock)

        return (
            docker_patch, pull_patch, health_patch,
            set_maint_patch, clear_maint_patch, save_sha_patch,
            notify_started_patch, notify_success_patch, notify_failure_patch,
            sleep_patch,
        ), dict(
            pull_ok=pull_ok,
            start_ok=start_ok,
            container_healthy=container_healthy,
            set_maintenance_ok=set_maintenance_ok,
        )

    @pytest.mark.asyncio
    async def test_full_success_flow(self):
        """Flusso completo: pull OK, container healthy → True, SHA salvato."""
        dm = MagicMock()
        dm.stop_container.return_value = True
        dm.start_container.return_value = True
        dm.get_container_logs.return_value = ""

        save_sha = AsyncMock()
        clear_maint = AsyncMock()
        notify_success = AsyncMock()

        with (
            patch('updater.updater.DockerManager', return_value=dm),
            patch('updater.updater.pull_latest_code', new_callable=AsyncMock, return_value=True),
            patch('updater.updater.verify_container_health', new_callable=AsyncMock, return_value=True),
            patch('updater.updater.set_maintenance', new_callable=AsyncMock, return_value=True),
            patch('updater.updater.clear_maintenance', clear_maint),
            patch('updater.updater.save_commit_sha', save_sha),
            patch('updater.updater.notify_update_started', new_callable=AsyncMock),
            patch('updater.updater.notify_update_success', notify_success),
            patch('updater.updater.notify_update_failure', new_callable=AsyncMock),
            patch('updater.updater.asyncio.sleep', new_callable=AsyncMock),
        ):
            from updater.updater import perform_update
            result = await perform_update(FAKE_OLD_SHA, FAKE_NEW_SHA)

        assert result is True
        save_sha.assert_awaited_once_with(FAKE_NEW_SHA)
        notify_success.assert_awaited_once()
        clear_maint.assert_awaited()

    @pytest.mark.asyncio
    async def test_returns_false_when_git_pull_fails(self):
        """git pull fallisce → rollback avviato, ritorna False."""
        dm = MagicMock()
        dm.stop_container.return_value = True
        dm.start_container.return_value = True

        notify_failure = AsyncMock()

        with (
            patch('updater.updater.DockerManager', return_value=dm),
            patch('updater.updater.pull_latest_code', new_callable=AsyncMock, return_value=False),
            patch('updater.updater.set_maintenance', new_callable=AsyncMock, return_value=True),
            patch('updater.updater.clear_maintenance', new_callable=AsyncMock),
            patch('updater.updater.save_commit_sha', new_callable=AsyncMock),
            patch('updater.updater.notify_update_started', new_callable=AsyncMock),
            patch('updater.updater.notify_update_success', new_callable=AsyncMock),
            patch('updater.updater.notify_update_failure', notify_failure),
            patch('updater.updater.asyncio.sleep', new_callable=AsyncMock),
        ):
            from updater.updater import perform_update
            result = await perform_update(FAKE_OLD_SHA, FAKE_NEW_SHA)

        assert result is False
        notify_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rollback_when_container_unhealthy(self):
        """Container non sano dopo update → rollback e False."""
        dm = MagicMock()
        dm.stop_container.return_value = True
        dm.start_container.return_value = True
        dm.get_container_logs.return_value = "error in bot"

        rollback = AsyncMock(return_value=True)
        notify_failure = AsyncMock()

        with (
            patch('updater.updater.DockerManager', return_value=dm),
            patch('updater.updater.pull_latest_code', new_callable=AsyncMock, return_value=True),
            patch('updater.updater.verify_container_health', new_callable=AsyncMock, return_value=False),
            patch('updater.updater.rollback_to_commit', rollback),
            patch('updater.updater.set_maintenance', new_callable=AsyncMock, return_value=True),
            patch('updater.updater.clear_maintenance', new_callable=AsyncMock),
            patch('updater.updater.save_commit_sha', new_callable=AsyncMock),
            patch('updater.updater.notify_update_started', new_callable=AsyncMock),
            patch('updater.updater.notify_update_success', new_callable=AsyncMock),
            patch('updater.updater.notify_update_failure', notify_failure),
            patch('updater.updater.asyncio.sleep', new_callable=AsyncMock),
        ):
            from updater.updater import perform_update
            result = await perform_update(FAKE_OLD_SHA, FAKE_NEW_SHA)

        assert result is False
        rollback.assert_awaited_once_with(FAKE_OLD_SHA)
        notify_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_schedules_maintenance_before_stopping_container(self):
        """La manutenzione viene schedulata prima di fermare il container."""
        dm = MagicMock()
        dm.stop_container.return_value = False  # Fermato subito per brevità

        set_maint = AsyncMock(return_value=True)

        with (
            patch('updater.updater.DockerManager', return_value=dm),
            patch('updater.updater.pull_latest_code', new_callable=AsyncMock, return_value=False),
            patch('updater.updater.set_maintenance', set_maint),
            patch('updater.updater.clear_maintenance', new_callable=AsyncMock),
            patch('updater.updater.save_commit_sha', new_callable=AsyncMock),
            patch('updater.updater.notify_update_started', new_callable=AsyncMock),
            patch('updater.updater.notify_update_success', new_callable=AsyncMock),
            patch('updater.updater.notify_update_failure', new_callable=AsyncMock),
            patch('updater.updater.asyncio.sleep', new_callable=AsyncMock),
        ):
            from updater.updater import perform_update
            await perform_update(FAKE_OLD_SHA, FAKE_NEW_SHA)

        # set_maintenance deve essere chiamata con status="scheduled" come prima cosa
        first_call_args = set_maint.call_args_list[0]
        assert first_call_args.kwargs.get("status") == "scheduled"

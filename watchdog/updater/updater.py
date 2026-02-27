import asyncio
import logging
import subprocess
from datetime import datetime, timedelta, timezone

from config import GITHUB_BRANCH, MAINTENANCE_NOTICE_MINUTES, GIT_REPO_PATH
from docker_manager.docker_Manager import DockerManager
from github_api import get_latest_commit_sha, get_current_commit_sha, save_commit_sha
from db import set_maintenance, clear_maintenance
from notification import (
    notify_update_success,
    notify_update_failure,
    notify_monitoring,
    notify_update_started,
)


# ============================================================================
# GIT OPERATIONS (run on the host volume via subprocess)
# ============================================================================

async def pull_latest_code() -> bool:
    """
    Esegue 'git pull' sul repository montato nel container watchdog.

    Il repo root è accessibile a GIT_REPO_PATH (default /repo) grazie al
    volume  ./:/repo  definito nel docker-compose.yml.
    Non usa container.exec_run perché il bot è già fermo in questo momento.

    Returns:
        True se il pull è riuscito, False altrimenti.
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ['git', 'pull', 'origin', GITHUB_BRANCH],
                cwd=GIT_REPO_PATH,
                capture_output=True,
                text=True,
                timeout=120,
            )
        )
        logging.info(f"Git pull stdout: {result.stdout.strip()}")
        if result.returncode != 0:
            logging.error(f"Git pull stderr: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logging.error("Git pull timed out after 120 seconds")
        return False
    except FileNotFoundError:
        logging.error("git executable not found — ensure git is installed in the watchdog image")
        return False
    except Exception as e:
        logging.error(f"Failed to pull latest code: {e}")
        return False


async def rollback_to_commit(sha: str) -> bool:
    """
    Esegue 'git reset --hard <sha>' sul repository montato.

    Args:
        sha: SHA del commit a cui fare rollback.

    Returns:
        True se successo, False altrimenti.
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ['git', 'reset', '--hard', sha],
                cwd=GIT_REPO_PATH,
                capture_output=True,
                text=True,
                timeout=60,
            )
        )
        logging.info(f"Git reset stdout: {result.stdout.strip()}")
        if result.returncode != 0:
            logging.error(f"Git reset stderr: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Failed to rollback to {sha}: {e}")
        return False


# ============================================================================
# HEALTH VERIFICATION
# ============================================================================

async def verify_container_health(docker_mgr: DockerManager, max_checks: int = 6) -> bool:
    """
    Verifica che il container sia healthy dopo l'aggiornamento.

    Args:
        docker_mgr: Istanza del DockerManager.
        max_checks: Numero massimo di tentativi (default: 6 → 1 minuto).

    Returns:
        True se il container è healthy, False altrimenti.
    """
    for i in range(max_checks):
        if docker_mgr.is_container_healthy():
            logging.info(f"Container is healthy (check {i + 1}/{max_checks})")
            return True
        logging.debug(f"Container health check {i + 1}/{max_checks} failed, waiting 10s…")
        await asyncio.sleep(10)

    logging.error(f"Container failed health check after {max_checks} attempts")
    return False


# ============================================================================
# MAIN UPDATE PROCEDURE
# ============================================================================

async def perform_update(current_sha: str | None, latest_sha: str) -> bool:
    """
    Esegue l'aggiornamento completo del sistema:

    1. Segnala manutenzione programmata (DB + Discord)
    2. Aspetta il preavviso
    3. Ferma container
    4. git pull sul volume montato
    5. Avvia container
    6. Verifica salute (max 6 tentativi × 10s = 1 min)
    7. Successo → salva SHA, pulisce manutenzione, notifica Discord
    8. Fallimento → rollback git, riavvia container, notifica Discord

    Args:
        current_sha: SHA del commit attualmente in produzione (può essere None).
        latest_sha: SHA del commit da installare.

    Returns:
        True se l'aggiornamento ha avuto successo, False altrimenti.
    """
    logging.info("=" * 80)
    logging.info("STARTING UPDATE PROCESS")
    logging.info("=" * 80)

    docker_mgr = DockerManager()
    sha_display = current_sha[:8] if current_sha else "unknown"

    # ------------------------------------------------------------------ #
    # 1. Programma manutenzione con preavviso                             #
    # ------------------------------------------------------------------ #
    now = datetime.now(timezone.utc)
    maintenance_start = now + timedelta(minutes=MAINTENANCE_NOTICE_MINUTES)
    maintenance_end = maintenance_start + timedelta(minutes=15)   # stima conservativa

    if not await set_maintenance(
        status="scheduled",
        message="Automatic system update in progress",
        start=maintenance_start,
        end=maintenance_end,
    ):
        logging.error("Failed to schedule maintenance — aborting update")
        return False

    logging.info(f"Maintenance scheduled: {maintenance_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    await notify_update_started(
        current_sha=sha_display,
        latest_sha=latest_sha[:8],
        minutes=MAINTENANCE_NOTICE_MINUTES,
    )

    # ------------------------------------------------------------------ #
    # 2. Attesa preavviso                                                 #
    # ------------------------------------------------------------------ #
    await asyncio.sleep(MAINTENANCE_NOTICE_MINUTES * 60)

    # ------------------------------------------------------------------ #
    # 3. Imposta manutenzione attiva                                      #
    # ------------------------------------------------------------------ #
    await set_maintenance(
        status="active",
        message="Automatic system update in progress",
        start=datetime.now(timezone.utc),
        end=maintenance_end,
    )

    # ------------------------------------------------------------------ #
    # 4. Ferma container                                                  #
    # ------------------------------------------------------------------ #
    logging.info("Stopping bot container…")
    if not docker_mgr.stop_container():
        logging.error("Failed to stop container — aborting update")
        await clear_maintenance()
        await notify_update_failure("Failed to stop bot container before update", sha_display)
        return False

    # ------------------------------------------------------------------ #
    # 5. git pull                                                         #
    # ------------------------------------------------------------------ #
    logging.info("Pulling latest code via git…")
    if not await pull_latest_code():
        logging.error("git pull failed — rolling back and restarting container")
        docker_mgr.start_container()
        await clear_maintenance()
        await notify_update_failure("git pull failed", sha_display)
        return False

    # ------------------------------------------------------------------ #
    # 6. Avvia container                                                  #
    # ------------------------------------------------------------------ #
    logging.info("Starting bot container with new code…")
    if not docker_mgr.start_container():
        logging.error("Failed to start container after pull — attempting rollback")
        # Rollback: git reset before restarting
        if current_sha:
            await rollback_to_commit(current_sha)
        docker_mgr.start_container()
        await clear_maintenance()
        await notify_update_failure("Failed to start container after update", sha_display)
        return False

    # ------------------------------------------------------------------ #
    # 7. Verifica salute container                                        #
    # ------------------------------------------------------------------ #
    await asyncio.sleep(10)  # attesa iniziale per startup

    if await verify_container_health(docker_mgr):
        # SUCCESS
        await save_commit_sha(latest_sha)
        await clear_maintenance()
        await notify_update_success(sha_display, latest_sha[:8])
        logging.info("=" * 80)
        logging.info("UPDATE COMPLETED SUCCESSFULLY")
        logging.info("=" * 80)
        return True

    # ------------------------------------------------------------------ #
    # 8. Rollback se container non è healthy                              #
    # ------------------------------------------------------------------ #
    logging.error("Container unhealthy after update — performing rollback…")
    logs = docker_mgr.get_container_logs()

    # Ferma, ripristina codice, riavvia
    docker_mgr.stop_container()
    if current_sha:
        rollback_ok = await rollback_to_commit(current_sha)
        if not rollback_ok:
            logging.error("Rollback git reset also failed — manual intervention required")
    docker_mgr.start_container()

    await clear_maintenance()
    await notify_update_failure(
        f"Container failed health check after update.\n\nRecent logs:\n```\n{logs[-1500:]}\n```",
        sha_display,
    )

    logging.info("=" * 80)
    logging.info("UPDATE FAILED — ROLLBACK COMPLETED")
    logging.info("=" * 80)
    return False

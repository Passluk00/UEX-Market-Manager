import logging
import asyncio
from datetime import datetime, timedelta
from config import GITHUB_BRANCH, MAINTENANCE_NOTICE_MINUTES
from docker import DockerManager


async def pull_latest_code() -> bool:
    """Esegue git pull nel container"""
    try:
        docker_mgr = DockerManager()
        container = docker_mgr.get_container()
        
        if not container:
            return False
            
        # Esegue git pull
        exec_result = container.exec_run(
            'git pull origin ' + GITHUB_BRANCH,
            workdir='/app'
        )
        
        output = exec_result.output.decode('utf-8')
        logging.info(f"Git pull output: {output}")
        
        return exec_result.exit_code == 0
    except Exception as e:
        logging.error(f"Failed to pull latest code: {e}")
        return False

async def perform_update() -> bool:
    """
    Esegue l'aggiornamento completo del sistema:
    1. Verifica nuovo commit disponibile
    2. Notifica manutenzione
    3. Ferma container
    4. Pull codice
    5. Riavvia container
    6. Verifica successo o rollback
    """
    logging.info("=" * 80)
    logging.info("STARTING UPDATE PROCESS")
    logging.info("=" * 80)
    
    docker_mgr = DockerManager()
    
    # 1. Verifica se c'è un nuovo aggiornamento
    current_sha = await get_current_commit_sha()
    latest_sha = await get_latest_commit_sha()
    
    if not latest_sha:
        logging.error("Cannot fetch latest commit SHA")
        return False
        
    if current_sha == latest_sha:
        logging.info("Already up to date")
        return True
        
    logging.info(f"Update available: {current_sha[:8] if current_sha else 'unknown'} -> {latest_sha[:8]}")
    
    # 2. Programma manutenzione con preavviso
    now = datetime.utcnow()
    maintenance_start = now + timedelta(minutes=MAINTENANCE_NOTICE_MINUTES)
    maintenance_end = maintenance_start + timedelta(minutes=10)  # stima 10 min
    
    if not await set_maintenance(maintenance_start, maintenance_end, "Automatic system update"):
        logging.error("Failed to schedule maintenance")
        return False
        
    logging.info(f"Maintenance scheduled for {maintenance_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    await notify_monitoring(
        f"🔧 Maintenance scheduled in {MAINTENANCE_NOTICE_MINUTES} minutes\n"
        f"Update: `{current_sha[:8] if current_sha else 'unknown'}` → `{latest_sha[:8]}`",
        "warning"
    )
    
    # 3. Aspetta il tempo di preavviso
    await asyncio.sleep(MAINTENANCE_NOTICE_MINUTES * 60)
    
    # 4. Ferma il container
    logging.info("Stopping container...")
    if not docker_mgr.stop_container():
        logging.error("Failed to stop container")
        await clear_maintenance()
        return False
        
    # 5. Pull del nuovo codice
    logging.info("Pulling latest code...")
    if not await pull_latest_code():
        logging.error("Failed to pull code, starting rollback...")
        docker_mgr.start_container()
        await clear_maintenance()
        await notify_update_failure("Failed to pull latest code", current_sha or "unknown")
        return False
        
    # 6. Avvia il container
    logging.info("Starting container with new code...")
    if not docker_mgr.start_container():
        logging.error("Failed to start container, attempting rollback...")
        # Rollback: git reset al commit precedente
        container = docker_mgr.get_container()
        if container and current_sha:
            container.exec_run(f'git reset --hard {current_sha}', workdir='/app')
        docker_mgr.start_container()
        await clear_maintenance()
        await notify_update_failure("Failed to start container after update", current_sha or "unknown")
        return False
        
    # 7. Verifica che il container sia healthy
    await asyncio.sleep(10)  # Attesa per startup
    
    max_checks = 6  # 1 minuto totale
    for i in range(max_checks):
        if docker_mgr.is_container_healthy():
            logging.info("Container is healthy after update")
            await save_commit_sha(latest_sha)
            await clear_maintenance()
            await notify_update_success(current_sha or "unknown", latest_sha)
            logging.info("=" * 80)
            logging.info("UPDATE COMPLETED SUCCESSFULLY")
            logging.info("=" * 80)
            return True
        await asyncio.sleep(10)
        
    # 8. Rollback se il container non è healthy
    logging.error("Container unhealthy after update, performing rollback...")
    logs = docker_mgr.get_container_logs()
    
    docker_mgr.stop_container()
    container = docker_mgr.get_container()
    if container and current_sha:
        container.exec_run(f'git reset --hard {current_sha}', workdir='/app')
    docker_mgr.start_container()
    
    await clear_maintenance()
    await notify_update_failure(
        f"Container failed health check\n\nLogs:\n{logs[-500:]}", 
        current_sha or "unknown"
    )
    
    logging.info("=" * 80)
    logging.info("UPDATE FAILED - ROLLBACK COMPLETED")
    logging.info("=" * 80)
    return False

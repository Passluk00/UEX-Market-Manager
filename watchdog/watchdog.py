import sys
import logging
import signal
import asyncio
from logger_watchdog import setup_logger
from datetime import datetime, time

# Import configurazione
from config import *

# Import database
from db.watchdog_db import db_pool

# Import GitHub API
from github_api import (
    get_latest_commit_sha,
    get_current_commit_sha,
    save_commit_sha
)

# Import Docker manager
from docker_manager import DockerManager

# Import Discord notifications
from notification import (
    notify_update_success,
    notify_update_failure,
    notify_monitoring,
    notify_container_restart
)

# Import update manager
from updater import perform_update


# ============================================================================
# WATCHDOG CLASS
# ============================================================================

class Watchdog:
    """
    Servizio watchdog principale
    
    Responsabilità:
    - Monitoraggio continuo della salute del container bot
    - Scheduling controllo aggiornamenti giornaliero
    - Coordinamento procedura di update automatico
    """
    
    def __init__(self):
        """Inizializza il watchdog"""
        self.docker_mgr = DockerManager()
        self.running = True
        self.last_update_check = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        
        logging.info("Watchdog initialized")
        logging.info(f"Container to monitor: {CONTAINER_NAME}")
        logging.info(f"Health check interval: {CHECK_INTERVAL}s")
        logging.info(f"Update check time: {UPDATE_CHECK_TIME}")
        
    async def check_container_health(self):
        """
        Verifica la salute del container e riavvia se necessario
        
        Implementa un sistema di retry con contatore di fallimenti consecutivi
        per evitare loop infiniti di restart
        """
        try:
            if not self.docker_mgr.is_container_healthy():
                self.consecutive_failures += 1
                
                logging.warning(
                    f"Container '{CONTAINER_NAME}' is not healthy "
                    f"(failure {self.consecutive_failures}/{self.max_consecutive_failures})"
                )
                
                # Notifica Discord
                await notify_monitoring(
                    f"⚠️ Container '{CONTAINER_NAME}' unhealthy, attempting restart...\n"
                    f"Consecutive failures: {self.consecutive_failures}",
                    "warning"
                )
                
                # Tenta restart
                if self.docker_mgr.restart_container():
                    logging.info("Container restarted successfully")
                    await notify_container_restart(CONTAINER_NAME, "health check failed")
                    
                    # Aspetta un po' per dare tempo al container di avviarsi
                    await asyncio.sleep(10)
                    
                    # Verifica se ora è healthy
                    if self.docker_mgr.is_container_healthy():
                        logging.info("Container is now healthy after restart")
                        self.consecutive_failures = 0  # Reset counter
                    else:
                        logging.warning("Container still unhealthy after restart")
                        
                        # Se troppi fallimenti, notifica con urgenza
                        if self.consecutive_failures >= self.max_consecutive_failures:
                            await notify_monitoring(
                                f"🚨 CRITICAL: Container '{CONTAINER_NAME}' "
                                f"failed {self.consecutive_failures} consecutive health checks!\n"
                                f"Manual intervention may be required.",
                                "error"
                            )
                else:
                    logging.error("Failed to restart container")
                    await notify_monitoring(
                        f"❌ Failed to restart container '{CONTAINER_NAME}'",
                        "error"
                    )
            else:
                # Container è healthy, reset del contatore
                if self.consecutive_failures > 0:
                    logging.info("Container recovered, resetting failure counter")
                    self.consecutive_failures = 0
                    
        except Exception as e:
            logging.error(f"Error during health check: {e}", exc_info=True)
            await notify_monitoring(f"❌ Health check error: {str(e)}", "error")
                
    async def should_check_updates(self) -> bool:
        """
        Determina se è il momento di controllare gli aggiornamenti
        
        Controlla se l'ora corrente è vicina all'ora configurata (±5 minuti)
        e se non abbiamo già fatto il controllo oggi
        
        Returns:
            True se bisogna controllare aggiornamenti, False altrimenti
        """
        try:
            now = datetime.now().time()
            target_time = time.fromisoformat(UPDATE_CHECK_TIME)
            
            # Calcola differenza in minuti
            now_minutes = now.hour * 60 + now.minute
            target_minutes = target_time.hour * 60 + target_time.minute
            time_diff = abs(now_minutes - target_minutes)
            
            # Finestra di 5 minuti per il controllo
            if time_diff <= 5:
                # Controlla se abbiamo già fatto l'update oggi
                if self.last_update_check:
                    if self.last_update_check.date() == datetime.now().date():
                        logging.debug("Update already checked today, skipping")
                        return False
                        
                logging.info("Time window for update check reached")
                return True
                
            return False
            
        except ValueError as e:
            logging.error(f"Invalid UPDATE_CHECK_TIME format: {e}")
            return False
        except Exception as e:
            logging.error(f"Error checking update schedule: {e}")
            return False
        
    async def run(self):
        """
        Loop principale del watchdog
        
        Esegue:
        1. Health check periodici del container
        2. Controllo aggiornamenti all'ora programmata
        3. Gestione errori e recovery
        """
        logging.info("=" * 80)
        logging.info("WATCHDOG SERVICE STARTED")
        logging.info("=" * 80)
        logging.info(f"GitHub Repo: {GITHUB_REPO}")
        logging.info(f"GitHub Branch: {GITHUB_BRANCH}")
        logging.info(f"Monitoring Container: {CONTAINER_NAME}")
        logging.info(f"Health Check Interval: {CHECK_INTERVAL}s")
        logging.info(f"Update Check Time: {UPDATE_CHECK_TIME}")
        logging.info(f"Maintenance Notice: {MAINTENANCE_NOTICE_MINUTES} minutes")
        logging.info("=" * 80)
        
        # Notifica Discord startup
        await notify_monitoring(
            f"🚀 Watchdog service started\n"
            f"Monitoring: `{CONTAINER_NAME}`\n"
            f"Update check: `{UPDATE_CHECK_TIME}` UTC\n"
            f"Health check: every `{CHECK_INTERVAL}s`",
            "success"
        )
        
        # Loop principale
        while self.running:
            try:
                # ============================================================
                # 1. HEALTH CHECK DEL CONTAINER
                # ============================================================
                logging.debug(f"Performing health check on '{CONTAINER_NAME}'")
                await self.check_container_health()
                
                # ============================================================
                # 2. CONTROLLO AGGIORNAMENTI (se è l'ora giusta)
                # ============================================================
                if await self.should_check_updates():
                    logging.info("=" * 80)
                    logging.info("UPDATE CHECK TRIGGERED")
                    logging.info("=" * 80)
                    
                    # Segna che abbiamo controllato oggi
                    self.last_update_check = datetime.now()
                    
                    # Controlla se ci sono aggiornamenti disponibili
                    current_sha = await get_current_commit_sha()
                    latest_sha = await get_latest_commit_sha()
                    
                    if not latest_sha:
                        logging.error("Could not fetch latest commit from GitHub")
                        await notify_monitoring(
                            "⚠️ Update check failed: Could not fetch latest commit from GitHub",
                            "warning"
                        )
                    elif current_sha == latest_sha:
                        logging.info("Already up to date - no update needed")
                        await notify_monitoring(
                            f"✅ Update check complete: Already up to date\n"
                            f"Current version: `{current_sha[:8] if current_sha else 'unknown'}`",
                            "info"
                        )
                    else:
                        logging.info(
                            f"Update available: "
                            f"{current_sha[:8] if current_sha else 'unknown'} -> {latest_sha[:8]}"
                        )
                        
                        # Esegui aggiornamento completo
                        update_success = await perform_update(
                            current_sha=current_sha,
                            latest_sha=latest_sha,
                        )
                        
                        if update_success:
                            logging.info("Update completed successfully")
                        else:
                            logging.error("Update failed - system rolled back")
                    
                    logging.info("=" * 80)
                    logging.info("UPDATE CHECK COMPLETED")
                    logging.info("=" * 80)
                
                # ============================================================
                # 3. ATTESA PRIMA DEL PROSSIMO CICLO
                # ============================================================
                await asyncio.sleep(CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                logging.info("Watchdog loop cancelled")
                break
                
            except Exception as e:
                logging.error(f"Unexpected error in watchdog loop: {e}", exc_info=True)
                await notify_monitoring(
                    f"❌ Watchdog error: {str(e)[:500]}",
                    "error"
                )
                # Attendi un po' prima di riprovare in caso di errore
                await asyncio.sleep(CHECK_INTERVAL)
        
        logging.info("Watchdog loop stopped")
                
    def stop(self):
        """
        Ferma il watchdog in modo graceful
        
        Chiamato dai signal handler per terminazione pulita
        """
        logging.info("Stop signal received")
        self.running = False

# ============================================================================
# SIGNAL HANDLERS
# ============================================================================

def setup_signal_handlers(watchdog: Watchdog):
    """
    Configura gli handler per i segnali di terminazione
    
    Args:
        watchdog: Istanza del watchdog da fermare
    """
    def signal_handler(signum, frame):
        """Handler per SIGTERM e SIGINT"""
        sig_name = signal.Signals(signum).name
        logging.info(f"Received signal {sig_name} ({signum})")
        watchdog.stop()
    
    # Registra handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logging.info("Signal handlers registered (SIGTERM, SIGINT)")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """
    Funzione principale del watchdog
    
    Gestisce:
    - Inizializzazione database pool
    - Creazione e avvio watchdog
    - Cleanup graceful alla terminazione
    """
    
    setup_logger()
    watchdog = None
    
    try:
        logging.info("=" * 80)
        logging.info("INITIALIZING WATCHDOG SERVICE")
        logging.info("=" * 80)
        
        # ====================================================================
        # 1. INIZIALIZZAZIONE DATABASE POOL
        # ====================================================================
        logging.info("Creating database connection pool...")
        await db_pool.create_pool()
        logging.info("Database pool created successfully")
        
        # ====================================================================
        # 2. CREAZIONE WATCHDOG
        # ====================================================================
        logging.info("Creating watchdog instance...")
        watchdog = Watchdog()
        
        # ====================================================================
        # 3. SETUP SIGNAL HANDLERS
        # ====================================================================
        setup_signal_handlers(watchdog)
        
        # ====================================================================
        # 4. AVVIO WATCHDOG
        # ====================================================================
        logging.info("Starting watchdog service...")
        await watchdog.run()
        
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
        
    except Exception as e:
        logging.critical(f"Fatal error in main: {e}", exc_info=True)
        await notify_monitoring(
            f"💥 Fatal watchdog error: {str(e)[:500]}",
            "error"
        )
        
    finally:
        # ====================================================================
        # CLEANUP
        # ====================================================================
        logging.info("=" * 80)
        logging.info("SHUTTING DOWN WATCHDOG SERVICE")
        logging.info("=" * 80)
        
        # Ferma watchdog se ancora in esecuzione
        if watchdog and watchdog.running:
            watchdog.stop()
        
        # Chiudi database pool
        try:
            logging.info("Closing database connection pool...")
            await db_pool.close_pool()
            logging.info("Database pool closed")
        except Exception as e:
            logging.error(f"Error closing database pool: {e}")
        
        # Notifica shutdown
        try:
            await notify_monitoring(
                "🛑 Watchdog service stopped",
                "warning"
            )
        except Exception as e:
            logging.error(f"Error sending shutdown notification: {e}")
        
        logging.info("=" * 80)
        logging.info("WATCHDOG SERVICE STOPPED")
        logging.info("=" * 80)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Entry point dello script
    
    Avvia il loop asyncio con la funzione main
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
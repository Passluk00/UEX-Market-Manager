import os
import psutil
from utils.i18n import t
from config import SYSTEM_LANGUAGE




def kill_process_on_port(port: int) -> bool:
    
    """
    Scans for and terminates any existing process occupying a specific network port.

    This utility is used during startup to ensure the required port is free. For 
    security, it includes protections against killing critical system processes 
    (like SSH), ignores its own PID, and only targets specific process types 
    (Python or Gunicorn).

    Args:
        port (int): The network port number to check and clear.

    Returns:
        bool: True if a process was found and successfully terminated, False otherwise.

    Note:
        The function attempts a graceful termination (terminate()) followed by a 
        forced kill (kill()) if the process does not exit within 3 seconds.
    """
    
    # --- SECURITY PROTECTION ---
    # Never touch port 22 (SSH) or invalid ports
    if port == 22 or port is None:
        return False

    current_pid = os.getpid()  # Avoid auto-kill

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            proc_name = (proc.info['name'] or "").lower()

            # Known processes only (extra protection)
            if 'python' not in proc_name and 'gunicorn' not in proc_name:
                continue

            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    if proc.info['pid'] == current_pid:
                        continue

                    print(
                        t(SYSTEM_LANGUAGE, "system.kill_found").format(
                            pid=proc.info['pid'],
                            port=port
                        )
                    )

                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()

                    print(
                        t(SYSTEM_LANGUAGE, "system.kill_success").format(
                            port=port
                        )
                    )
                    return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return False

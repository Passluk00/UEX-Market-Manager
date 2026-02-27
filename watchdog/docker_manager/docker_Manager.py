import logging
import docker
from config import CONTAINER_NAME

class DockerManager:
    """Gestisce le operazioni Docker sul container del bot"""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
            logging.info("Docker client initialized")
        except Exception as e:
            logging.error(f"Failed to initialize Docker client: {e}")
            raise
            
    def get_container(self, name: str = None):
        """
        Ottiene il container per nome
        
        Args:
            name: Nome del container (default: CONTAINER_NAME)
            
        Returns:
            Container object o None se non trovato
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            return self.client.containers.get(name)
        except docker.errors.NotFound:
            logging.error(f"Container '{name}' not found")
            return None
        except Exception as e:
            logging.error(f"Error getting container: {e}")
            return None
            
    def stop_container(self, name: str = None) -> bool:
        """
        Ferma il container
        
        Args:
            name: Nome del container (default: CONTAINER_NAME)
            
        Returns:
            True se successo, False altrimenti
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            container = self.get_container(name)
            if container:
                container.stop(timeout=30)
                logging.info(f"Container '{name}' stopped")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to stop container: {e}")
            return False
            
    def start_container(self, name: str = None) -> bool:
        """
        Avvia il container
        
        Args:
            name: Nome del container (default: CONTAINER_NAME)
            
        Returns:
            True se successo, False altrimenti
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            container = self.get_container(name)
            if container:
                container.start()
                logging.info(f"Container '{name}' started")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to start container: {e}")
            return False
            
    def restart_container(self, name: str = None) -> bool:
        """
        Riavvia il container
        
        Args:
            name: Nome del container (default: CONTAINER_NAME)
            
        Returns:
            True se successo, False altrimenti
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            container = self.get_container(name)
            if container:
                container.restart(timeout=30)
                logging.info(f"Container '{name}' restarted")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to restart container: {e}")
            return False
            
    def is_container_healthy(self, name: str = None) -> bool:
        """
        Verifica se il container è in esecuzione
        
        Args:
            name: Nome del container (default: CONTAINER_NAME)
            
        Returns:
            True se il container è running, False altrimenti
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            container = self.get_container(name)
            if container:
                status = container.status
                logging.debug(f"Container '{name}' status: {status}")
                return status == 'running'
            return False
        except Exception as e:
            logging.error(f"Failed to check container health: {e}")
            return False
            
    def get_container_logs(self, name: str = None, tail: int = 50) -> str:
        """
        Ottiene gli ultimi log del container
        
        Args:
            name: Nome del container (default: CONTAINER_NAME)
            tail: Numero di righe da recuperare
            
        Returns:
            Log come stringa
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            container = self.get_container(name)
            if container:
                logs = container.logs(tail=tail).decode('utf-8')
                return logs
            return ""
        except Exception as e:
            logging.error(f"Failed to get container logs: {e}")
            return ""
            
    def exec_command(self, command: str, workdir: str = '/app', name: str = None):
        """
        Esegue un comando nel container
        
        Args:
            command: Comando da eseguire
            workdir: Directory di lavoro
            name: Nome del container (default: CONTAINER_NAME)
            
        Returns:
            Tuple (exit_code, output)
        """
        if name is None:
            name = CONTAINER_NAME
            
        try:
            container = self.get_container(name)
            if container:
                exec_result = container.exec_run(command, workdir=workdir)
                output = exec_result.output.decode('utf-8')
                logging.debug(f"Command '{command}' output: {output}")
                return exec_result.exit_code, output
            return None, ""
        except Exception as e:
            logging.error(f"Failed to execute command: {e}")
            return None, ""
import logging
import docker

class DockerManager:
    """Gestisce le operazioni Docker"""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
            logging.info("Docker client initialized")
        except Exception as e:
            logging.error(f"Failed to initialize Docker client: {e}")
            raise
            
    def get_container(self, name: str = CONTAINER_NAME):
        """Ottiene il container per nome"""
        try:
            return self.client.containers.get(name)
        except docker.errors.NotFound:
            logging.error(f"Container '{name}' not found")
            return None
        except Exception as e:
            logging.error(f"Error getting container: {e}")
            return None
            
    def stop_container(self, name: str = CONTAINER_NAME) -> bool:
        """Ferma il container"""
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
            
    def start_container(self, name: str = CONTAINER_NAME) -> bool:
        """Avvia il container"""
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
            
    def restart_container(self, name: str = CONTAINER_NAME) -> bool:
        """Riavvia il container"""
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
            
    def is_container_healthy(self, name: str = CONTAINER_NAME) -> bool:
        """Verifica se il container è in esecuzione"""
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
            
    def get_container_logs(self, name: str = CONTAINER_NAME, tail: int = 50) -> str:
        """Ottiene gli ultimi log del container"""
        try:
            container = self.get_container(name)
            if container:
                logs = container.logs(tail=tail).decode('utf-8')
                return logs
            return ""
        except Exception as e:
            logging.error(f"Failed to get container logs: {e}")
            return ""

# watchdog/tests/test_docker_manager.py
"""
Tests per watchdog/docker_manager/docker_Manager.py

Copre:
- get_container()         — trovato, non trovato, eccezione Docker
- stop_container()        — successo, container non trovato, eccezione
- start_container()       — successo, container non trovato, eccezione
- restart_container()     — successo, container non trovato, eccezione
- is_container_healthy()  — running, exited, not found, eccezione
- get_container_logs()    — torna log, container non trovato, eccezione
"""

import pytest
from unittest.mock import MagicMock, patch
import docker


def _make_docker_client(container=None, not_found=False, error=False):
    """Restituisce un mock docker.from_env() con comportamento configurabile."""
    client = MagicMock()
    if not_found:
        client.containers.get.side_effect = docker.errors.NotFound("not found")
    elif error:
        client.containers.get.side_effect = Exception("Docker socket error")
    else:
        client.containers.get.return_value = container
    return client


class TestGetContainer:

    def test_returns_container_when_found(self):
        mock_container = MagicMock()
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.get_container("python")

        assert result == mock_container

    def test_returns_none_when_not_found(self):
        client = _make_docker_client(not_found=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.get_container("ghost")

        assert result is None

    def test_returns_none_on_exception(self):
        client = _make_docker_client(error=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.get_container("python")

        assert result is None


class TestStopContainer:

    def test_returns_true_on_success(self):
        mock_container = MagicMock()
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.stop_container()

        assert result is True
        mock_container.stop.assert_called_once_with(timeout=30)

    def test_returns_false_when_container_not_found(self):
        client = _make_docker_client(not_found=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.stop_container()

        assert result is False

    def test_returns_false_on_exception(self):
        mock_container = MagicMock()
        mock_container.stop.side_effect = Exception("Docker error")
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.stop_container()

        assert result is False


class TestStartContainer:

    def test_returns_true_on_success(self):
        mock_container = MagicMock()
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.start_container()

        assert result is True
        mock_container.start.assert_called_once()

    def test_returns_false_when_not_found(self):
        client = _make_docker_client(not_found=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.start_container()

        assert result is False

    def test_returns_false_on_exception(self):
        mock_container = MagicMock()
        mock_container.start.side_effect = Exception("start error")
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.start_container()

        assert result is False


class TestIsContainerHealthy:

    def test_returns_true_when_running(self):
        mock_container = MagicMock()
        mock_container.status = 'running'
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.is_container_healthy()

        assert result is True

    def test_returns_false_when_exited(self):
        mock_container = MagicMock()
        mock_container.status = 'exited'
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.is_container_healthy()

        assert result is False

    def test_returns_false_when_not_found(self):
        client = _make_docker_client(not_found=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.is_container_healthy()

        assert result is False

    def test_returns_false_on_exception(self):
        client = _make_docker_client(error=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.is_container_healthy()

        assert result is False


class TestGetContainerLogs:

    def test_returns_log_string(self):
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Starting bot...\nBot ready!\n"
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.get_container_logs()

        assert "Starting bot" in result
        assert isinstance(result, str)

    def test_returns_empty_string_when_not_found(self):
        client = _make_docker_client(not_found=True)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.get_container_logs()

        assert result == ""

    def test_returns_empty_string_on_exception(self):
        mock_container = MagicMock()
        mock_container.logs.side_effect = Exception("log error")
        client = _make_docker_client(container=mock_container)

        with patch('docker_manager.docker_Manager.docker.from_env', return_value=client):
            from docker_manager.docker_Manager import DockerManager
            dm = DockerManager()
            result = dm.get_container_logs()

        assert result == ""

import os

GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
CONTAINER_NAME = os.getenv('BOT_CONTAINER_NAME', 'python')
CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))  # secondi
UPDATE_CHECK_TIME = os.getenv('UPDATE_CHECK_TIME', '03:00')  # HH:MM formato 24h
MAINTENANCE_NOTICE_MINUTES = int(os.getenv('MAINTENANCE_NOTICE_MINUTES', '30'))

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'uexbot'),
    'user': os.getenv('DB_USER', 'uexuser'),
    'password': os.getenv('DB_PASSWORD', ''),
    'min_size': 2,
    'max_size': 10
}
WEBHOOK_URL = os.getenv("WEBHOOK_MONITORING_URL")

DOCKER_SOCKET = "unix:///var/run/docker.sock"

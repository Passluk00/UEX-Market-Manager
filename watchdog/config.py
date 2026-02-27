import os


# GitHub Configuration
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Passluk00/UEX-Market-Manager')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

# Docker Configuration
CONTAINER_NAME = os.getenv('BOT_CONTAINER_NAME', 'python')

# Git / Update Configuration
# Host-side path where the repo root is mounted inside the watchdog container.
# In docker-compose.yml we mount ./:/repo so git operations run on the real files.
GIT_REPO_PATH = os.getenv('GIT_REPO_PATH', '/repo')

# Timing Configuration
CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '60'))   # seconds
UPDATE_CHECK_TIME = os.getenv('UPDATE_CHECK_TIME', '03:00')        # HH:MM 24h UTC
MAINTENANCE_NOTICE_MINUTES = int(os.getenv('MAINTENANCE_NOTICE_MINUTES', '30'))

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'uexbot'),
    'user': os.getenv('DB_USER', 'uexuser'),
    'password': os.getenv('DB_PASSWORD', ''),
    'min_size': 2,
    'max_size': 10
}

# Discord Webhooks
WEBHOOK_MONITORING = os.getenv('WEBHOOK_MONITORING_URL')

# File Paths
COMMIT_SHA_FILE = os.path.join(GIT_REPO_PATH, 'bot', '.git_commit_sha')
LOG_FILE = '/app/watchdog.log'

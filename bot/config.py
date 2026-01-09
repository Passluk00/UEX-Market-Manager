import os

PORT = int(os.getenv("PORT", 20187))
TUNNEL_URL = os.getenv("TUNNEL_URL")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_MONITORING_URL = os.getenv("WEBHOOK_MONITORING_URL")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", 5432))

SYSTEM_LANGUAGE = os.getenv("SYSTEM_LANGUAGE", "en")   
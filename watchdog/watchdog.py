import docker
import time
import requests
import logging
from config import *

# ================= UTIL =================


def set_maintenance(minute_delay):
    
    try:
        
        
        
        
        
    except Exception as e:
        logging.error(f"errore: {e}")


def send_webhook(message, color=15158332):
    payload = {
        "username": "Docker Watchdog",
        "embeds": [{
            "title": "🐶 Watchdog",
            "description": message,
            "color": color,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }]
    }

    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        logging.info(f"[WEBHOOK] {r.status_code} → {message}")
    except Exception as e:
        logging.error(f"[WEBHOOK ERROR] {e}")

# ================= CORE =================

def connect_docker():
    client = docker.DockerClient(base_url=DOCKER_SOCKET)
    client.ping()
    return client

def restart_container(client):
    try:
        container = client.containers.get(CONTAINER_NAME)
        container.start()
        logging.info(f"🔄 Container {CONTAINER_NAME} Restarted")

        send_webhook(
            f"🔄 Container `{CONTAINER_NAME}` automatically RESTARTED",
            color=3066993  # green
        )
    except Exception as e:
        logging.error(f"❌ Container restart error: {e}")
        send_webhook(
            f"❌ ERROR restarting `{CONTAINER_NAME}`\n```{e}```",
            color=15158332
        )

def watchdog_loop():
    logging.info("🐶 Watchdog started")

    while True:
        try:
            client = connect_docker()
            logging.info("✅ Connected to Docker Engine")

            while True:
                try:
                    container = client.containers.get(CONTAINER_NAME)
                    status = container.status

                    logging.debug(f"🔍 State {CONTAINER_NAME}: {status}")

                    if status != "running":
                        logging.error("⚠️ Bot NON running → Restarting")
                        send_webhook(
                            f"⚠️ Container `{CONTAINER_NAME}` status `{status}` → RESTART",
                            color=15105570  # orange
                        )
                        restart_container(client)

                except docker.errors.NotFound:
                    logging.error("❌ Container NOT found → attempt to start")
                    send_webhook(
                        f"❌ Container `{CONTAINER_NAME}` NOT found → forced start",
                        color=15158332
                    )
                    restart_container(client)

                time.sleep(CHECK_INTERVAL)

        except Exception as e:
            logging.error(f"❌ Docker not available: {e}")
            send_webhook(
                f"❌ Docker Engine NOT available\n```{e}```",
                color=15158332
            )
            time.sleep(10)

# ================= MAIN =================

if __name__ == "__main__":
    watchdog_loop()

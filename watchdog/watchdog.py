import docker
import time
import requests
import os

# ================= CONFIG =================

BOT_CONTAINER_NAME = "python"  
CHECK_INTERVAL = 15  # SECONDS

WEBHOOK_URL = os.getenv("WEBHOOK_MONITORING_URL")

DOCKER_SOCKET = "unix:///var/run/docker.sock"

# ================= UTIL =================

def log(msg):
    print(msg, flush=True)

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
        log(f"[WEBHOOK] {r.status_code} → {message}")
    except Exception as e:
        log(f"[WEBHOOK ERROR] {e}")

# ================= CORE =================

def connect_docker():
    client = docker.DockerClient(base_url=DOCKER_SOCKET)
    client.ping()
    return client

def restart_container(client):
    try:
        container = client.containers.get(BOT_CONTAINER_NAME)
        container.start()
        log(f"🔄 Container {BOT_CONTAINER_NAME} Restarted")

        send_webhook(
            f"🔄 Container `{BOT_CONTAINER_NAME}` automatically RESTARTED",
            color=3066993  # green
        )
    except Exception as e:
        log(f"❌ Container restart error: {e}")
        send_webhook(
            f"❌ ERROR restarting `{BOT_CONTAINER_NAME}`\n```{e}```",
            color=15158332
        )

def watchdog_loop():
    log("🐶 Watchdog started")

    while True:
        try:
            client = connect_docker()
            log("✅ Connected to Docker Engine")

            while True:
                try:
                    container = client.containers.get(BOT_CONTAINER_NAME)
                    status = container.status

                    log(f"🔍 State {BOT_CONTAINER_NAME}: {status}")

                    if status != "running":
                        log("⚠️ Bot NON running → Restarting")
                        send_webhook(
                            f"⚠️ Container `{BOT_CONTAINER_NAME}` status `{status}` → RESTART",
                            color=15105570  # orange
                        )
                        restart_container(client)

                except docker.errors.NotFound:
                    log("❌ Container NOT found → attempt to start")
                    send_webhook(
                        f"❌ Container `{BOT_CONTAINER_NAME}` NOT found → forced start",
                        color=15158332
                    )
                    restart_container(client)

                time.sleep(CHECK_INTERVAL)

        except Exception as e:
            log(f"❌ Docker not available: {e}")
            send_webhook(
                f"❌ Docker Engine NOT available\n```{e}```",
                color=15158332
            )
            time.sleep(10)

# ================= MAIN =================

if __name__ == "__main__":
    watchdog_loop()

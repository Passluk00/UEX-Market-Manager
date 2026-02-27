import logging
from datetime import datetime
from config import WEBHOOK_MONITORING
import aiohttp

async def send_discord_webhook(webhook_url: str, embed: dict):
    """Invia una notifica via Discord webhook"""
    if not webhook_url:
        logging.warning("No webhook URL provided")
        return
        
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"embeds": [embed]}
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 204:
                    logging.info(f"Discord notification sent successfully")
                else:
                    logging.error(f"Discord webhook error: {response.status}")
    except Exception as e:
        logging.error(f"Failed to send Discord webhook: {e}")

async def notify_update_success(old_sha: str, new_sha: str):
    """Notifica aggiornamento riuscito"""
    embed = {
        "title": "✅ Update Successful",
        "description": "The bot has been updated successfully",
        "color": 0x00FF00,
        "fields": [
            {"name": "Old Version", "value": f"`{old_sha[:8]}`", "inline": True},
            {"name": "New Version", "value": f"`{new_sha[:8]}`", "inline": True}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_discord_webhook(WEBHOOK_MONITORING, embed)

async def notify_update_failure(error: str, old_sha: str):
    """Notifica fallimento aggiornamento con rollback"""
    try:
        embed = {
            "title": "❌ Update Failed - Rollback Executed",
            "description": f"Update failed and system rolled back to previous version",
            "color": 0xFF0000,
            "fields": [
                {"name": "Error", "value": f"```{error[:1000]}```", "inline": False},
                {"name": "Rolled Back To", "value": f"`{old_sha[:8]}`", "inline": True}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        await send_discord_webhook(WEBHOOK_MONITORING, embed)
    except Exception as e:
        logging.error(f"Failed to send update failure notification: {e}")


async def notify_monitoring(message: str, level: str = "info"):
    """Notifica eventi generici al monitoring webhook"""
    colors = {
        "info": 0x0099FF,
        "warning": 0xFFAA00,
        "error": 0xFF0000,
        "success": 0x00FF00
    }
    
    embed = {
        "title": f"🔔 Watchdog Notification",
        "description": message,
        "color": colors.get(level, 0x0099FF),
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_discord_webhook(WEBHOOK_MONITORING, embed)


async def notify_update_started(current_sha: str, latest_sha: str, minutes: int):
    """
    Notifica inizio procedura di aggiornamento
    
    Args:
        current_sha: SHA del commit corrente
        latest_sha: SHA del commit target
        minutes: Minuti di preavviso
    """
    embed = {
        "title": "🔧 Maintenance Scheduled",
        "description": f"System update will begin in {minutes} minutes",
        "color": 0xFFAA00,
        "fields": [
            {"name": "Current Version", "value": f"`{current_sha[:8]}`", "inline": True},
            {"name": "Target Version", "value": f"`{latest_sha[:8]}`", "inline": True},
            {"name": "Downtime", "value": "~5-10 minutes", "inline": False}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_discord_webhook(WEBHOOK_MONITORING, embed)

async def notify_container_restart(container_name: str, reason: str = "unhealthy"):
    """
    Notifica restart del container
    
    Args:
        container_name: Nome del container
        reason: Motivo del restart
    """
    embed = {
        "title": "🔄 Container Restarted",
        "description": f"Container `{container_name}` has been restarted",
        "color": 0xFFAA00,
        "fields": [
            {"name": "Reason", "value": reason, "inline": True},
            {"name": "Status", "value": "Running", "inline": True}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_discord_webhook(WEBHOOK_MONITORING, embed)
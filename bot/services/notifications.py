import logging
import datetime
import requests
from utils.i18n import t
from config import WEBHOOK_MONITORING_URL, SYSTEM_LANGUAGE



async def send_startup_notification():
    
    """
    Sends a system startup notification to a dedicated Discord monitoring channel via Webhook.

    This function creates a localized embed message containing the bot's current status 
    and the actions performed during initialization. It uses the monitoring URL defined 
    in the configuration and includes a UTC timestamp.

    Returns:
        None

    Raises:
        Exception: Logs an error if the HTTP POST request to the monitoring webhook fails.
    """
    
    lang = SYSTEM_LANGUAGE

    payload = {
        "embeds": [{
            "title": t(lang, "startup.title"),
            "description": t(lang, "startup.description"),
            "color": 3066993,
            "fields": [
                {
                    "name": t(lang, "startup.status_name"),
                    "value": t(lang, "startup.status_value"),
                    "inline": True
                },
                {
                    "name": t(lang, "startup.action_name"),
                    "value": t(lang, "startup.action_value"),
                    "inline": True
                }
            ],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }]
    }

    try:
        requests.post(WEBHOOK_MONITORING_URL, json=payload, timeout=5)
    except Exception as e:
        logging.error(f"💥 Unable to send startup notification: {e}")

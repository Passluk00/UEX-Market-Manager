import logging
from aiohttp import web
from utils.i18n import t
from config import PORT, SYSTEM_LANGUAGE
from utils.ports import kill_process_on_port
from webserver.handlers import handle_webhook_unificato




async def handle_webhook(request):
    
    """
    Handles incoming POST requests for webhooks.

    Extracts event details and user identification from the URL path, delegates 
    processing to the unified handler, and returns an appropriate HTTP response.

    Args:
        request (aiohttp.web.Request): The incoming HTTP request containing 
                                    path parameters and JSON payload.

    Returns:
        aiohttp.web.Response: HTTP response with the status and result message.
    """
    
    try:
        
        event_type = request.match_info["event_type"]
        user_id = request.match_info["user_id"]
        result = await handle_webhook_unificato(request, event_type, user_id)
        logging.info(
            t(SYSTEM_LANGUAGE, 
                "server.webhook_request",
                user_id=user_id,
                event=event_type
            )
        )
        return web.Response(status=result["status"], text=result["text"])
    
    except Exception as e:
    
        logging.exception(
            t(SYSTEM_LANGUAGE, "server.webhook_error",error=e)
        )
        return web.Response(status=500, text=f"Error: {e}")


async def handle_health(request):
    
    """
    Simple health check endpoint to verify if the server is reachable.

    Returns:
        aiohttp.web.Response: A 200 OK response with 'online' text.
    """
    
    return web.Response(status=200, text=f"online")


async def start_aiohttp_server():
    
    """
    Initializes and starts the asynchronous HTTP server.

    This function performs the following setup:
    1. Configures routes for dynamic webhooks and health checks.
    2. Ensures the target PORT is available by terminating conflicting processes.
    3. Binds the server to '0.0.0.0' to allow external traffic.
    4. Logs the successful startup or critical failures.

    Returns:
        None
    """
    
    app = web.Application()
    app.router.add_post("/webhook/{event_type}/{user_id}", handle_webhook)
    app.router.add_get("/health", handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    try:
        # Free the port only once (using the previously modified safe function)
        kill_process_on_port(PORT)
        
        # Attempt to launch the site
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logging.info(
            t(SYSTEM_LANGUAGE, "server.started", port=PORT)
        )
        
    except Exception as e:
  
        logging.critical(
            t(SYSTEM_LANGUAGE, "server.start_failed", error=e)
        )
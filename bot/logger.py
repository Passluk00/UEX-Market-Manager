import sys
import logging



"""
Configures the global logging system for the application.

This function performs two main tasks:
1. **UTF-8 Enforcement**: Reconfigures standard output and error streams to use UTF-8 
   encoding, preventing crashes or broken characters when logging emojis or 
   special symbols on certain operating systems (like Windows).
2. **Multi-Handler Logging**: Sets up a centralized logging format that records 
   timestamps, log levels, and messages. Logs are simultaneously sent to the 
   console (stdout) and persisted in a file named 'bot.log'.

Returns:
    None
"""
def setup_logger():
    # Force UTF-8 output (Windows fix)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

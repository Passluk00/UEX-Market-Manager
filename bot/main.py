from discord_bot.bot import bot
from logger import setup_logger
from config import DISCORD_TOKEN
from discord_bot.events import *
from discord_bot.commands import *


setup_logger()



"""
Main entry point for the Discord Bot application.

This script orchestrates the startup process by:
1. Initializing the global logger with UTF-8 support and file logging.
2. Importing all event listeners and slash commands to register them with the bot.
3. Starting the Discord client using the provided authentication token.

The bot runs in a blocking loop until the process is terminated.
"""

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

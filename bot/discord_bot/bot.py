import discord
from discord.ext import commands


intents = discord.Intents.default()
intents.message_content = True
intents.members = True



"""
Initializes the Discord Bot instance with required intents and configurations.

This setup defines the gateway intents necessary for the bot to function, 
specifically enabling access to message content and member events. It also 
initializes the command prefix and an internationalization placeholder.

Args:
    command_prefix (str): The prefix used to trigger bot commands.
    intents (discord.Intents): The configured gateway intents for the bot.

Returns:
    commands.Bot: The configured Discord bot instance.
"""
bot = commands.Bot(command_prefix="!", intents=intents)
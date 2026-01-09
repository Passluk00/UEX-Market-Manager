import discord
import logging
import db.pool as pool
from utils.i18n import t
import db.sessions as sessions
from discord_bot.bot import bot
from discord import app_commands
from discord_bot.views import OpenThreadButton
from config import SYSTEM_LANGUAGE



"""
Displays bot statistics including total registered users and active threads.
Requires 'Manage Guild' permissions.

Args:
    interaction (discord.Interaction): The interaction object for the slash command.

Returns:
    None
"""
@bot.tree.command(name="stats", description="Show bot statistics")
@app_commands.checks.has_permissions(manage_guild=True)
async def stats(interaction: discord.Interaction):
    
    lang = await sessions.resolve_and_store_language(interaction)
    
    
    if pool.db_pool is None:
        logging.error("❌ Database not initialized for /stats")
        await interaction.response.send_message(
            t(lang, "db_not_initialized"),
            ephemeral=True
        )
        return

    try:
        async with pool.db_pool.acquire() as conn:
            # Total number of registered users
            users_count = await conn.fetchval("SELECT COUNT(*) FROM sessions")
            
            # number of active threads (non-null thread_id)
            threads_active = await conn.fetchval(
                "SELECT COUNT(*) FROM sessions WHERE thread_id IS NOT NULL"
            )

        embed = discord.Embed(
            title=t(lang, "stats_title"),
            color=discord.Color.green()
        )
        embed.add_field(
            name=t(lang, "stats_users"),
            value=str(users_count),
            inline=True
        )
        embed.add_field(
            name=t(lang, "stats_threads"),
            value=str(threads_active),
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logging.exception(f"❌ Critical Error stats: {e}")
        await interaction.response.send_message(
                    t(lang, "stats_error"),
                    ephemeral=True
                )



"""
Sends an embed with a button to open a private chat thread in a specified channel.
Requires 'Manage Guild' permissions.

Args:
    interaction (discord.Interaction): The interaction object for the slash command.
    canale (discord.TextChannel): The target channel where the button will be sent.

Returns:
    None
"""
@bot.tree.command(name="add", description="Add the private chat button to a channel")
@app_commands.describe(canale="Channel where the button message will be sent")
@app_commands.checks.has_permissions(manage_guild=True)
async def add_button(interaction: discord.Interaction, canale: discord.TextChannel):
    """Slash command to add the button to a specific channel."""
    
    lang = SYSTEM_LANGUAGE
    
    try:
        view = OpenThreadButton(lang=lang)

        embed = discord.Embed(
            title=t(lang, "add_title"),
            description=t(lang, "add_description"),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text=t(lang, "add_footer")
        )

        embed.set_thumbnail(url="https://uexcorp.space/favicon.ico")

        await canale.send(embed=embed, view=view)
        await interaction.response.send_message(
            t(lang, "add_success", channel=canale.mention),
            ephemeral=True
        )

        logging.info(
            f"🔘 Button added by {interaction.user} in {canale.name}"
        )

    except Exception as e:
        logging.exception("💥 Error adding button with /add")
        await interaction.response.send_message(
            t(lang, "add_error"),
            ephemeral=True
        )
        
        
        
"""
Sets or updates the personalized welcome message for the user's future negotiations.

Args:
    interaction (discord.Interaction): The interaction object for the slash command.
    message (str): The full text of the welcome message.

Returns:
    None
"""
@bot.tree.command(name="add_welcome_message",description="Add or edit the welcome message for new negotiations")
@app_commands.describe(message="Full welcome message to be sent to users when they start a new negotiation")
async def add_welcome_message(interaction: discord.Interaction, message: str):
    user_id = str(interaction.user.id)

    lang = await sessions.resolve_and_store_language(interaction)

    # Salva direttamente il messaggio di benvenuto nel DB
    await sessions.save_user_session(
        user_id=user_id,
        welcome_message=message
    )

    await interaction.response.send_message(
        t(lang, "welcome_saved", message=message),
        ephemeral=True
    )
    logging.info(f"💾 Welcome message updated for user {user_id}")



"""
Enables or disables the automatic sending of the welcome message during negotiations.

Args:
    interaction (discord.Interaction): The interaction object for the slash command.
    enable (bool): Set to True to enable, False to disable.

Returns:
    None
"""
@bot.tree.command(name="enable_welcome_mex", description="Enable or disable the welcome message")
@app_commands.describe(enable="True to enable, False to disable the welcome message")
async def enable_welcome_mex(interaction: discord.Interaction, enable: bool):
    
    lang = await sessions.resolve_and_store_language(interaction)
    
    
    user_id = str(interaction.user.id)

    await sessions.save_user_session(
        user_id=user_id,
        enable=enable
    )

    await interaction.response.send_message(
        t(
            lang,
            "welcome_toggle",
            status=t(lang, "enabled") if enable else t(lang, "disabled")
        ),
        ephemeral=True
    )

    logging.info(f"💾 Welcome message {'enabled' if enable else 'disabled'} for {user_id}")










#### Command For Testing Only

# @bot.tree.command(name="lingua_impostata", description="Mostra la lingua attualmente impostata per il bot")
# @app_commands.checks.has_permissions(manage_guild=True)
# async def show_language(interaction: discord.Interaction):
#    
#    user_id = str(interaction.user.id)
#    var = await sessions.get_user_language(user_id=user_id)
#    
#    if var == "it":
#        logging.info(f"🌐 Lingua impostata su Italiana")
#        await interaction.response.send_message("🌐 La lingua attualmente impostata è: **Italiana 🇮🇹**", ephemeral=True)
#    
#    else:
#        logging.info(f"🌐 Lingua impostata su Inglese come default")
#        await interaction.response.send_message("🌐 The currently set language is: **English 🇺🇸**", ephemeral=True)
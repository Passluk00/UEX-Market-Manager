import discord
import logging
import db.pool as pool
import db.banned as ban
from utils.i18n import t
import db.sessions as sessions
from discord_bot.bot import bot
from discord import app_commands
from config import SYSTEM_LANGUAGE
from utils.roles_management import has_uex_manager_role
from discord_bot.views import OpenThreadButton


admin_group = app_commands.Group(
    name="admin",
    description="Admin-only bot management commands"
)

            
        

@bot.tree.command(name="add_welcome_message",description="Add or edit the welcome message for new negotiations")
@app_commands.describe(message="Full welcome message to be sent to users when they start a new negotiation")
async def add_welcome_message(interaction: discord.Interaction, message: str):
    
    
    """
    Sets or updates the personalized welcome message for the user's future negotiations.

    Args:
        interaction (discord.Interaction): The interaction object for the slash command.
        message (str): The full text of the welcome message.

    Returns:
        None
    """
    
    
    user_id = str(interaction.user.id)
    lang = await sessions.resolve_and_store_language(interaction)

    await sessions.save_user_session(
        user_id=user_id,
        welcome_message=message
    )

    await interaction.response.send_message(
        t(lang, "welcome_saved", message=message),
        ephemeral=True
    )
    logging.info(f"💾 Welcome message updated for user {user_id}")


@bot.tree.command(name="enable_welcome_mex", description="Enable or disable the welcome message")
@app_commands.describe(enable="True to enable, False to disable the welcome message")
async def enable_welcome_mex(interaction: discord.Interaction, enable: bool):

    """
    Enables or disables the automatic sending of the welcome message during negotiations.

    Args:
        interaction (discord.Interaction): The interaction object for the slash command.
        enable (bool): Set to True to enable, False to disable.

    Returns:
        None
    """

    
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




############  Admin Only Command  ############



@admin_group.command(name="add", description="Add the private chat button to a channel")
@app_commands.describe(
    channel="Channel where the button message will be sent",
    language="Language of the button message"
)
@app_commands.choices(
    language=[
        app_commands.Choice(name="🇮🇹 Italiano", value="it"),
        app_commands.Choice(name="🇬🇧 English", value="en"),
        app_commands.Choice(name="🇩🇪 Deutsch", value="de"),
        app_commands.Choice(name="🇫🇷 Français", value="fr"),
        app_commands.Choice(name="🇵🇱 Polski", value="pl"),
        app_commands.Choice(name="🇵🇹 Português", value="pt"),
        app_commands.Choice(name="🇷🇺 Русский", value="ru"),
        app_commands.Choice(name="🇨🇳 中文", value="zh"),
    ]
)
@has_uex_manager_role()
async def add_button(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    language: app_commands.Choice[str]
):
    
    """
    Sends an embed with a button to open a private chat thread in a specified channel.
    
    Requires 'Manage Guild' permissions.

    Args:
        interaction (discord.Interaction): The interaction object for the slash command.
        canale (discord.TextChannel): The target channel where the button will be sent.

    Returns:
        None
    """
    
    
    
    lang = language.value

    try:
        view = OpenThreadButton(lang=lang)

        embed = discord.Embed(
            title=t(lang, "add_title"),
            description=t(lang, "add_description"),
            color=discord.Color.blurple()
        )

        embed.set_footer(text=t(lang, "add_footer"))
        embed.set_thumbnail(url="https://uexcorp.space/favicon.ico")

        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            t(lang, "add_success", channel=channel.mention),
            ephemeral=True
        )

        logging.info(
            f"🔘 Button added by {interaction.user} in {channel.name} (lang={lang})"
        )

    except Exception:
        logging.exception("💥 Error adding button with /add")
        await interaction.response.send_message(
            t(lang, "add_error"),
            ephemeral=True
        ) 


@admin_group.command(name="stats", description="Show bot statistics")
@has_uex_manager_role()
async def stats(interaction: discord.Interaction):
    
    """
    Displays bot statistics including total registered users and active threads.
    Requires 'Manage Guild' permissions.

    Args:
        interaction (discord.Interaction): The interaction object for the slash command.

    Returns:
        None
    """
        
    
    lang = SYSTEM_LANGUAGE
    
    
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


@admin_group.command(name="ban", description="Ban a specific user")
@app_commands.describe(user="Ban a specific user, insert the motivations")
@has_uex_manager_role()
async def ban_user(
    interaction: discord.Interaction,
    user: discord.Member
):
    lang = await sessions.resolve_and_store_language(interaction)

    try:
        
        thread_id = await sessions.get_user_thread_id(user_id=user.id)
        
        if not thread_id:
            await interaction.response.send_message(
                t(lang, "chat_not_found", username=user.name),
                ephemeral=True
            )
            return
        
        thread = await interaction.client.fetch_channel(int(thread_id))
            
        await thread.send(
            t(lang, "chat_closed_readonly")
        )
        
        await thread.edit(
            locked=True
        )
        
        await sessions.remove_user_session(user_id=user.id)
        await ban.ban_user(user_id=user.id)
        
        await interaction.response.send_message(
            t(lang, "deleted_user", username=user.name),
            ephemeral=True
        )

        logging.info(t(lang, "deleted_user_info",username=user.name, admin=interaction.user.name),)

    except Exception as e:
        logging.info(t(lang, "deleted_user_error",username=user.name, e=e),)

        
        await interaction.response.send_message(
            t(lang, "generic_error_command_delete"),
            ephemeral=True
        )   


@admin_group.command(name="unban", description="Unban a specific user")
@app_commands.describe(user="Unban a specific user")
@has_uex_manager_role()
async def unban_user(
    interaction: discord.Interaction,
    user: discord.Member
):
    lang = await sessions.resolve_and_store_language(interaction)
    
    try:
        await ban.unban_user(user_id=user.id)
        
        await interaction.response.send_message(
            t(lang, "unban_user", username=user.name),
            ephemeral=True
        )
        
        logging.info(t(lang, "unban_user", username=user.name))
        
    except Exception as e:
        logging.error(t(lang, "unban_user_error_e", username=user.name, e=e))
        await interaction.response.send_message(
            t(lang, "unban_user_error", username=user.name),
            ephemeral=True
        )
        

bot.tree.add_command(admin_group)






@bot.tree.interaction_check
async def check_user_ban(interaction: discord.Interaction) -> bool:
    # security: only on guild
    if not interaction.guild:
        return True

    member = interaction.user

    # ignore admin (UEX Manager)
    uex_manager_role = discord.utils.get(member.roles, name="UEX Manager")
    if uex_manager_role:
        return True

    banned, reason = await ban.is_banned(member.id)
    if banned:
        lang = await sessions.resolve_and_store_language(interaction)

        await interaction.response.send_message(
            t(lang, "access_denied_ban", reason=reason),
            ephemeral=True
        )
        return False  # ⛔ Block All

    return True

    


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
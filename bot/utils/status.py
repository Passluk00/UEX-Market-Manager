import logging
import discord
import db.banned as ban
from utils.i18n import t
from discord.ext import tasks
import db.sessions as sessions
from datetime import datetime, timezone
from db.maintenance import get_status_message, set_maintenance, update_maintenance_state_if_needed



async def build_status_embed(lang: str) -> discord.Embed:
    
    """ Constructs a dynamic Embed representing the current operational status of the bot.

    This function triggers a maintenance state check and builds a visual summary 
    of the bot's health. It adjusts colors and fields based on whether maintenance 
    is currently active, scheduled for the future, or disabled.

    Args:
        None (Uses internal state from update_maintenance_state_if_needed).

    Returns:
        discord.Embed: A formatted embed containing the bot status, maintenance 
                    period details, and automatic update information.
    """
    
    state, status = await update_maintenance_state_if_needed()
    now = discord.utils.utcnow()

    embed = discord.Embed(
        title="🤖 UEX Bot Status",
        color=discord.Color.green(),
        timestamp=now
    )
   
    embed.add_field(
        name=t(lang=lang, key="status_bot_online"),
        value="`Online`"
    )
    
    if state == "active":
        
        embed.color = discord.Color.red()
        
        embed.add_field(
            name = t(lang=lang,key="maintenance_status"),
            value = t(lang=lang, key="status_value_active"),
            inline=False
        )
        
        embed.add_field(
            
            name= t(lang=lang,key="maintenance_status"),
            value= t(lang=lang, key="maintenance_period_value", 
                     maintenance_start=status['maintenance_start'], 
                     maintenance_end=status['maintenance_end']),
            inline=False
        )
        
        embed.add_field(
        
            name= t(lang=lang,key="maintenance_message"),
            value= status.get("maintenance_message") or "—", 
            inline=False
        )


    # caso manutenzione programmata
    elif state == "scheduled":
        embed.color = discord.Color.yellow()
        
        embed.add_field(
            
            name=t(lang=lang,key="maintenance_status"),
            value=t(lang=lang, key="status_value_scheduled"),
            inline=False
        )
        
        embed.add_field(
            
            name=t(lang=lang,key="maintenance_period"),
            value=str(status["maintenance_start"]), 
            inline=False
        )

    else:
        
        embed.color = discord.Color.green()
        embed.add_field(
        
            name=t(lang=lang,key="maintenance_status"),
            value=t(lang=lang, key="status_value_none"),
            inline=False
        )

    embed.set_footer(
        text= t(lang=lang, key="update_every_30_seconds")
    )
    
    return embed


async def update_status_message(bot: discord.Client):
    
    """ Retrieves and updates the existing status embed message with the latest bot information.

    This function fetches the stored channel and message IDs from the database, 
    locates the message within the Discord guild, and edits it with a freshly 
    generated status embed. It handles missing channels or messages gracefully 
    to avoid unnecessary crashes.

    Args:
        bot (discord.Client): The bot instance used to fetch the channel and edit the message.

    Returns:
        None: The function performs an in-place edit of the Discord message 
            and logs the outcome (success or error).
    """

    channel_id, message_id, lang = await get_status_message()
    if not channel_id or not message_id or not lang:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    try:
        message = await channel.fetch_message(message_id)
        embed = await build_status_embed(lang=lang)
        await message.edit(embed=embed)
        logging.debug("✅ Status embed updated")
    except Exception as e:
        logging.error(f"❌ Failed to update status embed: {e}")


async def check_maintenance(interaction: discord.Interaction, lang: str) -> bool:
    
    """ Validates if the bot is currently available or restricted due to an active maintenance state.

    This function triggers an update of the maintenance state and checks if it is currently 
    "active". If maintenance is ongoing, it blocks the interaction and informs the user 
    via an ephemeral message; otherwise, it allows the command execution to proceed.

    Args:
        interaction (discord.Interaction): The interaction object used to send the notification if blocked.

    Returns:
        bool: True if the bot is operational and the command can proceed; 
            False if maintenance is active and the interaction has been blocked.
    """
    
    state, status = await update_maintenance_state_if_needed()

    if state != "active":
        return True

    msg = status.get("maintenance_message") or "🛠️ Bot in manutenzione"
    await interaction.response.send_message(
        
        t(lang=lang,
            key="maintenance_active_message", msg=msg
        ),
        ephemeral=True
    )
    logging.debug(f"Interaction blocked due to active maintenance for {interaction.user.name}")
    return False


async def check_user_security(interaction: discord.Interaction) -> bool:
    
    """ Performs a multi-layered security and availability check for incoming interactions.

    This function coordinates the global access logic by allowing administrators 
    to bypass restrictions, verifying if the bot is in maintenance mode, and 
    checking the user's ban status. It ensures that only authorized and non-restricted 
    users can interact with the bot's features within a guild context.

    Args:
        interaction (discord.Interaction): The interaction object representing the command invocation.

    Returns:
        bool: True if the user passes all security layers or is an administrator; 
            False if the interaction is blocked due to maintenance or a ban.
    """
    
    if not interaction.guild:
        return True

    member = interaction.user

    uex_manager_role = discord.utils.get(member.roles, name="UEX Manager")
    if uex_manager_role:
        logging.debug(f"Admin bypass: {member.name}")
        return True

    if not await check_maintenance(interaction, lang):
        return False

    banned, reason = await ban.is_banned(member.id)
    if banned:
        lang = await sessions.resolve_and_store_language(interaction)
        await interaction.response.send_message(
            f"❌ {t(lang, 'access_denied_ban', reason=reason)}",
            ephemeral=True
        )
        logging.debug(f"User {member.name} blocked: banned (reason={reason})")
        return False

    return True


def start_status_task(bot: discord.Client):

    """ Initiates a background task that periodically synchronizes the bot's status.

    This function defines and starts an asynchronous loop that executes every 30 seconds. 
    During each cycle, it updates the internal maintenance state and refreshes the 
    public status embed. It includes error handling to ensure that exceptions within 
    individual cycles do not terminate the entire background process.

    Args:
        bot (discord.Client): The bot instance required to perform message edits and 
                            state updates.

    Returns:
        None: The function starts the loop as a background process and returns immediately.
    """

    @tasks.loop(seconds=30)
    async def status_loop():
        try:
            
            await update_maintenance_state_if_needed()
            await update_status_message(bot)
        except Exception as e:
            logging.exception(f"❌ Error in status_loop: {e}")

    status_loop.start()
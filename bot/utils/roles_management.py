import discord
from utils.i18n import t
import db.sessions as sessions
import db.banned as ban
from discord import app_commands
from logger import logging



def has_uex_manager_role():
    
    """ A decorator check that restricts command execution to users with the "UEX Manager" role.

    This function verifies the user's roles and, if the required role is not found, 
    resolves the user's language to send a localized ephemeral error message.

    Args:
        interaction (discord.Interaction): The interaction object representing the command invocation.

    Returns:
        bool: True if the user has the "UEX Manager" role, False otherwise (triggering an ephemeral response).
    """
    
    async def predicate(interaction: discord.Interaction) -> bool:
        # Verifica se l'utente ha il ruolo con quel nome esatto
        lang = await sessions.resolve_and_store_language(interaction)
        role = discord.utils.get(interaction.user.roles, name="UEX Manager")
        if role:
            return True
        
        # Se non ha il ruolo, inviamo un messaggio di errore privato
        await interaction.response.send_message(
            t(lang, "access_denied",),
            ephemeral=True
        )
        return False
    
    return app_commands.check(predicate)


async def assign_uex_user_role(interaction: discord.Interaction) -> bool:
    
    """ Assigns the "UEX user" role to a member if they are not banned and do not have administrative roles.

    This function checks if the user is a manager or banned before attempting to assign the role. 
    If the role is missing from the server, it logs an error but continues execution. 
    It is typically used to initialize user permissions during their first interaction.

    Args:
        interaction (discord.Interaction): The interaction object containing the guild and user context.

    Returns:
        bool: True if the role was assigned, already present, or if the user is a manager; 
            False if the user is banned and cannot receive the role.
    """
    
    guild = interaction.guild
    member = interaction.user

    check_manage = has_uex_manager_role()
    if check_manage:
        logging.debug(f"⚠️ User {member} has UEX Manager role, skipping UEX user role assignment")
        return True

    # 1. Check ban
    
    check_ban = await is_user_banned(interaction)
    if check_ban:
        logging.debug(f"🚫 User {member} is banned, cannot assign role")
        return False
    
    # 2. Get role
    role = discord.utils.get(guild.roles, name="UEX user")
    if not role:
        logging.error("❌ Role 'UEX user' not found")
        return True  # Role missing, but not a ban, so return True

    # 3. Assign role if missing
    if role not in member.roles:
        await member.add_roles(role, reason="First bot interaction")
        logging.debug(f"✅ Assigned 'UEX user' role to {member}")
    return True


async def is_user_banned(interaction: discord.Interaction) -> bool:
    
    """ Checks if a user is currently banned from using the bot's services.

    This function queries the ban system for the user's status. If a ban is active, 
    it resolves the user's language and sends a localized ephemeral message 
    detailing the access denial and the specific reason for the ban.

    Args:
        interaction (discord.Interaction): The interaction object representing the command invocation.

    Returns:
        bool: True if the user is banned (and an error message was sent), False otherwise.
    """
    
    member = interaction.user
    
    banned, reason = await ban.is_banned(member.id)
    lang = await sessions.resolve_and_store_language(interaction)

    if banned:
        logging.debug(f"🚫 User {member} is banned: {reason}")
        await interaction.response.send_message(
            t(lang, "access_denied_ban", reason=reason),
            ephemeral=True
        )
        return True
    
    return False
import discord
from utils.i18n import t
import db.sessions as sessions
import db.banned as ban
from discord import app_commands
from logger import logging

def has_uex_manager_role():
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
    """
    Returns False ONLY if user is banned.
    Otherwise assigns role if missing and returns True.
    """
    guild = interaction.guild
    member = interaction.user

    # 1. Check ban
    banned, motivation = await ban.is_banned(str(member.id))
    if banned:
        lang = await sessions.resolve_and_store_language(interaction)
        await interaction.response.send_message(
            t(lang, "user_banned", reason=motivation),
            ephemeral=True
        )
        return False

    # 2. Get role
    role = discord.utils.get(guild.roles, name="UEX user")
    if not role:
        logging.error("❌ Role 'UEX user' not found")
        return True  # non blocchiamo

    # 3. Assign role if missing
    if role not in member.roles:
        await member.add_roles(role, reason="First bot interaction")

    return True



async def is_user_banned(interaction: discord.Interaction) -> bool:
    
    member = interaction.user
    
    banned, reason = await ban.is_banned(member.id)
    lang = await sessions.resolve_and_store_language(interaction)

    if banned:
        await interaction.response.send_message(
            t(lang, "access_denied_ban", reason=reason),
            ephemeral=True
        )
        return False
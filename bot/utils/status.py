import discord
import logging
import db.banned as ban
from utils.i18n import t
from discord.ext import tasks
from datetime import datetime
import db.sessions as sessions
from db import sessions, banned as ban
from utils.status_storage import get_status_message, set_status_message
from db.maintenance import get_maintenance_status, get_status_maintenance

async def check_maintenance(interaction: discord.Interaction) -> bool:
    """
    Verifica se il bot è in manutenzione e blocca l'interazione se necessario.
    Restituisce True se l'interazione può continuare, False altrimenti.
    """
    status = await get_maintenance_status()  # Deve restituire dict con chiavi: maintenance, maintenance_message, maintenance_start, maintenance_end
    if not status or not status.get("maintenance"):
        return True  # manutenzione non attiva

    now = datetime.utcnow()
    start = status.get("maintenance_start")
    end = status.get("maintenance_end")

    # Controllo se la manutenzione è attiva nel range
    if start and end and not (start <= now <= end):
        logging.debug(f"[CHECK] Maintenance scheduled but not active: {start} - {end}")
        return True

    msg = status.get("maintenance_message") or "🛠️ Bot in manutenzione"
    await interaction.response.send_message(
        f"🚧 **Manutenzione attiva**\n{msg}",
        ephemeral=True
    )
    logging.info(f"[CHECK] Interaction blocked due to active maintenance for {interaction.user}")
    return False


async def check_user_security(interaction: discord.Interaction) -> bool:
    """
    Funzione principale di controllo sicurezza per slash commands, bottoni e modali.
    Ordine di verifica:
        1. Admin
        2. Manutenzione
        3. Utente bannato
    """
    if not interaction.guild:
        # Interazioni fuori da server (DM) non vengono bloccate
        return True

    member = interaction.user

    # 1️⃣ Controllo Admin
    uex_manager_role = discord.utils.get(member.roles, name="UEX Manager")
    if uex_manager_role:
        logging.info(f"[CHECK] Admin bypass: {member} is a UEX Manager")
        return True

    # 2️⃣ Controllo manutenzione
    if not await check_maintenance(interaction):
        return False

    # 3️⃣ Controllo utente bannato
    banned, reason = await ban.is_banned(member.id)
    if banned:
        lang = await sessions.resolve_and_store_language(interaction)
        await interaction.response.send_message(
            t(lang, "access_denied_ban", reason=reason),
            ephemeral=True
        )
        logging.info(f"[CHECK] User {member} blocked: banned (reason={reason})")
        return False

    # Tutto ok
    return True



async def build_status_embed() -> discord.Embed:
    status = await get_maintenance_status()
    now = datetime.now()

    embed = discord.Embed(
        title="🤖 UEX Bot Status",
        color=discord.Color.green(),
        timestamp=now
    )

    embed.add_field(
        name="🟢 Stato Bot",
        value="Online",
        inline=False
    )

    if status and status["maintenance"]:
        embed.color = discord.Color.orange()
        embed.add_field(
            name="🛠️ Manutenzione",
            value="ATTIVA",
            inline=False
        )
        embed.add_field(
            name="📅 Periodo",
            value=f"{status['maintenance_start']} → {status['maintenance_end']}",
            inline=False
        )
        embed.add_field(
            name="💬 Messaggio",
            value=status.get("maintenance_message", "—"),
            inline=False
        )
    else:
        embed.add_field(
            name="🛠️ Manutenzione",
            value="Nessuna",
            inline=False
        )

    embed.set_footer(text="Aggiornamento automatico ogni 5 minuti")
    return embed



async def update_status_message(bot: discord.Client):
    channel_id, message_id = get_status_message()
    if not channel_id or not message_id:
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    message = await channel.fetch_message(message_id)
    embed = await build_status_embed()
    await message.edit(embed=embed)
    logging.debug("✅ Status embed updated")
        
        

def start_status_task(bot):
    @tasks.loop(minutes=5)
    async def status_loop():
        await update_status_message(bot)

    status_loop.start()
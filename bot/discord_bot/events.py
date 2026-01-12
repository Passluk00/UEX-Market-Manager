import re
import discord
import logging
import aiohttp
from config import *
from utils.i18n import t
from db.pool import init_db
from config import TUNNEL_URL
from discord_bot.bot import bot
from utils.logo import show_logo
import db.sessions as db_session
from webserver.server import start_aiohttp_server
from services.notifications import send_startup_notification
from services.uex_api import fetch_and_store_uex_username, send_uex_message
from webserver.session_http import init_http

aiohttp_session = None



"""
Handles the bot's startup sequence.

This event performs several critical initialization steps:
1. Displays the startup logo.
2. Sends a startup notification via the notifications service.
3. Initializes the database connection pool.
4. Sets up a global aiohttp session for API requests.
5. Starts the internal webserver for webhooks.
6. Synchronizes global slash commands with Discord.
7. Re-registers persistent views (like the Open Thread button).

Returns:
    None
"""
@bot.event
async def on_ready():
    
    from discord_bot.views import OpenThreadButton

# 1. Show logo at startup
    show_logo()

# 2. log the start and send the startup notification
    logging.info(f"✅ Online bots like {bot.user}")
    await send_startup_notification()
    
    
# 3. Start Database
    
    try:
        await init_db()
        logging.info("✅ Database Ready.")
    except Exception as e:
        logging.critical(f"❌ DB not initialized: {e}")
        return

    await init_http()
    logging.info("🌐 aiohttp session initialized")

# 4. Start Server (Last fase)
    logging.info(f"📡 Base URL webhook: {TUNNEL_URL}")
    logging.info("🌐 Starting webhook server...")
    bot.loop.create_task(start_aiohttp_server())

# 5. Synchronizing Command
    try:
        await bot.tree.sync()
        logging.info("✅ Commands synchronized.")
    except Exception as e:
        logging.error(f"❌ Error synchronizing commands: {e}")
        
    bot.add_view(OpenThreadButton(lang=SYSTEM_LANGUAGE))



"""
Processes incoming messages to handle credential registration and notification replies.

The logic is split into two main flows:
1. **Credential Registration**: If a user sends a message containing 'bearer:', 'secret:', and 'username:', 
   the bot uses regex to extract and save these UEX API keys to the database.
2. **Notification Replies**: If a user replies to a bot-sent notification embed, the bot extracts 
   the negotiation hash from the embed and forwards the user's message to the UEX API.

Args:
    message (discord.Message): The message object sent by a user.

Returns:
    None
"""

# TODO modificare questa parte di codice rimuovere inserimento keys 


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not isinstance(message.channel, discord.Thread):
        return

    uid = str(message.author.id)
    content = message.content.strip()
    session = await db_session.get_user_session(uid)
   
    lang = await db_session.get_user_language(uid)
   
# ---------- Insert Bearer/Secret/Username keys ----------
    if not session.get("bearer_token") or not session.get("secret_key") or not session.get("username"):
        if all(x in content for x in ("bearer:", "secret:", "username:")):
            try:
                # Usa una regex robusta per estrarre i 3 campi
                match = re.search(
                    r"bearer:\s*([^\s]+)\s+secret:\s*([^\s]+)\s+username:\s*([^\s]+)",
                    content,
                    re.IGNORECASE
                )
                if not match:
                    await message.channel.send("❌ Formato non corretto. Usa: `bearer:<token> secret:<secret_key> username:<nick>`")
                    return

                bearer = match.group(1).strip().replace("<", "").replace(">", "")
                secret = match.group(2).strip().replace("<", "").replace(">", "")
                username_to_test = match.group(3).strip().replace("<", "").replace(">", "")
                
                await db_session.save_user_session(
                    user_id=uid,
                    thread_id=session.get("thread_id"),
                    uex_username=username_to_test,
                    bearer_token=bearer,
                    secret_key=secret
                )


# ---------- Retrieve and verify UEX username ----------
                try:
                    username = await fetch_and_store_uex_username(uid, secret, bearer, username_to_test, aiohttp_session)
                    if username:
                        await message.channel.send(t(lang, "credentials_saved", username=username),)
                    else:
                        await message.channel.send(t(lang, "credentials_saved_error"),)
                except Exception as e:
                    logging.warning(f"⚠️ Error fetching username UEX for {uid}: {e}")
                    await message.channel.send(t(lang, "credentials_saved_error"),)

            except Exception as e: 
                logging.exception(f"❌ Error parsing user credentials {uid}: {e}")
                await message.channel.send(t(lang, "credentials_format_error"),)
        else:
            pass

# ---------- If the user is responding to a notification ----------
    if message.reference and message.reference.resolved:
        replied_msg = message.reference.resolved

# ---------- Get the notification hash from the embed ----------
        embed = replied_msg.embeds[0] if replied_msg.embeds else None
        notif_hash = None

        if embed and embed.description:
            match = re.search(r"/hash/([a-f0-9-]+)", embed.description)
            if match:
                notif_hash = match.group(1)

        if not notif_hash:
            await message.channel.send(t(lang, "hash_not_found"),)
            return

        try:
            
            ok, error = await send_uex_message(
                        session=aiohttp_session,
                        bearer_token=session['bearer_token'],
                        secret_key=session["secret_key"],
                        notif_hash=hash,
                        message=message
                    )
            
            if ok:
                embed = discord.Embed(
                    title=t(lang, "embed.reply_sent.title"),
                    description=t(
                        lang,
                        "embed.reply_sent.description",
                        message=content
                    ),
                    color=discord.Color.green()
                )
                embed.add_field(
                    name=t(lang, "embed.reply_sent.negotiation"),
                    value=t(
                        lang,
                        "embed.reply_sent.link",
                        hash=notif_hash
                    ),
                    inline=False
                )
                embed.set_footer(text=t(lang, "add_footer"))

                await message.channel.send(embed=embed)

            else:
                
                await message.channel.send(t(lang,"errors.uex_send_failed",error=error))
                
        except:
            logging.info(t(lang,"errors.uex_send_failed",error=error))

    await bot.process_commands(message)



"""
Cleans up the database when a Discord thread is deleted.

Automatically removes all user sessions associated with the deleted thread ID 
to ensure data consistency and prevent orphaned sessions.

Args:
    thread (discord.Thread): The thread object that was deleted.

Returns:
    None
"""
@bot.event
async def on_thread_delete(thread: discord.Thread):
    """
    When a thread is deleted, it deletes all associated sessions
    in the DB for users connected to that thread.
    """
    try:
        removed_count = await db_session.remove_sessions_by_thread(thread.id)

        if removed_count:
            logging.info(
                t(
                    SYSTEM_LANGUAGE,
                    "thread.deleted_sessions",
                    count=removed_count,
                    thread_id=thread.id
                )
            )
    except Exception as e:
        logging.exception(t(SYSTEM_LANGUAGE, "thread.delete_error", thread_id=thread.id, error=e))



"""
Removes a specific user's session when they leave a Discord thread.

Ensures that if a user manually leaves or is removed from a negotiation thread, 
their session data is cleared from the database.

Args:
    thread (discord.Thread): The thread the member left.
    member (discord.Member): The member who left the thread.

Returns:
    None
"""
@bot.event
async def on_thread_member_remove(thread: discord.Thread, member: discord.Member):
    """
    When a user leaves a thread, their session is removed from the database
    if it was associated with that thread.
    """
    try:
        removed = await db_session.remove_user_session(str(member.id))

        if removed:
            logging.info(
                t(
                    SYSTEM_LANGUAGE,
                    "thread.user_left",
                    user_id=member.id,
                    thread_id=thread.id
                )
            )
    except Exception as e:
        logging.exception(
            t(SYSTEM_LANGUAGE, "thread.user_leave_error", user_id=member.id, thread_id=thread.id, error=e)
        )

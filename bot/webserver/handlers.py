import json
import logging
import discord
from utils.i18n import t
from db.sessions import *
from db.negotiations import *
from discord_bot.bot import bot
from services.notifications import *
import discord_bot.events as devents
from utils.text_cleaner import clean_text
from services.uex_api import send_uex_message


"""
Processes unified incoming webhooks for various event types (negotiations, replies, completions).

Args:
    request (aiohttp.web.Request): The incoming HTTP request object containing the JSON payload.
    event_type (str): The type of event triggered (e.g., 'negotiation_started', 'user_reply').
    user_id (str): The unique identifier of the user associated with the webhook.

Returns:
    dict: A dictionary containing the 'status' (HTTP code) and a 'text' message describing the outcome.
"""
async def handle_webhook_unificato(request, event_type: str, user_id: str):
    try:
        body = await request.text()
        data = json.loads(body) if body else {}
        
        lang = await get_user_language(user_id)
        
        if event_type == "negotiation_started":
            
            seller = data.get("listing_owner_username")
            buyer = data.get("client_username")
            hash = data.get("negotiation_hash")

            await save_negotiation_link(
                    hash,
                    buyer,
                    seller
                )
            
# ------- Retrieve user thread -------
            thread_id = await get_user_thread_id(str(user_id))
            if not thread_id:
                logging.warning(f"⚠️ No thread found for User: {seller}")
                return {"status": 404, "text": "User_thread_id not found"}
            
# ------- Retrieve Thread Seller -------
            thread = bot.get_channel( thread_id )
            if not thread:
                logging.warning(f"⚠️ No thread found for Seller: {seller}")
                return {"status": 404, "text": "thread not found"}
            
# ------- Notification to Seller of a New Deal -------
            embed = discord.Embed(
                title=t(lang, "embed.negotiation_started.title"),
                description=t(
                    lang, 
                    "embed.negotiation_started.description",
                    buyer=buyer,
                    title=data.get("listing_title", "—"),
                    hash=hash
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text=t(lang, "embed.footer"))
            await thread.send(embed=embed)
            

            enabled, message = await get_user_welcome_message(user_id)            
            if enabled and message:
                
                bearer, key = await get_user_keys(user_id)
                
                ok, error = await send_uex_message(
                        session=devents.aiohttp_session,
                        bearer_token=bearer,
                        secret_key=key,
                        notif_hash=hash,
                        message=message
                    )
                            
                if ok:
                    
                    embed=discord.Embed(
                            title=t(lang, "embed.welcome.title"),
                            description=message,
                            color=discord.Color.purple()
                        )
                    embed.set_footer(text=t(lang, "embed.footer"))
                    await thread.send(embed=embed)            
                
                else:
                    logging.warning(f"⚠️ error sending welcome message for user_id={user_id}: {error}")
            else:
                logging.error("he does not have the consent to send the message or the message is missing")
            
            
# ------- Case 2: Reply message -------
        elif event_type == "user_reply":
            
            seller = data.get("listing_owner_username")
            user = data.get("client_username")
            hash = data.get("negotiation_hash")

            link = await get_negotiation_link(hash)
            if not link:
                return {"status": 404, "text": "negotiation link not found"}
            
            if user == None:
                logging.warning(f"Invalid Username")
                return {"status": 404, "text": "Invalid Username"}
            
            

            if user == seller:
                
                buyer_username = link.get("buyer_id")
                
                session_buyer = await find_session_by_username(buyer_username)
                if not session_buyer:
                    logging.warning(f"⚠️ Buyer_Session not found")
                    return {"status": 404, "text": "Buyer_Sessions not found"}
                
                
                buyer_thread_id = session_buyer.get("thread_id")
                if not buyer_thread_id: 
                    logging.warning(f"⚠️ Buyer_Thread_Id not found")
                    return {"status": 404, "text": "Buyer_thread_id not found"}
                
                
# -------- Retrieve Thread Buyer ----------
                thread = bot.get_channel( buyer_thread_id )
                if not thread:
                    logging.warning(f"⚠️ Thread not found for seller: {seller}")
                    return {"status": 404, "text": "thread not found"}
                
                
                
# -------- Notify Buyer of a new Notification ---------
                embed = discord.Embed(
                    title=t(lang, "embed.new_message.title"),
                    description=t(lang, 
                        "embed.new_message.description",
                        author=user,
                        message=clean_text(data.get("message", "")),
                        title=data.get("listing_title", "—"),
                        hash=hash
                    ),
                    color=discord.Color.gold()
                )
                embed.set_footer(text=t(lang, "embed.footer"))
                await thread.send(embed=embed)

            
            
            elif user != seller:
                
# -------- Recover user session --------
                thread_id = await get_user_thread_id(str(user_id))
                if not thread_id:
                    logging.warning(f"⚠️No Thread_id Found for Seller: {seller}")
                    return {"status": 404, "text": "Seller_thread_id not found"}
                
# -------- Recover Thread Seller --------
                thread = bot.get_channel( thread_id )
                if not thread:
                    logging.warning(f"⚠️ Thread not found for Seller: {seller}")
                    return {"status": 404, "text": "thread not found"}
                
                
# -------- Notice to Seller of a New Notification --------
                embed = discord.Embed(
                    title=t(lang, "embed.new_message.title"),
                    description=t(lang, 
                        "embed.new_message.description",
                        author=user,
                        message=data.get("message", ""),
                        title=data.get("listing_title", "—"),
                        hash=hash
                    ),
                    color=discord.Color.gold()
                )
                embed.set_footer(text=t(lang, "embed.footer"))
                await thread.send(embed=embed)
                
            else:
                logging.warning(f"⚠️ Username '{user}' does not match either the buyer or the seller for hash={hash}")
                return {"status": 400, "text": "Unknown message source"}
            
            
# -------- Case 3: Negotiation terminated --------
        elif event_type in ("negotiation_completed_client", "negotiation_completed_advertiser"):
            hash = data.get("negotiation_hash")
            seller = data.get("listing_owner_username")
            
# -------- Recover user session --------
            thread_id = await get_user_thread_id(str(user_id))
            if not thread_id:
                logging.warning(f"⚠️ No Thread_id Found for Seller: {seller}")
                return {"status": 404, "text": "Seller_thread_id not found"}
            
# -------- Recover Thread Seller --------
            thread = bot.get_channel( thread_id )
            if not thread:
                logging.warning(f"⚠️ Thread not found for Seller: {seller}")
                return {"status": 404, "text": "thread not found"}
        
            await delete_negotiation_link(hash)
            embed = discord.Embed(
                title=t(lang, 
                        "embed.negotiation_completed.title",
                        user=data.get("client_username", "—")
                ),
                description=t(lang, 
                    "embed.negotiation_completed.description",
                    title=data.get("listing_title", "—"),
                    stars=data.get("rating_stars", 0),
                    comment=data.get("rating_comments", "—"),
                    hash=hash
                ),
                color=discord.Color.red()
            )
            embed.set_footer(text=t(lang, "embed.footer"))
            await thread.send(embed=embed)
            
        
        
        else:
            
# -------- Recover user session --------
            thread_id = await get_user_thread_id(str(user_id))
            if not thread_id:
                logging.warning(f"⚠️ No Thread_id Found for Seller: {seller}")
                return {"status": 404, "text": "Seller_thread_id not found"}
            
# -------- Recover Thread Seller --------
            thread = bot.get_channel( thread_id )
            if not thread:
                logging.warning(f"⚠️ Thread not found for Seller: {seller}")
                return {"status": 404, "text": "thread not found"}
            
# -------- Notice to Seller Error --------
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_footer(
                text=f"Made with love by Passluk"
            )
            embed.title = f"ℹ️ Evento: {event_type}"
            embed.description = json.dumps(data, indent=2)
            await thread.send(embed=embed)

        logging.info(f"✅ Webhook successfully processed for event='{event_type}' → user_id={user_id}")
        return {"status": 200, "text": "Webhook processed"}

    except Exception as e:
        logging.exception(f"💥 Unified webhook_handle error: {e}")
        return {"status": 500, "text": f"internal error: {e}"}


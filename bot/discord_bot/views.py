import discord
import aiohttp
import logging
import dateparser
from utils.i18n import t
from config import TUNNEL_URL
import db.sessions as sessions
from discord import ui
from datetime import datetime, timezone
from utils.status import check_user_security
from services.uex_api import fetch_and_store_uex_username
from db.maintenance import set_maintenance
from utils.status import update_status_message






class StatusView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        
class MaintenanceModal(ui.Modal):
    def __init__(self, lang: str, bot_instance):
        super().__init__(title=t(lang, "modal_maintenance_title"))
        self.lang = lang
        self.bot = bot_instance
        
        
        self.message_input = ui.TextInput(
            label=t(lang, "modal_maintenance_message_label"),
            placeholder=t(lang, "modal_maintenance_message_placeholder"),
            style=discord.TextStyle.long,
            required=True,
        )

        self.start_input = ui.TextInput(
            label=t(lang, "modal_maintenance_start_label"),
            placeholder=t(lang, "modal_maintenance_start_placeholder"),
            default=t(lang, "modal_maintenance.now_keyword"),
            required=True,
        )

        self.end_input = ui.TextInput(
            label=t(lang, "modal_maintenance_end_label"),
            placeholder=t(lang, "modal_maintenance_end_placeholder"),
            required=True,
        )
        
        self.add_item(self.message_input)
        self.add_item(self.start_input)
        self.add_item(self.end_input)
        
        
    async def on_submit(self, interaction: discord.Interaction):
        
        now = datetime.now(timezone.utc)
        end_dt = dateparser.parse(self.end_input.value, settings={'RELATIVE_BASE': now, 'PREFER_DATES_FROM': 'future'})
        
        ## Controllare questo codice se da errore
        
        start_dt = None
        
        if self.start_input.value.lower() == t(self.lang, "modal_maintenance.now_keyword").lower():
            start_dt = now
        else:
            start_dt = dateparser.parse(self.start_input.value, settings={'RELATIVE_BASE': now, 'PREFER_DATES_FROM': 'future'})
        
        
        if not start_dt or not end_dt:
            await interaction.response.send_message(
                t(self.lang, "modal_maintenance_invalid_date"),
                ephemeral=True
            )
            return
        
        try:
            
            await set_maintenance(
                status="scheduled",
                message=self.message_input.value,
                start=start_dt.astimezone(timezone.utc),    
                end=end_dt.astimezone(timezone.utc)
            )
            
            await update_status_message(bot=self.bot)
            
            await interaction.response.send_message(
                t(
                    lang=self.lang,
                    key="set_maintenance",
                    start=start_dt.strftime("%Y-%m-%d %H:%M UTC"),
                    end=end_dt.strftime("%Y-%m-%d %H:%M UTC"),
                    message=self.message_input.value
                ),
                ephemeral=True
            )
            
            logging.info(
                         t(lang=self.lang,
                           key="maintenance_set_by",
                           name=interaction.user.name,
                           start_dt=start_dt,
                           end_dt=end_dt
                           )
            )

        except Exception as e:
            logging.exception(f"❌ Error setting maintenance by admin {interaction.user.name}: {e}")
            await interaction.response.send_message(
                t(self.lang, "error_set_maintenance", e=e),
                ephemeral=True
            )


class DataModal(ui.Modal):
    def __init__(self, lang: str, user_id: str, aiohttp_session: aiohttp.ClientSession):
        super().__init__(title=t(lang, "modal_title"))
        self.lang = lang
        self.user_id = user_id
        self.aiohttp_session = aiohttp_session

        self.bearer_input = ui.TextInput(
            label=t(lang, "modal_label_bearer"),
            placeholder=t(lang, "modal_placeholder_bearer"),
            style=discord.TextStyle.short,
            required=True,
            max_length=50
        )

        self.secret_input = ui.TextInput(
            label=t(lang, "modal_label_secret_key"),
            placeholder=t(lang, "modal_placeholder_secret_key"),
            style=discord.TextStyle.short,
            required=True,
            max_length=50
        )

        self.user_input = ui.TextInput(
            label=t(lang, "modal_label_username"),
            placeholder=t(lang, "modal_placeholder_username"),
            style=discord.TextStyle.short,
            required=False,
            max_length=50
        )

        self.add_item(self.bearer_input)
        self.add_item(self.secret_input)
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        
        sec = await check_user_security(interaction)
        if not sec:          
            return
        
        try:
            verified_username = await fetch_and_store_uex_username(
                user_id=self.user_id,
                bearer_token=self.bearer_input.value,
                secret_key=self.secret_input.value,
                username_guess=self.user_input.value,
                session=self.aiohttp_session
            )

            if not verified_username:
                await interaction.response.send_message(
                    t(self.lang, "modal_invalid_username"),
                    ephemeral=True
                )
                return

            await sessions.save_user_session(
                user_id=self.user_id,
                bearer_token=self.bearer_input.value,
                secret_key=self.secret_input.value,
                uex_username=verified_username
            )

            await interaction.response.send_message(
                t(self.lang, "modal_success_verified", username=verified_username),
                ephemeral=True
            )

        except Exception:
            logging.exception(f"❌ Errore submit modal user {self.user_id}")
            await interaction.response.send_message(
                t(self.lang, "generic_error"),
                ephemeral=True
            )


class SetupTutorialView(ui.View):
    
    def __init__(self, lang: str, user_id: str, username: str):
        from webserver.session_http import get_http_session
        super().__init__(timeout=None)
        self.lang = lang
        self.user_id = user_id
        self.username = username
        self.current_page = 0
        self.total_pages = 3
        self.aiohttp_session = get_http_session()

        # Button to open the modal
        self.data_button = ui.Button(
            label=t(lang, "guide_button_insert"),
            style=discord.ButtonStyle.green,
            custom_id="insert_data_button"
        )
        self.data_button.callback = self.open_modal

        # Call update_buttons only after the button exists
        self.update_buttons()

    def create_embed(self):
        embed = discord.Embed(color=discord.Color.blurple())

        if self.current_page == 0:
            embed.title = f"👋 {t(self.lang, 'guide_welcome_title')}"
            embed.description = t(self.lang, 'guide_welcome_desc', username=self.username)
            embed.set_thumbnail(url="https://uexcorp.space/favicon.ico")

        elif self.current_page == 1:
            embed.title = f"📝 {t(self.lang, 'guide_input_data_title')}"
            embed.description = t(self.lang, 'guide_keys_desc')


        elif self.current_page == 2:
            embed.title = f"🔗 {t(self.lang, 'guide_webhook_title')}"
            embed.description = t(self.lang, 'guide_webhook_desc')

            base = f"{TUNNEL_URL}/webhook"
            embed.add_field(name=t(self.lang, "guide_negotiation_started"), value=f"`{base}/negotiation_started/{self.user_id}`", inline=False)
            embed.add_field(name=t(self.lang, "guide_negotiation_adv"), value=f"`{base}/negotiation_completed_advertiser/{self.user_id}`", inline=False)
            embed.add_field(name=t(self.lang, "guide_negotiation_cli"), value=f"`{base}/negotiation_completed_client/{self.user_id}`", inline=False)
            embed.add_field(name=t(self.lang, "guide_reply"), value=f"`{base}/user_reply/{self.user_id}`", inline=False)
            embed.add_field(name="✅", value=t(self.lang, "guide_save_note"), inline=False)

        embed.set_footer(text=t(self.lang, "guide_footer_page", current=self.current_page + 1, total=self.total_pages))
        return embed

    def update_buttons(self):
        # Disable border arrows
        self.prev_page.disabled = (self.current_page == 0)
        self.next_page.disabled = (self.current_page == self.total_pages - 1)

        # Show data button only on page 1
        if self.current_page == 1:
            if self.data_button not in self.children:
                # I insert the button between the arrows: first I remove all the arrows and recreate them in order
                self.clear_items()
                self.add_item(self.prev_page)
                self.add_item(self.data_button)
                self.add_item(self.next_page)
        else:
            if self.data_button in self.children:
                self.remove_item(self.data_button)

    async def open_modal(self, interaction: discord.Interaction, ):
        await interaction.response.send_modal(DataModal(self.lang, interaction.user.id, self.aiohttp_session))

    # Left arrow button
    @ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button):
        
        sec = await check_user_security(interaction)
        if not sec:          
            return
        
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    # Right arrow button
    @ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        
        sec = await check_user_security(interaction)
        if not sec:          
            return
        
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


class OpenThreadButton(ui.View):
    def __init__(self, lang):
        super().__init__(timeout=None)
        self.lang = lang

    @ui.button(label="Open Chat", style=discord.ButtonStyle.primary, custom_id="open_thread_button")
    async def open_thread(self, interaction: discord.Interaction, button: ui.Button):
        

        sec = await check_user_security(interaction)
        if not sec:          
            return
        
        
        lang = await sessions.resolve_and_store_language(interaction)
        user_id = str(interaction.user.id)
        channel = interaction.channel

        try:
            thread_id = await sessions.get_user_thread_id(user_id)
            if thread_id:
                try:
                    existing_thread = await interaction.client.fetch_channel(int(thread_id))
                    if existing_thread and not existing_thread.archived:
                        await interaction.response.send_message(t(lang, "already_active"), ephemeral=True)
                        return
                except discord.NotFound:
                    await sessions.remove_user_session(user_id)

            #1. Creating a private thread
            thread = await channel.create_thread(
                name=f"Chat {interaction.user.name.capitalize()}",
                type=discord.ChannelType.private_thread,
                invitable=False,
            )
            await thread.add_user(interaction.user)

            # 2. Save session
            await sessions.save_user_session(
                user_id=user_id,
                thread_id=thread.id,
                language=lang
            )

            #3. Launch the Paginated Tutorial in the thread
            tutorial_view = SetupTutorialView(lang=lang, user_id=user_id, username=interaction.user.name)
            await thread.send(
                content=f"👋 {interaction.user.mention}", 
                embed=tutorial_view.create_embed(), 
                view=tutorial_view
            )

            #4. Feedback to the user on the button
            await interaction.response.send_message(t(lang, "thread_created"), ephemeral=True)

        except Exception as e:
            logging.error(f"❌ Error on open_thread: {e}")
            await interaction.response.send_message(t(lang, "generic_error"), ephemeral=True)
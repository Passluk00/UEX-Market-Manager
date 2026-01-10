import discord
import aiohttp
from discord import ui
import logging
from utils.i18n import t
from config import TUNNEL_URL
import db.sessions as sessions
from services.uex_api import fetch_and_store_uex_username



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


        
        


# --- View guida con bottone al centro delle frecce ---
class SetupTutorialView(ui.View):
    def __init__(self, lang: str, user_id: str, username: str, aiohttp_session: aiohttp.ClientSession):
        super().__init__(timeout=None)
        self.lang = lang
        self.user_id = user_id
        self.username = username
        self.current_page = 0
        self.total_pages = 3
        self.aiohttp_session = aiohttp_session

        # Bottone per aprire il modal
        self.data_button = ui.Button(
            label=t(lang, "guide_button_insert"),
            style=discord.ButtonStyle.green,
            custom_id="insert_data_button"
        )
        self.data_button.callback = self.open_modal

        # Chiama update_buttons solo dopo che il bottone esiste
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
        # Disabilita le frecce ai bordi
        self.prev_page.disabled = (self.current_page == 0)
        self.next_page.disabled = (self.current_page == self.total_pages - 1)

        # Mostra il bottone dati solo a pagina 1
        if self.current_page == 1:
            if self.data_button not in self.children:
                # Inserisco il bottone tra le frecce: prima rimuovo tutte le frecce e li ricreo nell'ordine
                self.clear_items()
                self.add_item(self.prev_page)
                self.add_item(self.data_button)
                self.add_item(self.next_page)
        else:
            if self.data_button in self.children:
                self.remove_item(self.data_button)

    async def open_modal(self, interaction: discord.Interaction, ):
        await interaction.response.send_modal(DataModal(self.lang, interaction.user.id, self.aiohttp_session))

    # Bottone freccia sinistra
    @ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    # Bottone freccia destra
    @ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

class OpenThreadButton(ui.View):
    def __init__(self, lang, aiohttp_session: aiohttp.ClientSession):
        super().__init__(timeout=None)
        self.lang = lang
        self.aiohttp_session = aiohttp_session

    @ui.button(label="Open Chat", style=discord.ButtonStyle.primary, custom_id="open_thread_button")
    async def open_thread(self, interaction: discord.Interaction, button: ui.Button):
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
            tutorial_view = SetupTutorialView(lang=lang, user_id=user_id, username=interaction.user.name, aiohttp_session=self.aiohttp_session)
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
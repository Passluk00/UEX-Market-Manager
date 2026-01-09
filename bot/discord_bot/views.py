import discord
from discord import ui
import logging
from utils.i18n import t
from config import TUNNEL_URL
import db.sessions as sessions

class SetupTutorialView(ui.View):
    
    """
    Gestisce un tutorial interattivo a pagine dentro un singolo Embed.
    """
    def __init__(self, lang: str, user_id: str, username: str):
        super().__init__(timeout=None)
        self.lang = lang
        self.user_id = user_id
        self.username = username
        self.current_page = 0
        self.total_pages = 3
        self.update_buttons()

    def create_embed(self):
        embed = discord.Embed(color=discord.Color.blurple())
        
        if self.current_page == 0:
            embed.title = f"👋 {t(self.lang, 'guide_welcome_title')}"
            embed.description = t(self.lang, 'guide_welcome_desc', username=self.username)
            embed.set_thumbnail(url="https://uexcorp.space/favicon.ico")

        elif self.current_page == 1:
            embed.title = f"🔑 {t(self.lang, 'guide_keys_title')}"
            embed.description = t(self.lang, 'guide_keys_desc')

        elif self.current_page == 2:
            embed.title = f"🔗 {t(self.lang, 'guide_webhook_title')}"
            embed.description = t(self.lang, 'guide_webhook_desc')
            
            # Generazione URL dinamici
            base = f"{TUNNEL_URL}/webhook"
            embed.add_field(name=t(self.lang, "guide_negotiation_started"), value=f"`{base}/negotiation_started/{self.user_id}`", inline=False)
            embed.add_field(name=t(self.lang, "guide_negotiation_adv"), value=f"`{base}/negotiation_completed_advertiser/{self.user_id}`", inline=False)
            embed.add_field(name=t(self.lang, "guide_negotiation_cli"), value=f"`{base}/negotiation_completed_client/{self.user_id}`", inline=False)
            embed.add_field(name=t(self.lang, "guide_reply"), value=f"`{base}/user_reply/{self.user_id}`", inline=False)
            
            embed.add_field(name="✅", value=t(self.lang, "guide_save_note"), inline=False)

        embed.set_footer(text=t(self.lang, "guide_footer_page", current=self.current_page + 1, total=self.total_pages))
        return embed

    def update_buttons(self):
        """Disable buttons at the edges of the guide."""
        self.prev_page.disabled = (self.current_page == 0)
        self.next_page.disabled = (self.current_page == self.total_pages - 1)

    @ui.button(label="⬅️", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        

class OpenThreadButton(ui.View):
    def __init__(self, lang):
        super().__init__(timeout=None)
        self.lang = lang

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
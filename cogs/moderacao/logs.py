
import discord
from discord.ext import commands
from discord import ui, Interaction, TextStyle, ButtonStyle
from supabase import Client
import logging
from datetime import datetime

# --- Funções Auxiliares de Banco de Dados ---
async def get_log_config(supabase: Client, guild_id: int) -> dict:
    try:
        response = supabase.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
        if response.data:
            return response.data[0].get('settings', {}).get('logs', {})
    except Exception as e:
        logging.error(f"Erro ao buscar config de logs para o servidor {guild_id}: {e}")
    return {}

# --- Modais de Configuração Específicos ---

class LogChannelModal(ui.Modal, title="Configurar Canal de Logs"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        enabled_value = "sim" if config.get("enabled") else "não"
        self.add_item(ui.TextInput(label="Ativar sistema? (sim/não)", custom_id="enabled", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="ID do Canal de Anúncios", custom_id="log_channel_id", default=str(config.get("log_channel_id", ""))))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "log_channel_id": int(self.children[1].value)
            }
            
            def update_settings(settings):
                if 'logs' not in settings: settings['logs'] = {}
                settings['logs'].update(data)

            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
            if success:
                await interaction.followup.send("✅ Canal e status dos logs atualizados!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ocorreu um erro inesperado ao salvar.", ephemeral=True)
        except (ValueError, TypeError):
            await interaction.followup.send("❌ Erro: O ID do canal deve ser um número válido.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao submeter LogChannelModal: {e}")
            await interaction.followup.send(f"❌ Ocorreu um erro inesperado ao salvar.", ephemeral=True)

class LogJoinModal(ui.Modal, title="Configurar Mensagem de Entrada"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        placeholders = "Use {user.mention}, {user.name}, etc."
        self.add_item(ui.TextInput(label="Mensagem de Entrada", style=TextStyle.paragraph, custom_id="join_message", default=config.get("join_message", ""), placeholder=placeholders))
        self.add_item(ui.TextInput(label="URL da Imagem de Entrada", custom_id="join_image_url", default=config.get("join_image_url", ""), placeholder="https://exemplo.com/img.png", required=False))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            data = {"join_message": self.children[0].value, "join_image_url": self.children[1].value}
            
            def update_settings(settings):
                if 'logs' not in settings: settings['logs'] = {}
                settings['logs'].update(data)

            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações de entrada atualizadas!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ocorreu um erro inesperado ao salvar.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao submeter LogJoinModal: {e}")
            await interaction.followup.send(f"❌ Ocorreu um erro inesperado ao salvar.", ephemeral=True)

class LogLeaveModal(ui.Modal, title="Configurar Mensagem de Saída"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        placeholders = "Use {user.name}, {guild.name}, etc."
        self.add_item(ui.TextInput(label="Mensagem de Saída", style=TextStyle.paragraph, custom_id="leave_message", default=config.get("leave_message", ""), placeholder=placeholders, required=False))
        self.add_item(ui.TextInput(label="URL da Imagem de Saída", custom_id="leave_image_url", default=config.get("leave_image_url", ""), placeholder="https://exemplo.com/img.png", required=False))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            data = {"leave_message": self.children[0].value, "leave_image_url": self.children[1].value}
            
            def update_settings(settings):
                if 'logs' not in settings: settings['logs'] = {}
                settings['logs'].update(data)

            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações de saída atualizadas!", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Ocorreu um erro inesperado ao salvar.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao submeter LogLeaveModal: {e}")
            await interaction.followup.send(f"❌ Ocorreu um erro inesperado ao salvar.", ephemeral=True)


# --- View com os Botões de Ação ---

class LogSettingsView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def get_config_and_show_modal(self, interaction: Interaction, modal_class):
        config = await get_log_config(self.bot.supabase_client, interaction.guild.id)
        modal = modal_class(self.bot, config)
        await interaction.response.send_modal(modal)

    @ui.button(label="Canal e Status", style=ButtonStyle.primary, emoji="⚙️")
    async def channel_button(self, interaction: Interaction, button: ui.Button):
        await self.get_config_and_show_modal(interaction, LogChannelModal)

    @ui.button(label="Mensagem de Entrada", style=ButtonStyle.green, emoji="📥")
    async def join_button(self, interaction: Interaction, button: ui.Button):
        await self.get_config_and_show_modal(interaction, LogJoinModal)

    @ui.button(label="Mensagem de Saída", style=ButtonStyle.red, emoji="📤")
    async def leave_button(self, interaction: Interaction, button: ui.Button):
        await self.get_config_and_show_modal(interaction, LogLeaveModal)

# --- Cog Principal ---
class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def format_message(self, template: str, member: discord.Member) -> str:
        if not template: return ""
        return template.replace("{user.mention}", member.mention) \
                       .replace("{user.name}", member.name) \
                       .replace("{user.id}", str(member.id)) \
                       .replace("{guild.name}", member.guild.name) \
                       .replace("{guild.member_count}", str(member.guild.member_count))

    async def send_log_embed(self, member: discord.Member, event_type: str):
        config = await get_log_config(self.bot.supabase_client, member.guild.id)
        if not config or not config.get("enabled"): return

        channel_id = config.get("log_channel_id")
        message_template = config.get(f"{event_type}_message")
        
        if not channel_id or not message_template: return
            
        channel = self.bot.get_channel(channel_id)
        if not channel: return

        image_url = config.get(f"{event_type}_image_url")
        formatted_message = self.format_message(message_template, member)
        color = discord.Color.green() if event_type == 'join' else discord.Color.red()

        embed = discord.Embed(description=formatted_message, color=color, timestamp=datetime.utcnow())
        embed.set_author(name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        if image_url: embed.set_image(url=image_url)
        embed.set_footer(text=f"Total de membros: {member.guild.member_count}")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            logging.error(f"Falha ao enviar log de entrada/saída no servidor {member.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.send_log_embed(member, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.send_log_embed(member, "leave")

async def setup(bot: commands.Bot):
    await bot.add_cog(Logs(bot))

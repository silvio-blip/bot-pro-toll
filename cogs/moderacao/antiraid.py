
import discord
from discord.ext import commands
from discord import ui, Interaction
from supabase import Client
import logging
from collections import deque
from datetime import datetime, timedelta

# --- Modal de Configuração ---

class AntiRaidConfigModal(ui.Modal, title="Configuração do Anti-Raid"):
    """Modal para configurar o sistema de Anti-Raid."""
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}

        enabled_value = "sim" if self.config.get("enabled") else "não"
        
        self.add_item(ui.TextInput(label="Ativar sistema?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="ID do Canal para Alertas", custom_id="alert_channel_id", placeholder="Cole o ID do canal de texto", default=str(self.config.get("alert_channel_id", ""))))
        self.add_item(ui.TextInput(label="Nº de entradas para alerta", custom_id="join_limit", placeholder="Ex: 10", default=str(self.config.get("join_limit", ""))))
        self.add_item(ui.TextInput(label="Janela de tempo (segundos)", custom_id="join_time_window", placeholder="Ex: 5", default=str(self.config.get("join_time_window", ""))))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        try:
            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "alert_channel_id": int(self.children[1].value),
                "join_limit": int(self.children[2].value),
                "join_time_window": int(self.children[3].value),
            }

            def update_settings(settings):
                settings['anti_raid'] = config_data

            success = await self.bot.get_and_update_server_settings(guild_id, update_settings)
            
            if success:
                await interaction.followup.send("✅ Configurações do Anti-Raid salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar as configurações. Verifique os valores.", ephemeral=True)

        except Exception as e:
            logging.error(f"Erro ao salvar config do Anti-Raid: {e}")
            await interaction.followup.send("❌ Erro ao salvar as configurações. Verifique os valores.", ephemeral=True)

# --- Cog Principal ---

class AntiRaid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase: Client = bot.supabase_client
        self.joins = {}

    async def get_server_config(self, guild_id: int) -> dict:
        try:
            response = self.supabase.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('anti_raid', {})
        except Exception as e:
            logging.error(f"Erro ao buscar config de anti-raid para o servidor {guild_id}: {e}")
        return {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return
        guild_id = member.guild.id
        config = await self.get_server_config(guild_id)
        if not config.get('enabled'): return

        now = datetime.utcnow()
        if guild_id not in self.joins:
            self.joins[guild_id] = deque()
        self.joins[guild_id].append(now)
        
        time_window = timedelta(seconds=config.get('join_time_window', 5))
        while self.joins[guild_id] and self.joins[guild_id][0] < now - time_window:
            self.joins[guild_id].popleft()
        
        if len(self.joins[guild_id]) >= config.get('join_limit', 10):
            try:
                alert_channel = self.bot.get_channel(config['alert_channel_id'])
                if alert_channel:
                    await alert_channel.send(
                        f"@here 🚨 **Alerta de Raid Detectado!** 🚨\n"
                        f"{len(self.joins[guild_id])} membros entraram nos últimos {time_window.seconds} segundos."
                    )
                self.joins[guild_id].clear()
            except Exception as e:
                logging.error(f"Erro ao enviar alerta de raid para o servidor {guild_id}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaid(bot))

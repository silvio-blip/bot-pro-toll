
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui, TextStyle
from supabase import Client
import logging
from datetime import datetime, timezone

# --- Modal de Configuração ---

class WarnsConfigModal(ui.Modal, title="Configuração do Sistema de Avisos"):
    """Modal para configurar o sistema de Avisos (Warns)."""
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        
        enabled_value = "sim" if self.config.get("enabled") else "não"

        self.add_item(ui.TextInput(label="Ativar sistema?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="Máximo de Avisos", custom_id="max_warns", placeholder="Ex: 3", default=str(self.config.get("max_warns", ""))))
        self.add_item(ui.TextInput(label="Ação Automática (kick/ban)", custom_id="action", placeholder="kick ou ban", default=self.config.get("action", ""), max_length=4))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        try:
            action_value = self.children[2].value.lower()
            if action_value not in ['kick', 'ban']:
                await interaction.followup.send("❌ Ação inválida. Use 'kick' ou 'ban'.", ephemeral=True)
                return

            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "max_warns": int(self.children[1].value),
                "action": action_value,
            }

            def update_settings(settings):
                settings['warns'] = config_data

            success = await self.bot.get_and_update_server_settings(guild_id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações do sistema de avisos salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar as configurações. Verifique os valores.", ephemeral=True)

        except Exception as e:
            logging.error(f"Erro ao submeter modal de Avisos: {e}")
            await interaction.followup.send("❌ Erro ao processar as configurações.", ephemeral=True)

# --- Cog Principal ---

class Warns(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase: Client = bot.supabase_client

    async def get_server_config(self, guild_id: int) -> dict:
        try:
            response = self.supabase.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('warns', {})
        except Exception as e:
            logging.error(f"Erro ao buscar config de warns para o servidor {guild_id}: {e}")
        return {}

    @app_commands.command(name="warn", description="Aplica uma advertência a um membro.")
    @app_commands.describe(membro="O membro a ser advertido.", motivo="O motivo da advertência.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: Interaction, membro: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)

        if membro.bot or membro.id == interaction.user.id:
            await interaction.followup.send("❌ Você não pode advertir bots ou a si mesmo.", ephemeral=True)
            return

        try:
            self.supabase.table("warnings").insert({
                "guild_id": interaction.guild.id,
                "warned_user_id": membro.id,
                "warned_user_name": membro.name,
                "moderator_user_id": interaction.user.id,
                "moderator_user_name": interaction.user.name,
                "reason": motivo,
                "warned_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            await interaction.followup.send(f"✅ {membro.mention} foi advertido. Motivo: '{motivo}'.", ephemeral=True)
            await self.check_auto_punishment(interaction, membro)

        except Exception as e:
            logging.error(f"Erro ao registrar advertência: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao registrar a advertência.", ephemeral=True)

    async def check_auto_punishment(self, interaction: Interaction, membro: discord.Member):
        config = await self.get_server_config(interaction.guild.id)
        if not config.get("enabled"): return

        max_warns = config.get("max_warns")
        action = config.get("action")

        try:
            warnings_count = len(self.supabase.table("warnings").select("id").eq("guild_id", interaction.guild.id).eq("warned_user_id", membro.id).execute().data)

            if warnings_count >= max_warns:
                punishment_reason = f"Atingiu o limite de {max_warns} advertências."
                await interaction.channel.send(f"🚨 {membro.mention} atingiu o limite de advertências e será punido.")
                
                if action == "kick":
                    await membro.kick(reason=punishment_reason)
                    await interaction.channel.send(f"👢 O usuário foi expulso do servidor.")
                elif action == "ban":
                    await membro.ban(reason=punishment_reason)
                    await interaction.channel.send(f"🔨 O usuário foi banido do servidor.")
                
                self.supabase.table("warnings").delete().eq("guild_id", interaction.guild.id).eq("warned_user_id", membro.id).execute()

        except Exception as e:
            logging.error(f"Erro no sistema de auto-punição: {e}")
            await interaction.channel.send("⚠️ Erro ao tentar aplicar a punição automática.")

    @warn.error
    async def on_warn_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ocorreu um erro inesperado.", ephemeral=True)
            logging.error(f"Erro não tratado no comando /warn: {error}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Warns(bot))

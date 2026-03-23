from discord.ext import commands
from discord import app_commands, Interaction, Permissions
import logging

class Admin(commands.Cog):
    """Cog para comandos administrativos e de dono do bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sync", description="[Admin] Força a sincronização dos comandos de barra com o Discord.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction: Interaction):
        """Sincroniza os comandos do bot com o Discord."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            synced = await self.bot.tree.sync()
            logging.info(f"Sincronização manual iniciada por {interaction.user}.")
            await interaction.followup.send(f"✅ Sincronizados {len(synced)} comandos globalmente.", ephemeral=True)
        except Exception as e:
            logging.error(f"Falha na sincronização manual: {e}")
            await interaction.followup.send(f"❌ Falha ao sincronizar comandos. Verifique os logs do bot.", ephemeral=True)

    @sync.error
    async def sync_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Apenas administradores podem usar este comando.", ephemeral=True)
        else:
            logging.error(f"Erro inesperado no comando sync: {error}")
            await interaction.response.send_message("Ocorreu um erro ao tentar executar este comando.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Adiciona o cog Admin ao bot."""
    await bot.add_cog(Admin(bot))

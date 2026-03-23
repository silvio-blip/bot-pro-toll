
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class Lock(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lock", description="Tranca um canal, impedindo que membros enviem mensagens.")
    @app_commands.describe(canal="O canal que você deseja trancar. Se não for especificado, tranca o canal atual.", motivo="O motivo para trancar o canal.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: Interaction, canal: discord.TextChannel = None, motivo: str = "Nenhum motivo especificado."):
        """Tranca um canal, impedindo o envio de mensagens."""
        target_channel = canal or interaction.channel

        # Pega a permissão atual do cargo @everyone
        overwrite = target_channel.overwrites_for(interaction.guild.default_role)
        
        # Se já estiver trancado, não faz nada
        if overwrite.send_messages is False:
            await interaction.response.send_message(f"🔒 O canal {target_channel.mention} já está trancado.", ephemeral=True)
            return

        # Altera a permissão para negar o envio de mensagens
        overwrite.send_messages = False
        await target_channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        # Envia a confirmação e a mensagem no canal trancado
        await interaction.response.send_message(f"✅ O canal {target_channel.mention} foi trancado.", ephemeral=True)
        
        embed = discord.Embed(
            title="🔒 Canal Trancado",
            description=f"Este canal foi temporariamente desativado pela moderação.",
            color=discord.Color.red()
        )
        embed.add_field(name="Motivo", value=motivo, inline=False)
        await target_channel.send(embed=embed)

    @app_commands.command(name="unlock", description="Destranca um canal, permitindo que membros voltem a enviar mensagens.")
    @app_commands.describe(canal="O canal que você deseja destrancar. Se não for especificado, destranca o canal atual.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: Interaction, canal: discord.TextChannel = None):
        """Destranca um canal, permitindo o envio de mensagens."""
        target_channel = canal or interaction.channel

        overwrite = target_channel.overwrites_for(interaction.guild.default_role)

        # Se não estiver trancado, não faz nada
        if overwrite.send_messages is not False:
            await interaction.response.send_message(f"🔓 O canal {target_channel.mention} não está trancado.", ephemeral=True)
            return

        # Restaura a permissão padrão (ou permite, se não houver configuração)
        overwrite.send_messages = None # None herda da categoria/servidor, que geralmente é permitido
        await target_channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        await interaction.response.send_message(f"✅ O canal {target_channel.mention} foi destrancado.", ephemeral=True)
        
        embed = discord.Embed(
            title="🔓 Canal Destrancado",
            description="Este canal foi reaberto. Por favor, sigam as regras.",
            color=discord.Color.green()
        )
        await target_channel.send(embed=embed)

    @lock.error
    @unlock.error
    async def on_lock_unlock_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Você não tem permissão para gerenciar canais.", ephemeral=True)
        else:
            logging.error(f"Erro nos comandos de lock/unlock: {error}")
            await interaction.response.send_message("❌ Ocorreu um erro ao executar este comando.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Lock(bot))

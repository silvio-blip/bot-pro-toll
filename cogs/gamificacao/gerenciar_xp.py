
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class GerenciarXp(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gerenciar_xp", description="Adiciona ou remove XP de um usuário.")
    @app_commands.describe(usuario="O usuário para gerenciar o XP", acao="A ação a ser realizada", quantidade="A quantidade de XP")
    @app_commands.choices(acao=[
        app_commands.Choice(name="Adicionar", value="add"),
        app_commands.Choice(name="Remover", value="remove"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def gerenciar_xp(self, interaction: Interaction, usuario: discord.Member, acao: app_commands.Choice[str], quantidade: int):
        """Comando para administradores adicionarem ou removerem XP de um membro."""
        if quantidade <= 0:
            await interaction.response.send_message("❌ A quantidade deve ser um número positivo.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            xp_change = quantidade if acao.value == "add" else -quantidade
            action_text = "adicionados" if acao.value == "add" else "removidos"

            # Chama a função centralizada para atualizar o XP e recalcular o nível
            # O `is_message` é False porque esta não é uma XP ganha por mensagem
            new_level = await self.bot.update_xp(usuario, interaction.guild, xp_change, is_message=False)

            # Mensagem de confirmação
            await interaction.followup.send(f"✅ {quantidade} pontos de XP foram {action_text} com sucesso para {usuario.mention}.", ephemeral=True)

            # Se o usuário subiu de nível, envia mensagem por DM
            if new_level is not None:
                try:
                    await usuario.send(f"🎉 Parabéns {usuario.mention}, você alcançou o **Nível {new_level}** no servidor {interaction.guild.name}! 🎉")
                except discord.Forbidden:
                    pass

        except Exception as e:
            logging.error(f"Erro ao executar o comando /gerenciar_xp: {e}")
            await interaction.followup.send("Ocorreu um erro ao tentar modificar o XP do usuário.", ephemeral=True)
    
    @gerenciar_xp.error
    async def gerenciar_xp_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando. Apenas administradores podem usar.", ephemeral=True)
        else:
            logging.error(f"Erro no comando gerenciar_xp: {error}")
            await interaction.response.send_message("❌ Ocorreu um erro ao executar este comando.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GerenciarXp(bot))

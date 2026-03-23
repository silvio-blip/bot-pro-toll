
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

            # Se o usuário subiu de nível, envia uma mensagem pública
            if new_level is not None:
                try:
                    # Tenta enviar no canal da interação, se falhar, não faz nada
                    await interaction.channel.send(f"🎉 Parabéns {usuario.mention}, você foi promovido para o **Nível {new_level}**! 🎉")
                except discord.Forbidden:
                    logging.warning(f"Não foi possível anunciar o level up de {usuario.name} no canal {interaction.channel.name}.")

        except Exception as e:
            logging.error(f"Erro ao executar o comando /gerenciar_xp: {e}")
            await interaction.followup.send("Ocorreu um erro ao tentar modificar o XP do usuário.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GerenciarXp(bot))

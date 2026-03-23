import discord
from discord.ext import commands
from discord import app_commands, Interaction
import random

class DiceCommand(commands.Cog):
    """Cog para o comando de dado."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dado", description="Lança um dado com um número de lados especificado.")
    @app_commands.describe(lados="O número de lados que o dado deve ter.")
    async def dado(self, interaction: Interaction, lados: app_commands.Range[int, 2, 1000] = 6):
        """Lança um dado com um número de lados especificado (padrão 6)."""
        
        try:
            resultado = random.randint(1, lados)
            
            embed = discord.Embed(
                title="🎲 Rolagem de Dado 🎲",
                description=f"Você rolou um dado de **{lados}** lados.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Resultado", value=f"O dado caiu no número **{resultado}**!", inline=False)
            embed.set_footer(text=f"Comando solicitado por: {interaction.user.display_name}")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                f"Ocorreu um erro ao tentar rolar o dado: {e}", 
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DiceCommand(bot))

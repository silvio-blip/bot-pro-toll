import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class RankGeral(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rank_geral", description="Mostra o ranking de XP de todos os usuários do servidor.")
    async def rank_geral(self, interaction: Interaction):
        """Exibe o ranking de todos os membros do servidor."""
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id

        try:
            # Busca todos os perfis do servidor, agora incluindo o 'level'
            profiles_response = self.bot.supabase_client.table("gamification_profiles") \
                .select("user_name, xp, level") \
                .eq("guild_id", guild_id) \
                .order("xp", desc=True) \
                .limit(50) \
                .execute()

            if not profiles_response.data:
                await interaction.followup.send("Ninguém no servidor possui XP ainda.", ephemeral=True)
                return

            embed = discord.Embed(title=f"🏆 Ranking Geral de XP - {interaction.guild.name}", color=discord.Color.gold())
            
            description = ""
            for i, profile in enumerate(profiles_response.data, 1):
                user_name = profile.get('user_name', "Usuário Desconhecido")
                xp = profile.get('xp', 0)
                level = profile.get('level', 0)
                
                description += f"**{i}.** {user_name} - **Nível {level}** ({xp} XP)\n"

            # A CULPA FOI MINHA. CORRIGINDO A INDENTAÇÃO AQUI.
            if not description:
                await interaction.followup.send("Não foi possível gerar o ranking.", ephemeral=True)
                return

            embed.description = description
            embed.set_footer(text=f"Exibindo os top {len(profiles_response.data)} membros com mais XP.")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logging.error(f"Erro ao executar o comando /rank_geral: {e}")
            await interaction.followup.send("Ocorreu um erro ao buscar o ranking do servidor.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RankGeral(bot))
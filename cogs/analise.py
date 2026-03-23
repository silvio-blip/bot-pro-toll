
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import time
import json
import urllib.parse
from datetime import datetime
from collections import defaultdict
import logging

class Analise(commands.Cog):
    """Cog para análise de dados e estatísticas do servidor."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Verifica a latência do bot.")
    async def ping(self, interaction: Interaction):
        """Calcula e exibe a latência do bot."""
        start_time = time.time()
        api_latency = round(self.bot.latency * 1000)

        embed = discord.Embed(title="🏓 Pong!", description="Analisando latências...", color=discord.Color.greyple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

        end_time = time.time()
        full_latency = round((end_time - start_time) * 1000)

        new_embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
        new_embed.add_field(name="Latência da API", value=f"`{api_latency}ms`", inline=True)
        new_embed.add_field(name="Latência Completa", value=f"`{full_latency}ms`", inline=True)
        new_embed.set_footer(text="Latência completa = Tempo de envio + Resposta da API + Tempo de recebimento")
        await interaction.edit_original_response(embed=new_embed)

    @app_commands.command(name="top_atividade", description="Exibe o ranking de membros mais ativos por mensagens.")
    async def top_atividade(self, interaction: Interaction):
        """Exibe o ranking de atividade de mensagens do servidor."""
        await interaction.response.defer(ephemeral=False)
        try:
            response = self.bot.supabase_client.table("gamification_profiles").select("user_name", "message_count").eq("guild_id", interaction.guild.id).order("message_count", desc=True).limit(10).execute()
            if not response.data:
                await interaction.followup.send("Ainda não há dados de atividade de mensagens para este servidor.", ephemeral=True)
                return

            embed = discord.Embed(title="🏆 Top 10 Membros Mais Ativos", description=f"Ranking de atividade em **{interaction.guild.name}**.", color=discord.Color.gold())
            ranking_text = ""
            for i, profile in enumerate(response.data):
                rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"**#{i+1}**"
                ranking_text += f"{rank_emoji} **{profile['user_name']}**: `{profile['message_count']}` mensagens\n"
            
            if not ranking_text: ranking_text = "Ninguém enviou mensagens ainda!"
            embed.add_field(name="Classificação", value=ranking_text, inline=False)
            embed.set_footer(text="A contagem de mensagens começou quando o sistema de XP foi ativado.")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao buscar o ranking de atividade: {e}", ephemeral=True)

    @app_commands.command(name="crescimento", description="Mostra o gráfico de crescimento de novos membros.")
    @app_commands.describe(periodo="Agrupar dados por 'dia' ou 'mês'.")
    @app_commands.choices(periodo=[
        app_commands.Choice(name='Diário', value='D'),
        app_commands.Choice(name='Mensal', value='M')
    ])
    async def crescimento(self, interaction: Interaction, periodo: app_commands.Choice[str]):
        await interaction.response.defer()
        try:
            # 1. Fetch data from Supabase
            response = self.bot.supabase_client.table("member_growth_stats").select("joined_at").eq("guild_id", interaction.guild.id).execute()
            if not response.data:
                await interaction.followup.send("Não há dados de entrada de membros para gerar um gráfico ainda.")
                return

            # 2. Process data in pure Python
            growth_counts = defaultdict(int)
            date_format = "%Y-%m-%d" if periodo.value == 'D' else "%Y-%m"

            for record in response.data:
                joined_at_str = record['joined_at'].split('+')[0]
                dt_obj = datetime.fromisoformat(joined_at_str)
                grouping_key = dt_obj.strftime(date_format)
                growth_counts[grouping_key] += 1
            
            if not growth_counts:
                await interaction.followup.send("Não foi possível processar os dados de data para o gráfico.")
                return

            # Sort data by date
            sorted_items = sorted(growth_counts.items())
            labels = [item[0] for item in sorted_items]
            data_points = [item[1] for item in sorted_items]

            # 3. Construct QuickChart URL
            chart_config = {
                'type': 'bar',
                'data': {
                    'labels': labels,
                    'datasets': [{
                        'label': 'Novos Membros',
                        'data': data_points,
                        'backgroundColor': 'rgba(88, 101, 242, 0.8)', # Discord Blurple
                        'borderColor': 'rgba(88, 101, 242, 1)',
                        'borderWidth': 1
                    }]
                },
                'options': {
                    'title': {
                        'display': True,
                        'text': f'Crescimento de Membros ({periodo.name})',
                        'fontColor': '#FFFFFF',
                        'fontSize': 16
                    },
                    'legend': {
                        'labels': { 'fontColor': '#FFFFFF' }
                    },
                    'scales': {
                        'yAxes': [{
                            'ticks': {
                                'beginAtZero': True,
                                'fontColor': '#FFFFFF',
                                'stepSize': 1
                            },
                            'gridLines': { 'color': 'rgba(255, 255, 255, 0.1)' }
                        }],
                        'xAxes': [{
                            'ticks': { 'fontColor': '#FFFFFF' },
                            'gridLines': { 'color': 'rgba(255, 255, 255, 0.1)' }
                        }]
                    }
                },
                'backgroundColor': 'rgba(47, 49, 54, 1)' # Discord Grey
            }

            encoded_config = urllib.parse.quote(json.dumps(chart_config))
            chart_url = f"https://quickchart.io/chart?c={encoded_config}&width=800&height=450"

            # 4. Send the embed with the chart URL
            embed = discord.Embed(
                title=f"📈 Gráfico de Crescimento de Membros",
                color=discord.Color.blurple()
            )
            embed.set_image(url=chart_url)
            embed.set_footer(text=f"Dados agrupados em visualização {periodo.name.lower()}.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logging.error(f"Erro ao gerar gráfico de crescimento com API externa: {e}")
            await interaction.followup.send(f"Ocorreu um erro ao gerar o gráfico de crescimento: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Analise(bot))
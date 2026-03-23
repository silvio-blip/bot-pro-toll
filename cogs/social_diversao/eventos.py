import discord
from discord.ext import commands
from discord import app_commands
import logging

class Eventos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="criar_evento", description="Cria um evento customizado no canal.")
    @app_commands.describe(titulo="O título do seu evento.", subtitulo="Uma breve descrição para o evento.", imagem="A URL da imagem que aparecerá no evento.")
    async def criar_evento(self, interaction: discord.Interaction, titulo: str, subtitulo: str, imagem: str):
        """Cria e envia um embed de evento no canal atual."""
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id

        try:
            # Administradores podem criar eventos livremente
            if not interaction.user.guild_permissions.administrator:
                # Busca a configuração do servidor
                response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()

                required_role_id = None
                # Verifica se há dados e extrai a configuração do evento
                if response.data:
                    settings = response.data[0].get('settings', {})
                    event_config = settings.get('event_config', {})
                    required_role_id = event_config.get('event_creator_role_id')
                
                # Se não houver cargo configurado, informa o usuário
                if not required_role_id:
                    await interaction.followup.send("O cargo para criar eventos ainda não foi configurado. Peça para um administrador fazer isso no painel de controle (`/painel`).", ephemeral=True)
                    return
                
                # Verifica se o usuário possui o cargo necessário
                user_roles = [role.id for role in interaction.user.roles]
                if int(required_role_id) not in user_roles:
                    required_role = interaction.guild.get_role(int(required_role_id))
                    await interaction.followup.send(f"Você não tem permissão para usar este comando. É necessário ter o cargo {required_role.mention if required_role else 'configurado'} ou ser um administrador.", ephemeral=True)
                    return

        except Exception as e:
            logging.error(f"Erro crítico ao verificar permissões de evento para {interaction.user.name}: {e}")
            await interaction.followup.send("Ocorreu um erro inesperado ao verificar suas permissões. Por favor, tente novamente.", ephemeral=True)
            return

        # Se a verificação passar, cria e envia o evento
        embed = discord.Embed(
            title=titulo,
            description=subtitulo,
            color=discord.Color.brand_green()
        )
        embed.set_image(url=imagem)
        embed.set_footer(text=f"Evento anunciado por {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        try:
            await interaction.channel.send(embed=embed)
            await interaction.followup.send("Seu evento foi criado com sucesso!", ephemeral=True)
        except discord.errors.Forbidden:
            await interaction.followup.send("Não tenho permissão para enviar mensagens neste canal.", ephemeral=True)
        except Exception as e:
            logging.error(f"Falha ao criar evento: {e}")
            await interaction.followup.send(f"Não foi possível criar o evento. Verifique se a URL da imagem é válida.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Eventos(bot))

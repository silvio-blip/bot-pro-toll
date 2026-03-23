
import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle, Interaction
import logging

# --- IDs de Configuração ---
HUB_NOTIFICATION_CHANNEL_ID = 1484771954320871555 # CANAL DE NOTIFICAÇÃO
HUB_GUILD_ID = 1426737123956097175
HUB_STAFF_ROLE_ID = 1484488679253606540
HUB_CATEGORY_ID = 1484768469831651468

# --- View para Iniciar o Atendimento (Enviada para o canal de notificação) ---
class StartSupportView(ui.View):
    def __init__(self, requesting_user_id: int, requesting_guild_id: int):
        super().__init__(timeout=None)
        self.children[0].custom_id = f"start_support:{requesting_user_id}:{requesting_guild_id}"

    @ui.button(label="Iniciar Atendimento", style=ButtonStyle.success, emoji="✅")
    async def start_support(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer()

        try:
            _, user_id_str, guild_id_str = button.custom_id.split(":")
            requesting_user_id = int(user_id_str)
            
            hub_guild = interaction.client.get_guild(HUB_GUILD_ID) or await interaction.client.fetch_guild(HUB_GUILD_ID)
            requesting_user = await interaction.client.fetch_user(requesting_user_id)
            staff_role = hub_guild.get_role(HUB_STAFF_ROLE_ID)
            support_category = hub_guild.get_channel(HUB_CATEGORY_ID)

            if not all([hub_guild, requesting_user, staff_role, support_category]):
                await interaction.followup.send("❌ Falha ao encontrar um dos recursos essenciais (servidor, usuário, cargo ou categoria).", ephemeral=True)
                return

            overwrites = {
                hub_guild.default_role: discord.PermissionOverwrite(read_messages=False),
                staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                requesting_user: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
                hub_guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            channel_name = f"suporte-{requesting_user.name}"
            new_channel = await hub_guild.create_text_channel(
                name=channel_name,
                category=support_category,
                overwrites=overwrites,
                topic=f"Atendimento para {requesting_user.name} (ID: {requesting_user.id})"
            )

            button.disabled = True
            button.label = "Atendimento Iniciado"
            button.style = ButtonStyle.secondary
            await interaction.message.edit(view=self)

            welcome_embed = discord.Embed(
                title=f"Bem-vindo ao Suporte, {requesting_user.name}!",
                description=f"Este canal foi criado para seu atendimento direto com a equipe de suporte do bot.\n\nPor favor, descreva seu problema ou dúvida em detalhes.\n\nA equipe {staff_role.mention} já foi notificada.",
                color=discord.Color.blue()
            )
            await new_channel.send(content=f"Olá {requesting_user.mention}!", embed=welcome_embed)
            
            await interaction.followup.send(f"✅ Canal {new_channel.mention} criado com sucesso no servidor Hub.", ephemeral=True)
            
            try:
                await requesting_user.send(f"Seu canal de suporte foi aberto! Por favor, clique aqui para ser atendido: {new_channel.mention}")
            except discord.Forbidden:
                await new_channel.send(f"⚠️ {requesting_user.mention}, não foi possível enviar uma notificação para sua DM.")

        except Exception as e:
            logging.error(f"Erro ao iniciar atendimento: {e}")
            await interaction.followup.send(f"❌ Ocorreu um erro crítico: {e}", ephemeral=True)

# --- View para Solicitar Suporte (Enviada para os servidores clientes) ---
class RequestSupportView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Solicitar Suporte ao Desenvolvedor", style=ButtonStyle.primary, emoji="🛠️", custom_id="request_hub_support:v1")
    async def request_support(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("Seu pedido de suporte foi enviado para o desenvolvedor do bot. Você será notificado quando o atendimento começar.", ephemeral=True)
        
        # Busca o canal de notificação em vez do dono do bot
        notification_channel = await interaction.client.fetch_channel(HUB_NOTIFICATION_CHANNEL_ID)
        
        embed = discord.Embed(
            title="Novo Pedido de Suporte",
            description=f"Um usuário precisa de ajuda.",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Usuário", value=f"{interaction.user.name} ({interaction.user.id})", inline=False)
        embed.add_field(name="Servidor de Origem", value=f"{interaction.guild.name} ({interaction.guild.id})", inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Clique no botão abaixo para iniciar o atendimento.")

        view = StartSupportView(requesting_user_id=interaction.user.id, requesting_guild_id=interaction.guild.id)
        
        try:
            # Envia a notificação para o canal especificado
            await notification_channel.send(embed=embed, view=view)
        except discord.Forbidden:
            logging.error(f"Não foi possível enviar mensagem para o canal de notificação (ID: {HUB_NOTIFICATION_CHANNEL_ID}). Permissões?.")
        except Exception as e:
            logging.error(f"Erro desconhecido ao enviar notificação de suporte: {e}")


# --- Cog Principal ---
class HubSupport(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(RequestSupportView())
        self.bot.add_view(StartSupportView(requesting_user_id=0, requesting_guild_id=0))

    @app_commands.command(name="setup-suporte", description="Configura o painel para solicitar suporte ao desenvolvedor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_suporte(self, interaction: Interaction, canal: discord.TextChannel):
        embed = discord.Embed(
            title="Suporte Técnico do Bot",
            description="Encontrou um problema, um bug ou tem alguma dúvida sobre o bot?\n\nClique no botão abaixo para enviar um pedido de suporte diretamente para a equipe de desenvolvimento. Um canal privado será criado para você no nosso servidor de suporte.",
            color=0x2b2d31
        )
        try:
            await canal.send(embed=embed, view=RequestSupportView())
            await interaction.response.send_message(f"✅ Painel de suporte configurado em {canal.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ O bot não tem permissão para enviar mensagens neste canal.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro em /setup-suporte: {e}")
            await interaction.response.send_message("❌ Um erro inesperado ocorreu.", ephemeral=True)

    @setup_suporte.error
    async def on_setup_suporte_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Apenas administradores podem usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ocorreu um erro.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HubSupport(bot))

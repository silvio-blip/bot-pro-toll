import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from typing import Optional, List, Dict
from datetime import datetime

from .api_handler import APIHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("🤖 AGENTE IA")


class AgentIA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_handler = APIHandler()
        self.active_channels: Dict[int, int] = {}
        self.message_locks: Dict[int, asyncio.Lock] = {}
        logging.info("[🤖] Agente IA carregado com sucesso.")

    async def get_config(self, guild_id: int) -> Optional[Dict]:
        try:
            response = self.bot.supabase_client.table("ai_agent_config").select("*").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logging.error(f"[❌] Erro ao buscar configuração: {e}")
            return None

    async def save_config(self, guild_id: int, config: Dict) -> bool:
        try:
            self.bot.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": guild_id,
                **config
            }, on_conflict="server_guild_id").execute()
            logging.info(f"[✅] Configuração salva para servidor {guild_id}")
            return True
        except Exception as e:
            logging.error(f"[❌] Erro ao salvar configuração: {e}")
            return False

    async def get_conversation(self, guild_id: int, user_id: int) -> List[Dict]:
        try:
            response = self.bot.supabase_client.table("ai_conversations").select("messages").eq("server_guild_id", guild_id).eq("user_id", user_id).execute()
            if response.data:
                return response.data[0].get("messages", [])
            return []
        except Exception as e:
            logging.error(f"[❌] Erro ao buscar conversa: {e}")
            return []

    async def save_conversation(self, guild_id: int, user_id: int, messages: List[Dict]) -> bool:
        try:
            self.bot.supabase_client.table("ai_conversations").upsert({
                "server_guild_id": guild_id,
                "user_id": user_id,
                "messages": messages,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar conversa: {e}")
            return False

    async def check_permissions(self, interaction: discord.Interaction) -> tuple[bool, Optional[str]]:
        config = await self.get_config(interaction.guild_id)
        
        if not config:
            return False, "O agente IA não foi configurado neste servidor. Use os comandos de configuração no painel."
        
        if not config.get("enabled", False):
            return False, "O agente IA está desativado neste servidor."
        
        allowed_role_id = config.get("allowed_role_id")
        if allowed_role_id:
            role = interaction.guild.get_role(allowed_role_id)
            if role and role in interaction.user.roles:
                return True, None
            return False, f"Você não tem permissão para usar o agente IA. Precisa do cargo <@{allowed_role_id}>."
        
        return True, None

    async def create_private_channel(self, interaction: discord.Interaction, config: Dict) -> Optional[discord.TextChannel]:
        category_id = config.get("channel_category_id")
        
        if category_id:
            category = interaction.guild.get_channel(category_id)
            if not category:
                category = None
        else:
            category = None
        
        channel_name = f"ia-{interaction.user.name.lower().replace(' ', '-')}"
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        }
        
        viewer_role_id = config.get("viewer_role_id")
        if config.get("enable_viewer_role") and viewer_role_id:
            viewer_role = interaction.guild.get_role(viewer_role_id)
            if viewer_role:
                overwrites[viewer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_messages=True)
        
        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Conversa com {config.get('agent_name', 'IA')}"
            )
            self.active_channels[interaction.user.id] = channel.id
            return channel
        except Exception as e:
            logger.error(f"Erro ao criar canal: {e}")
            return None

    @app_commands.command(name="ia", description="Iniciar conversa com o Agente IA")
    async def ia_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        has_permission, error_msg = await self.check_permissions(interaction)
        if not has_permission:
            await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            return
        
        config = await self.get_config(interaction.guild_id)
        
        if not config.get("api_url") or not config.get("api_key") or not config.get("model_name"):
            await interaction.followup.send("❌ O agente IA não está completamente configurado. Configure a API e o modelo no painel.", ephemeral=True)
            return
        
        existing_channel_id = self.active_channels.get(interaction.user.id)
        if existing_channel_id:
            existing_channel = self.bot.get_channel(existing_channel_id)
            if existing_channel:
                await interaction.followup.send(f"Você já tem um canal ativo: {existing_channel.mention}", ephemeral=True)
                return
        
        channel = await self.create_private_channel(interaction, config)
        
        if not channel:
            logging.error(f"[❌] Erro ao criar canal para usuário {interaction.user.id}")
            await interaction.followup.send("❌ Erro ao criar canal de conversa.", ephemeral=True)
            return
        
        logging.info(f"[✅] Canal criado para {interaction.user.name} | Canal: {channel.name}")
        agent_name = config.get("agent_name", "IA")
        
        embed = discord.Embed(
            title=f"🤖 Conversa com {agent_name} iniciada",
            description=f"Bem-vindo! Você está em uma conversa privada com o {agent_name}.\n\nPode começar a enviar suas mensagens aqui.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Suas mensagens serão lembradas durante toda a conversa.")
        
        await interaction.followup.send(f"Canal criado: {channel.mention}", ephemeral=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        user_channel_id = self.active_channels.get(message.author.id)
        if not user_channel_id or message.channel.id != user_channel_id:
            return
        
        if message.author.id not in self.message_locks:
            self.message_locks[message.author.id] = asyncio.Lock()
        
        async with self.message_locks[message.author.id]:
            await message.channel.typing()
            logging.info(f"[💬] Mensagem recebida de {message.author.name} | Servidor: {message.guild.name}")
            
            config = await self.get_config(message.guild.id)
            if not config:
                return
            
            conversation = await self.get_conversation(message.guild.id, message.author.id)
            logging.info(f"[📚] Histórico carregado | Mensagens: {len(conversation)}")
            
            messages_for_api = []
            for msg in conversation:
                messages_for_api.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            messages_for_api.append({
                "role": "user",
                "content": message.content
            })
            
            system_prompt = config.get("system_prompt", "")
            if system_prompt and (not messages_for_api or messages_for_api[0].get("role") != "system"):
                pass
            
            logging.info(f"[🔄] Enviando para API...")
            success, error, response = await self.api_handler.send_message(
                api_url=config["api_url"],
                api_key=config["api_key"],
                model=config["model_name"],
                messages=messages_for_api,
                system_prompt=system_prompt
            )
            
            if not success:
                logging.error(f"[❌] Erro na API: {error}")
                embed = discord.Embed(
                    title="❌ Erro na API",
                    description=error,
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
                return
            
            conversation.append({
                "role": "user",
                "content": message.content,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            conversation.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await self.save_conversation(message.guild.id, message.author.id, conversation)
            logging.info(f"[✅] Resposta salva | Total de mensagens: {len(conversation)}")
            
            embed = discord.Embed(
                description=response,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"{config.get('agent_name', 'IA')} • Lembre-se: suas conversas são mantidas em memória")
            
            await message.channel.send(embed=embed)
            logging.info(f"[✅] Resposta enviada para {message.author.name}")

    @app_commands.command(name="ia-clear", description="Limpar histórico de conversa com a IA")
    async def ia_clear_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        has_permission, error_msg = await self.check_permissions(interaction)
        if not has_permission:
            await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            return
        
        try:
            self.bot.supabase_client.table("ai_conversations").delete().eq("server_guild_id", interaction.guild_id).eq("user_id", interaction.user.id).execute()
            
            if interaction.user.id in self.active_channels:
                channel_id = self.active_channels.pop(interaction.user.id)
                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        await channel.delete()
                    except:
                        pass
            
            await interaction.followup.send("✅ Histórico de conversa limpo com sucesso!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao limpar histórico: {str(e)}", ephemeral=True)

    @app_commands.command(name="ia-status", description="Ver status do agente IA neste servidor")
    async def ia_status_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        config = await self.get_config(interaction.guild_id)
        
        if not config:
            await interaction.followup.send("❌ O agente IA não foi configurado neste servidor.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🤖 Status do Agente IA - {interaction.guild.name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Ativado",
            value="✅ Sim" if config.get("enabled") else "❌ Não",
            inline=True
        )
        
        embed.add_field(
            name="Nome do Agente",
            value=config.get("agent_name", "Não definido"),
            inline=True
        )
        
        embed.add_field(
            name="Modelo",
            value=config.get("model_name", "Não definido"),
            inline=True
        )
        
        allowed_role_id = config.get("allowed_role_id")
        if allowed_role_id:
            role = interaction.guild.get_role(allowed_role_id)
            embed.add_field(
                name="Cargo Permitido",
                value=f"@{role.name}" if role else f"ID: {allowed_role_id}",
                inline=True
            )
        
        embed.add_field(
            name="API Provider",
            value=config.get("api_provider", "Não definido"),
            inline=True
        )
        
        if config.get("channel_category_id"):
            embed.add_field(
                name="Categoria de Canais",
                value=f"ID: {config.get('channel_category_id')}",
                inline=True
            )
        
        if config.get("enable_viewer_role") and config.get("viewer_role_id"):
            viewer_role = interaction.guild.get_role(config.get("viewer_role_id"))
            embed.add_field(
                name="Cargo que pode ver",
                value=f"@{viewer_role.name}" if viewer_role else f"ID: {config.get('viewer_role_id')}",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AgentIA(bot))
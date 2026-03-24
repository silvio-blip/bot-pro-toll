import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from typing import Optional, List, Dict
from datetime import datetime

from .api_handler import APIHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("🤖 AGENTE IA")

class AgentIA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_handler = APIHandler()
        self.active_channels: Dict[int, int] = {}
        self.message_locks: Dict[int, asyncio.Lock] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """CORREÇÃO DEFINITIVA: Carrega os canais de IA ativos sem causar erros de arranque."""
        try:
            # Lógica corrigida: Removemos o filtro .not_() que causava o erro.
            # Agora, filtramos em Python, o que é mais seguro.
            response = self.bot.supabase_client.table("ai_conversations").select("user_id, channel_id").execute()
            if response.data:
                loaded_channels = 0
                for record in response.data:
                    channel_id = record.get('channel_id')
                    if channel_id:  # Filtra para garantir que channel_id não é null
                        user_id = record.get('user_id')
                        if self.bot.get_channel(channel_id):
                            self.active_channels[user_id] = channel_id
                            loaded_channels += 1
                if loaded_channels > 0:
                    logger.info(f"[✅] Carregados {loaded_channels} canais de IA ativos da base de dados.")
        except Exception as e:
            logger.error(f"[❌] Erro crítico ao carregar canais de IA: {e}")

    async def get_config(self, guild_id: int) -> Optional[Dict]:
        try:
            # CORREÇÃO: Adicionado .single() para garantir que apenas um resultado é retornado.
            response = self.bot.supabase_client.table("ai_agent_config").select("*").eq("server_guild_id", guild_id).single().execute()
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"[❌] Erro ao buscar config de IA: {e}")
            return None

    async def get_conversation(self, guild_id: int, user_id: int) -> List[Dict]:
        try:
            # CORREÇÃO: Adicionado .single() para garantir que apenas um resultado é retornado.
            response = self.bot.supabase_client.table("ai_conversations").select("messages").eq("server_guild_id", guild_id).eq("user_id", user_id).single().execute()
            return response.data.get("messages", []) if response.data else []
        except Exception:
            return []

    async def save_or_update_conversation(self, guild_id: int, user_id: int, messages: List[Dict] = None, channel_id: Optional[int] = -1):
        try:
            record = {"server_guild_id": guild_id, "user_id": user_id, "updated_at": datetime.utcnow().isoformat()}
            if messages is not None: record['messages'] = messages
            if channel_id != -1: record['channel_id'] = channel_id
            self.bot.supabase_client.table("ai_conversations").upsert(record, on_conflict="server_guild_id,user_id").execute()
            return True
        except Exception as e:
            logger.error(f"[❌] Erro ao salvar/atualizar conversa: {e}")
            return False

    @app_commands.command(name="ia", description="Iniciar conversa com o Agente IA")
    async def ia_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if (channel_id := self.active_channels.get(interaction.user.id)) and (channel := self.bot.get_channel(channel_id)):
            return await interaction.followup.send(f"❗️ Você já tem um canal de IA ativo: {channel.mention}", ephemeral=True)

        config = await self.get_config(interaction.guild.id)
        if not config or not config.get("enabled"):
            return await interaction.followup.send("❌ O Agente IA está desativado ou não configurado.", ephemeral=True)

        channel = await self.create_private_channel(interaction, config)
        if not channel: return await interaction.followup.send("❌ Erro ao criar seu canal de IA.", ephemeral=True)

        self.active_channels[interaction.user.id] = channel.id
        await self.save_or_update_conversation(interaction.guild.id, interaction.user.id, channel_id=channel.id)
        
        agent_name = config.get("agent_name", "IA")
        embed = discord.Embed(title=f"🤖 Conversa com {agent_name}", description="Bem-vindo! Pode começar a enviar suas mensagens aqui.", color=discord.Color.blue()).set_footer(text="Suas mensagens serão lembradas durante toda a conversa.")
        await interaction.followup.send(f"✅ Canal de IA criado: {channel.mention}", ephemeral=True)
        await channel.send(embed=embed)

    async def create_private_channel(self, interaction: discord.Interaction, config: Dict) -> Optional[discord.TextChannel]:
        try:
            category = interaction.guild.get_channel(config.get("channel_category_id")) if config.get("channel_category_id") else None
            channel_name = f"ia-{interaction.user.name.lower().replace(' ', '-')}"
            overwrites = { interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True) }
            if config.get("enable_viewer_role") and (viewer_role := interaction.guild.get_role(config.get("viewer_role_id"))):
                overwrites[viewer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
            return await interaction.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e: 
            logger.error(f"[❌] Erro ao criar canal: {e}"); return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or self.active_channels.get(message.author.id) != message.channel.id:
            return
        
        lock = self.message_locks.setdefault(message.author.id, asyncio.Lock())
        async with lock, message.channel.typing():
            config = await self.get_config(message.guild.id)
            if not config: return

            conversation_history = await self.get_conversation(message.guild.id, message.author.id)
            api_history = [{'role': msg['role'], 'content': msg['content']} for msg in conversation_history]
            
            messages_for_api = []
            if system_prompt := config.get("system_prompt"): messages_for_api.append({"role": "system", "content": system_prompt})
            messages_for_api.extend(api_history)
            messages_for_api.append({"role": "user", "content": message.content})
            
            success, error, response = await self.api_handler.send_message(api_url=config["api_url"], api_key=config["api_key"], model=config["model_name"], messages=messages_for_api)
            
            if not success: return await message.channel.send(embed=discord.Embed(title="❌ Erro na API", description=error, color=discord.Color.red()))
            
            conversation_history.append({"role": "user", "content": message.content, "timestamp": datetime.utcnow().isoformat()})
            conversation_history.append({"role": "assistant", "content": response, "timestamp": datetime.utcnow().isoformat()})
            await self.save_or_update_conversation(message.guild.id, message.author.id, messages=conversation_history)

            embed = discord.Embed(description=response, color=discord.Color.green()).set_footer(text=f"{config.get('agent_name', 'IA')} • Conversas em memória")
            await message.channel.send(embed=embed)

    @app_commands.command(name="ia-clear", description="Limpa seu histórico e fecha o canal de IA.")
    async def ia_clear_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        channel_id = self.active_channels.pop(interaction.user.id, None)
        
        await self.save_or_update_conversation(interaction.guild.id, interaction.user.id, messages=[], channel_id=None)

        if channel_id and (channel := self.bot.get_channel(channel_id)):
            try: await channel.delete()
            except discord.NotFound: pass

        await interaction.followup.send("✅ Seu histórico e canal de IA foram limpos com sucesso!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AgentIA(bot))
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

    async def cog_load(self):
        """Carrega os canais de IA ativos da base de dados quando o bot inicia."""
        await self.bot.wait_until_ready()
        try:
            response = self.bot.supabase_client.table("ai_conversations").select("user_id, channel_id").eq("is_channel_active", True).execute()
            if response.data:
                for item in response.data:
                    if self.bot.get_channel(item['channel_id']):
                        self.active_channels[item['user_id']] = item['channel_id']
                logger.info(f"[✅] Carregados {len(self.active_channels)} canais de IA ativos.")
        except Exception as e:
            logger.error(f"[❌] Erro ao carregar canais de IA ativos: {e}")

    async def get_config(self, guild_id: int) -> Optional[Dict]:
        try:
            response = self.bot.supabase_client.table("ai_agent_config").select("*").eq("server_guild_id", guild_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logging.error(f"[❌] Erro ao buscar config de IA: {e}")
            return None

    async def get_conversation(self, guild_id: int, user_id: int) -> List[Dict]:
        try:
            response = self.bot.supabase_client.table("ai_conversations").select("messages").eq("server_guild_id", guild_id).eq("user_id", user_id).single().execute()
            return response.data.get("messages", []) if response.data else []
        except Exception:
            return [] # Retorna lista vazia se não encontrar ou der erro

    async def save_conversation(self, guild_id: int, user_id: int, messages: List[Dict]) -> bool:
        try:
            self.bot.supabase_client.table("ai_conversations").upsert({
                "server_guild_id": guild_id,
                "user_id": user_id,
                "messages": messages,
                "updated_at": datetime.utcnow().isoformat()
            }, on_conflict="server_guild_id,user_id").execute()
            return True
        except Exception as e:
            logger.error(f"[❌] Erro ao salvar conversa: {e}")
            return False

    async def update_channel_status(self, guild_id: int, user_id: int, channel_id: Optional[int], is_active: bool):
        """Atualiza o status do canal na base de dados."""
        try:
            self.bot.supabase_client.table("ai_conversations").upsert({
                "server_guild_id": guild_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "is_channel_active": is_active
            }, on_conflict="server_guild_id,user_id").execute()
        except Exception as e:
            logger.error(f"[❌] Erro ao atualizar status do canal: {e}")

    @app_commands.command(name="ia", description="Iniciar conversa com o Agente IA")
    async def ia_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if (channel_id := self.active_channels.get(interaction.user.id)) and (channel := self.bot.get_channel(channel_id)):
            return await interaction.followup.send(f"❗️ Você já tem um canal de IA ativo: {channel.mention}", ephemeral=True)

        config = await self.get_config(interaction.guild.id)
        if not config or not config.get("enabled"):
            return await interaction.followup.send("❌ O Agente IA está desativado ou não configurado.", ephemeral=True)

        # ... (criação do canal, como antes)
        channel = await self.create_private_channel(interaction, config)
        if not channel:
            return await interaction.followup.send("❌ Erro ao criar seu canal de IA.", ephemeral=True)

        # Registra o novo canal na memória e na base de dados
        self.active_channels[interaction.user.id] = channel.id
        await self.update_channel_status(interaction.guild.id, interaction.user.id, channel.id, True)
        
        # ... (envia mensagem de boas-vindas)
        agent_name = config.get("agent_name", "IA")
        embed = discord.Embed(title=f"🤖 Conversa com {agent_name}", description="Bem-vindo! Pode começar a enviar suas mensagens aqui.", color=discord.Color.blue())
        await interaction.followup.send(f"✅ Canal de IA criado: {channel.mention}", ephemeral=True)
        await channel.send(embed=embed)

    async def create_private_channel(self, interaction: discord.Interaction, config: Dict) -> Optional[discord.TextChannel]:
        # (Esta função permanece a mesma de antes)
        category = interaction.guild.get_channel(config.get("channel_category_id")) if config.get("channel_category_id") else None
        channel_name = f"ia-{interaction.user.name.lower().replace(' ', '-')}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True)
        }
        if config.get("enable_viewer_role") and (viewer_role := interaction.guild.get_role(config.get("viewer_role_id"))):
            overwrites[viewer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        try:
            return await interaction.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            logger.error(f"[❌] Erro ao criar canal privado: {e}")
            return None

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
            if system_prompt := config.get("system_prompt"): 
                messages_for_api.append({"role": "system", "content": system_prompt})
            messages_for_api.extend(api_history)
            messages_for_api.append({"role": "user", "content": message.content})
            
            success, error, response = await self.api_handler.send_message(
                api_url=config["api_url"], api_key=config["api_key"], model=config["model_name"], messages=messages_for_api
            )
            
            if not success:
                await message.channel.send(embed=discord.Embed(title="❌ Erro na API", description=error, color=discord.Color.red()))
                return
            
            conversation_history.append({"role": "user", "content": message.content, "timestamp": datetime.utcnow().isoformat()})
            conversation_history.append({"role": "assistant", "content": response, "timestamp": datetime.utcnow().isoformat()})
            
            await self.save_conversation(message.guild.id, message.author.id, conversation_history)

            await message.channel.send(embed=discord.Embed(description=response, color=discord.Color.green()))

    @app_commands.command(name="ia-clear", description="Limpa seu histórico e fecha o canal de IA.")
    async def ia_clear_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Remove da memória
        channel_id = self.active_channels.pop(interaction.user.id, None)
        
        # Marca como inativo na DB
        await self.update_channel_status(interaction.guild.id, interaction.user.id, None, False)
        
        # Limpa o histórico da conversa na DB
        await self.save_conversation(interaction.guild.id, interaction.user.id, [])

        if channel_id and (channel := self.bot.get_channel(channel_id)):
            try:
                await channel.delete()
            except discord.NotFound:
                pass # Canal já foi deletado, o que é ok

        await interaction.followup.send("✅ Seu histórico e canal de IA foram limpos com sucesso!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AgentIA(bot))

import discord
from discord.ext import commands
import logging
import random
import time

class XpSystem(commands.Cog):
    """Cog para o sistema de ganho de XP por mensagem."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_cooldowns = {}

    async def get_guild_settings(self, guild_id: int) -> dict:
        """Busca as configurações de XP diretamente do banco de dados."""
        try:
            response = self.bot.supabase_client.table("server_configurations") \
                .select("settings") \
                .eq("server_guild_id", guild_id) \
                .execute()

            if response.data:
                server_settings = response.data[0].get('settings', {})
                gamification = server_settings.get('gamification_xp', {})
                logging.info(f"[XP] Config carregada para guild {guild_id}: {gamification}")
                return gamification
            else:
                logging.warning(f"[XP] Nenhuma configuração encontrada para guild {guild_id}")
        except Exception as e:
            logging.error(f"[XP] Erro ao buscar configurações para o servidor {guild_id}: {e}")
        return {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.channel.permissions_for(message.guild.me).send_messages:
            return
        
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        guild_id = message.guild.id
        settings = await self.get_guild_settings(guild_id)
        
        if not settings.get("enabled", False):
            return

        cooldown_seconds = settings.get("cooldown_seconds", 60)
        current_time = time.time()
        user_id = message.author.id

        if guild_id not in self.user_cooldowns:
            self.user_cooldowns[guild_id] = {}
        
        last_message_time = self.user_cooldowns[guild_id].get(user_id, 0)

        if (current_time - last_message_time) > cooldown_seconds:
            await self.grant_xp_and_level_up(message, settings)
            self.user_cooldowns[guild_id][user_id] = current_time

    async def grant_xp_and_level_up(self, message: discord.Message, settings: dict):
        """Concede XP e verifica se o usuário subiu de nível, usando a função centralizada."""
        xp_min = settings.get("xp_min", 5)
        xp_max = settings.get("xp_max", 15)
        xp_to_add = random.randint(xp_min, xp_max)
        
        logging.info(f"[XP] Concedendo {xp_to_add} XP para {message.author.name} ({message.author.id}) no servidor {message.guild.name}")

        try:
            new_level = await self.bot.update_xp(message.author, message.guild, xp_to_add, is_message=True)

            if new_level is not None:
                try:
                    level_up_message = settings.get("level_up_message", "🎉 Parabéns {mention}, você alcançou o **Nível {level}** no servidor {guild}! 🎉")
                    logging.info(f"[XP] Mensagem de level up carregada: {level_up_message}")
                    formatted_message = level_up_message.format(mention=message.author.mention, level=new_level, user=message.author.display_name, guild=message.guild.name)
                    await message.author.send(formatted_message)
                except discord.Forbidden:
                    logging.warning(f"Não foi possível enviar a DM de level up para {message.author.name}.")

        except Exception as e:
            logging.error(f"[XP] Erro Crítico ao chamar update_xp para {message.author.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(XpSystem(bot))

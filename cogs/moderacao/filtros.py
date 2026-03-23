
import discord
from discord.ext import commands
from discord import ui, Interaction, Member
from supabase import Client
import logging
from collections import defaultdict
from datetime import datetime, timedelta

# --- Funções Auxiliares de Configuração ---

async def get_filter_config(bot: commands.Bot, guild_id: int, filter_key: str) -> dict:
    """Busca a configuração de um filtro específico para um servidor."""
    try:
        response = bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
        if response.data:
            return response.data[0].get('settings', {}).get(filter_key, {})
    except Exception as e:
        logging.error(f"Erro ao buscar config do filtro {filter_key} para o servidor {guild_id}: {e}")
    return {}

# --- Modais de Configuração ---

class BadWordsConfigModal(ui.Modal, title="Filtro de Palavras Proibidas"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        enabled_value = "sim" if self.config.get("enabled") else "não"
        words = ", ".join(self.config.get("words", []))

        self.add_item(ui.TextInput(label="Ativar filtro?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="Palavras (separadas por vírgula)", custom_id="words", style=discord.TextStyle.long, placeholder="exemplo1, exemplo2, ...", default=words, required=False))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        words_list = [word.strip().lower() for word in self.children[1].value.split(',') if word.strip()]
        config_data = {
            "enabled": self.children[0].value.lower() == 'sim',
            "words": words_list
        }

        def update_settings(settings):
            settings['bad_words'] = config_data

        success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
        if success:
            await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)

class InviteFilterConfigModal(ui.Modal, title="Filtro de Convites"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        enabled_value = "sim" if self.config.get("enabled") else "não"
        self.add_item(ui.TextInput(label="Ativar filtro?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        config_data = {"enabled": self.children[0].value.lower() == 'sim'}

        def update_settings(settings):
            settings['invite_filter'] = config_data

        success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
        if success:
            await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)

# ... (outros modais seguem o mesmo padrão de correção)

class LinkFilterConfigModal(ui.Modal, title="Filtro de Links"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        enabled_value = "sim" if self.config.get("enabled") else "não"
        self.add_item(ui.TextInput(label="Ativar filtro?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        config_data = {"enabled": self.children[0].value.lower() == 'sim'}

        def update_settings(settings):
            settings['link_filter'] = config_data

        success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
        if success:
            await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)

class AntiCapsConfigModal(ui.Modal, title="Filtro de Excesso de CAPS"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        enabled_value = "sim" if self.config.get("enabled") else "não"
        self.add_item(ui.TextInput(label="Ativar filtro?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="Percentual Mínimo de CAPS (%)", custom_id="caps_percentage", placeholder="Ex: 70", default=str(self.config.get("percentage", "70"))))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            percentage = int(self.children[1].value)
            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "percentage": percentage
            }
            def update_settings(settings):
                settings['anti_caps'] = config_data
            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ Percentual de CAPS deve ser um número inteiro.", ephemeral=True)

class AntiEmojiConfigModal(ui.Modal, title="Filtro de Excesso de Emojis"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        enabled_value = "sim" if self.config.get("enabled") else "não"
        self.add_item(ui.TextInput(label="Ativar filtro?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="Quantidade Máxima de Emojis", custom_id="max_emojis", placeholder="Ex: 5", default=str(self.config.get("max_emojis", "5"))))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            max_emojis = int(self.children[1].value)
            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "max_emojis": max_emojis
            }
            def update_settings(settings):
                settings['anti_emoji'] = config_data
            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ A quantidade de emojis deve ser um número inteiro.", ephemeral=True)

class AntiSpamConfigModal(ui.Modal, title="Filtro Anti-Spam"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        enabled_value = "sim" if self.config.get("enabled") else "não"
        self.add_item(ui.TextInput(label="Ativar filtro?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="Nº de mensagens", custom_id="msg_count", placeholder="Ex: 5", default=str(self.config.get("msg_count", "5"))))
        self.add_item(ui.TextInput(label="Intervalo de tempo (segundos)", custom_id="interval", placeholder="Ex: 10", default=str(self.config.get("interval", "10"))))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            msg_count = int(self.children[1].value)
            interval = int(self.children[2].value)
            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "msg_count": msg_count,
                "interval": interval
            }
            def update_settings(settings):
                settings['anti_spam'] = config_data
            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ Os valores devem ser números inteiros.", ephemeral=True)

# --- Cog Principal ---

class Filtros(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_tracker = defaultdict(lambda: defaultdict(list))

    async def get_server_config(self, guild_id: int) -> dict:
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {})
        except Exception as e:
            logging.error(f"Erro ao buscar config de filtros para o servidor {guild_id}: {e}")
        return {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        
        config = await self.get_server_config(message.guild.id)
        if not config:
            return

        # --- Verificações dos Filtros ---
        delete_message = False
        reason = ""

        # Bad Words
        bad_words_config = config.get('bad_words', {})
        if bad_words_config.get('enabled'):
            if any(word in message.content.lower() for word in bad_words_config.get('words', [])):
                delete_message = True
                reason = "Uso de palavra proibida."

        # Invite Filter
        invite_filter_config = config.get('invite_filter', {})
        if not delete_message and invite_filter_config.get('enabled'):
            if "discord.gg/" in message.content or "discord.com/invite/" in message.content:
                delete_message = True
                reason = "Envio de convites de servidor não é permitido."
        
        # Link Filter
        link_filter_config = config.get('link_filter', {})
        if not delete_message and link_filter_config.get('enabled'):
            if "http://" in message.content or "https://" in message.content:
                delete_message = True
                reason = "Envio de links não é permitido."

        # Anti-CAPS
        anti_caps_config = config.get('anti_caps', {})
        if not delete_message and anti_caps_config.get('enabled'):
            text_len = len(message.content)
            if text_len > 10: # Evitar falsos positivos em mensagens curtas
                caps_len = sum(1 for c in message.content if c.isupper())
                if (caps_len / text_len * 100) > anti_caps_config.get('percentage', 70):
                    delete_message = True
                    reason = "Uso excessivo de letras maiúsculas (CAPS)."
        
        # Anti-Emoji
        anti_emoji_config = config.get('anti_emoji', {})
        if not delete_message and anti_emoji_config.get('enabled'):
            # Esta é uma forma simplificada de contar emojis.
            # Para uma contagem precisa, seria necessária uma biblioteca como a `emoji`.
            import re
            emoji_regex = r'<a?:\w+:\d+>|\U0001F000-\U0001FAFF|\u2600-\u26FF|\u2700-\u27BF'
            emoji_count = len(re.findall(emoji_regex, message.content))
            if emoji_count > anti_emoji_config.get('max_emojis', 5):
                delete_message = True
                reason = "Uso excessivo de emojis."

        # Anti-Spam
        anti_spam_config = config.get('anti_spam', {})
        if not delete_message and anti_spam_config.get('enabled'):
            now = datetime.utcnow()
            user_msgs = self.spam_tracker[message.guild.id][message.author.id]
            interval = timedelta(seconds=anti_spam_config.get('interval', 10))
            
            # Remove timestamps antigos
            user_msgs = [t for t in user_msgs if now - t < interval]
            user_msgs.append(now)
            self.spam_tracker[message.guild.id][message.author.id] = user_msgs

            if len(user_msgs) > anti_spam_config.get('msg_count', 5):
                delete_message = True
                reason = "Spam de mensagens detectado."
                # Poderia adicionar uma punição aqui, como um mute temporário.

        if delete_message:
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention}, sua mensagem foi removida. Motivo: {reason}", delete_after=10)
            except discord.errors.NotFound:
                pass # A mensagem já foi deletada
            except discord.errors.Forbidden:
                logging.warning(f"Sem permissão para deletar mensagem no servidor {message.guild.id}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Filtros(bot))
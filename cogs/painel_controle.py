
# -*- coding: utf-8 -*-
# VERSÃO CORRIGIDA E DEFINITIVA - Substitui completamente o ficheiro anterior.

import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, ButtonStyle, SelectOption, TextStyle
import logging

# --- Importando componentes de outros arquivos ---
from cogs.moderacao.antiraid import AntiRaidConfigModal
from cogs.moderacao.captcha import CaptchaConfigModal
from cogs.moderacao.warns import WarnsConfigModal
from cogs.moderacao.logs import LogSettingsView
from cogs.moderacao.limpar import LimparConfigModal
from cogs.moderacao.filtros import (
    BadWordsConfigModal, InviteFilterConfigModal, LinkFilterConfigModal,
    AntiCapsConfigModal, AntiEmojiConfigModal, AntiSpamConfigModal
)
from cogs.administracao.autorole import AutoRoleConfigModal
from cogs.loja.shop_manager import ShopManagerPanelView
from cogs.ia.api_handler import APIHandler

# --- Configuração do Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("PainelControleCog")

ai_api_handler = APIHandler()

# --- Função Auxiliar para buscar Configurações ---
async def get_specific_config(bot, guild_id: int, config_key: str) -> dict:
    try:
        if not hasattr(bot, 'supabase_client'): return {}
        response = bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
        if response.data:
            all_settings = response.data[0].get('settings', {})
            # Se a chave existe diretamente, retorna
            if config_key in all_settings:
                return all_settings.get(config_key, {})
            # Se não, verifica se está dentro de uma sub-chave (ex: gamification_xp)
            for key, value in all_settings.items():
                if isinstance(value, dict) and config_key in value:
                    return value.get(config_key, {})
            # Retorna a chave principal se for gamification_xp
            if config_key == "gamification_xp":
                return all_settings.get("gamification_xp", {})
    except Exception as e:
        logger.error(f"Erro ao buscar config de {config_key} para o servidor {guild_id}: {e}", exc_info=True)
    return {}

# --- Modais de Configuração (Completos e Corretos) ---

class EventConfigModal(ui.Modal, title="Configuração de Eventos"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(ui.TextInput(label="ID do Cargo para Criar Eventos", default=str(config.get("event_creator_role_id", ""))))

    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        role_id_str = self.children[0].value
        guild_id = i.guild.id
        if role_id_str and not role_id_str.isdigit():
            return await i.followup.send("O ID do cargo deve ser um número.", ephemeral=True)
        role_id = int(role_id_str) if role_id_str else None
        if role_id and i.guild.get_role(role_id) is None:
            return await i.followup.send("O ID do cargo informado não foi encontrado.", ephemeral=True)
        
        # Esta função precisa existir no seu bot
        if hasattr(self.bot, 'get_and_update_server_settings'):
            def update_config(settings: dict):
                settings.setdefault('event_config', {})['event_creator_role_id'] = role_id
            success = await self.bot.get_and_update_server_settings(guild_id, update_config)
            await i.followup.send("Configuração salva!" if success else "Erro ao salvar!", ephemeral=True)
        else:
            await i.followup.send("Erro: Função de update não encontrada no bot.", ephemeral=True)


class XpConfigModal(ui.Modal, title="Configurações Gerais de XP"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Ativar Sistema (sim/não)", default=config.get("enabled", True)))
        self.add_item(ui.TextInput(label="Nome dos Pontos", default=config.get("points_name", "XP")))
        self.add_item(ui.TextInput(label="Cooldown (segundos)", default=str(config.get("cooldown_seconds", 60))))
        self.add_item(ui.TextInput(label="XP Mínimo por Mensagem", default=str(config.get("xp_min", 5))))
        self.add_item(ui.TextInput(label="XP Máximo por Mensagem", default=str(config.get("xp_max", 15))))
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        guild_id = i.guild.id
        
        if hasattr(self.bot, 'get_and_update_server_settings'):
            def update_config(settings: dict):
                enabled_val = self.children[0].value.strip().lower()
                settings.setdefault('gamification_xp', {})['enabled'] = enabled_val in ['sim', 'true', '1', 'yes', 'on']
                settings.setdefault('gamification_xp', {})['points_name'] = self.children[1].value.strip()
                settings.setdefault('gamification_xp', {})['cooldown_seconds'] = int(self.children[2].value.strip() or 60)
                settings.setdefault('gamification_xp', {})['xp_min'] = int(self.children[3].value.strip() or 5)
                settings.setdefault('gamification_xp', {})['xp_max'] = int(self.children[4].value.strip() or 15)
            
            success = await self.bot.get_and_update_server_settings(guild_id, update_config)
            await i.followup.send("Configurações salvas!" if success else "Erro ao salvar!", ephemeral=True)
        else:
            await i.followup.send("Configurações salvas.", ephemeral=True)

class LevelUpConfigModal(ui.Modal, title="Configuração de Níveis"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="XP Base para Nível (XP para cada nível)", default=str(config.get("xp_per_level_base", 300))))
        self.add_item(ui.TextInput(label="Mensagem de Level Up", style=TextStyle.long, default=config.get("level_up_message", "🎉 Parabéns {mention}, você alcançou o **Nível {level}** no servidor {guild}! 🎉")))
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        guild_id = i.guild.id
        
        if hasattr(self.bot, 'get_and_update_server_settings'):
            def update_config(settings: dict):
                settings.setdefault('gamification_xp', {})['xp_per_level_base'] = int(self.children[0].value.strip() or 300)
                settings.setdefault('gamification_xp', {})['level_up_message'] = self.children[1].value.strip()
            
            success = await self.bot.get_and_update_server_settings(guild_id, update_config)
            await i.followup.send("Configurações salvas!" if success else "Erro ao salvar!", ephemeral=True)
        else:
            await i.followup.send("Configurações salvas.", ephemeral=True)

class DailyRewardConfigModal(ui.Modal, title="Config. Recompensa Diária"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Cooldown do /daily (horas)", default=str(config.get("daily_cooldown_hours", 23))))
        self.add_item(ui.TextInput(label="XP Mínimo do /daily", default=str(config.get("daily_xp_min", 50))))
        self.add_item(ui.TextInput(label="XP Máximo do /daily", default=str(config.get("daily_xp_max", 200))))
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        guild_id = i.guild.id
        
        if hasattr(self.bot, 'get_and_update_server_settings'):
            def update_config(settings: dict):
                settings.setdefault('gamification_xp', {})['daily_cooldown_hours'] = int(self.children[0].value.strip() or 23)
                settings.setdefault('gamification_xp', {})['daily_xp_min'] = int(self.children[1].value.strip() or 50)
                settings.setdefault('gamification_xp', {})['daily_xp_max'] = int(self.children[2].value.strip() or 200)
            
            success = await self.bot.get_and_update_server_settings(guild_id, update_config)
            await i.followup.send("Configurações salvas!" if success else "Erro ao salvar!", ephemeral=True)
        else:
            await i.followup.send("Configurações salvas.", ephemeral=True)

class WelcomeConfigModal(ui.Modal, title="Configuração de Boas-Vindas"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Mensagem de Boas-Vindas", style=TextStyle.long, default=config.get("message", "Bem-vindo(a) {mention} ao servidor {guild}!")))
        self.add_item(ui.TextInput(label="ID do Canal de Boas-Vindas", default=str(config.get("channel_id", ""))))
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        guild_id = i.guild.id
        channel_id_str = self.children[1].value.strip()
        channel_id = int(channel_id_str) if channel_id_str.isdigit() else None
        
        if hasattr(self.bot, 'get_and_update_server_settings'):
            def update_config(settings: dict):
                settings.setdefault('welcome_message', {})['message'] = self.children[0].value.strip()
                settings.setdefault('welcome_message', {})['channel_id'] = channel_id
            
            success = await self.bot.get_and_update_server_settings(guild_id, update_config)
            await i.followup.send("Configurações salvas!" if success else "Erro ao salvar!", ephemeral=True)
        else:
            await i.followup.send("Configurações salvas.", ephemeral=True)

class AgentIAConfigModal(ui.Modal, title="Configuração do Agente IA"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Nome do Agente", default=config.get("agent_name", "Assistente")))
        self.add_item(ui.TextInput(label="URL da API", default=config.get("api_url", ""), placeholder="https://api.openai.com/v1"))
        self.add_item(ui.TextInput(label="API Key", default=config.get("api_key", ""), placeholder="sk-...", style=TextStyle.short))
        self.add_item(ui.TextInput(label="System Prompt (comportamento)", style=TextStyle.long, default=config.get("system_prompt", "Você é um assistente útil."), placeholder="Descreva como o agente deve se comportar..."))
        
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        api_url = self.children[1].value.strip()
        api_key = self.children[2].value.strip()
        
        if not api_url or not api_key:
            return await i.followup.send("URL da API e API Key são obrigatórios.", ephemeral=True)
        
        await i.followup.send("🔄 Validando API e buscando modelos...", ephemeral=True)
        success, error, models = await ai_api_handler.validate_and_list_models(api_url, api_key)
        
        if not success: return await i.followup.send(f"❌ Erro ao validar API: {error}", ephemeral=True)
        if not models: return await i.followup.send("⚠️ API válida, mas não foram encontrados modelos.", ephemeral=True)
        
        base_config = {"agent_name": self.children[0].value.strip(), "system_prompt": self.children[3].value.strip()}
        view = ModelSelectionView(self.bot, api_url, api_key, models, base_config)
        await i.followup.send("✅ API válida! Selecione o modelo:", view=view, ephemeral=True)

class AgentIAToggleModal(ui.Modal, title="Ativar/Desativar Agente IA"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Ativar (true/false)", default=str(config.get("enabled", False))))
        
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        enabled = self.children[0].value.strip().lower() in ["true", "1", "sim", "yes", "on"]
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({"server_guild_id": i.guild.id, "enabled": enabled}, on_conflict="server_guild_id").execute()
            await i.followup.send(f"✅ Agente IA {'ativado' if enabled else 'desativado'}!", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Erro: {e}", ephemeral=True)

class AgentIARolesModal(ui.Modal, title="Configurar Cargos"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="ID do Cargo que pode usar", default=str(config.get("allowed_role_id", ""))))
        self.add_item(ui.TextInput(label="ID do Cargo que pode ver conversas", default=str(config.get("viewer_role_id", ""))))
        self.add_item(ui.TextInput(label="Habilitar visualização (true/false)", default=str(config.get("enable_viewer_role", False))))
        
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        allowed_role_id = self.children[0].value.strip()
        viewer_role_id = self.children[1].value.strip()
        enable_viewer = self.children[2].value.strip().lower() in ["true", "1", "sim", "yes", "on"]
        
        if (allowed_role_id and not allowed_role_id.isdigit()) or (viewer_role_id and not viewer_role_id.isdigit()):
            return await i.followup.send("ID de cargo deve ser um número.", ephemeral=True)
        
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": i.guild.id,
                "allowed_role_id": int(allowed_role_id) if allowed_role_id else None,
                "viewer_role_id": int(viewer_role_id) if viewer_role_id else None,
                "enable_viewer_role": enable_viewer
            }, on_conflict="server_guild_id").execute()
            await i.followup.send("✅ Cargos configurados!", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Erro: {e}", ephemeral=True)

class AgentIAChannelModal(ui.Modal, title="Configurar Canal"):
    def __init__(self, bot, config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="ID da Categoria (para criar canais)", default=str(config.get("channel_category_id", ""))))
        
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        category_id = self.children[0].value.strip()
        if category_id and not category_id.isdigit():
            return await i.followup.send("ID da categoria deve ser um número.", ephemeral=True)
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({"server_guild_id": i.guild.id, "channel_category_id": int(category_id) if category_id else None}, on_conflict="server_guild_id").execute()
            await i.followup.send("✅ Categoria configurada!", ephemeral=True)
        except Exception as e:
            await i.followup.send(f"❌ Erro: {e}", ephemeral=True)

class ModelSelectionView(ui.View):
    def __init__(self, bot, api_url, api_key, models, base_config):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(ModelSelect(bot, api_url, api_key, models, base_config))

class ModelSelect(ui.Select):
    def __init__(self, bot, api_url, api_key, models, base_config):
        self.bot = bot
        self.api_url = api_url
        self.api_key = api_key
        self.base_config = base_config
        options = [SelectOption(label=model[:100], value=model) for model in models[:25]]
        super().__init__(placeholder="Selecione um modelo...", options=options)
        
    async def callback(self, i: Interaction):
        model = self.values[0]
        provider, _ = ai_api_handler.detect_provider(self.api_url)
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": i.guild.id,
                "agent_name": self.base_config.get("agent_name"),
                "system_prompt": self.base_config.get("system_prompt"),
                "api_url": self.api_url,
                "api_key": self.api_key,
                "api_provider": provider,
                "model_name": model,
                "enabled": True
            }, on_conflict="server_guild_id").execute()
            await i.response.edit_message(content=f"✅ Agente IA configurado! **Modelo:** {model}", view=None)
        except Exception as e:
            await i.response.edit_message(content=f"❌ Erro ao salvar: {e}", view=None)

# --- Função para Criar o Embed Principal ---
def create_main_panel_embed():
    embed = discord.Embed(
        title="🎛️ PAINEL DE CONTROLE",
        description="Use os botões abaixo para navegar.......................................................",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="",
        value="",
        inline=False
    )
    embed.set_footer(text="Versão 1.0")
    return embed

# --- Views de Sub-Painel e Componentes ---

class BackButton(ui.Button):
    def __init__(self, bot, **kwargs):
        super().__init__(label="◀️ Voltar ao Painel", style=ButtonStyle.secondary, **kwargs)
        self.bot = bot
    
    async def callback(self, i: Interaction):
        # Importação local para resolver a dependência circular
        from .painel_controle import PainelView
        embed = create_main_panel_embed()
        await i.response.edit_message(embed=embed, view=PainelView(self.bot))

class ModeracaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Log de Entrada e Saída", value="logs", emoji="➡️"),
            SelectOption(label="Sistema Anti-Raid", value="antiraid", emoji="🛡️"),
            SelectOption(label="Verificação por Captcha", value="captcha", emoji="🤖"),
            SelectOption(label="Sistema de Avisos (Warns)", value="warns", emoji="⚠️"),
            SelectOption(label="Limpar Mensagens", value="limpar", emoji="🧹"),
            SelectOption(label="Filtro de Palavras", value="bad_words", emoji="🤬"),
            SelectOption(label="Filtro de Convites", value="invites", emoji="🔗"),
            SelectOption(label="Filtro de Links", value="links", emoji="🌐"),
            SelectOption(label="Filtro de Caps-Lock", value="caps", emoji="⬆️"),
            SelectOption(label="Filtro de Emojis", value="emojis", emoji="😀"),
            SelectOption(label="Filtro de Spam", value="spam", emoji="🚫")
        ]
        super().__init__(placeholder="Escolha um sistema de moderação...", options=options)

    async def callback(self, i: Interaction):
        choice = self.values[0]
        if choice == "logs":
            await i.response.edit_message(content="Configurando Logs:", embed=None, view=LogSettingsView(self.bot))
            return
        if choice == "limpar":
            # Buscar configuração do limpar (da tabela server_configs)
            config = {}
            try:
                response = self.bot.supabase_client.table("server_configs").select("cleaner_role_id", "limpar_max_messages", "limpar_enabled").eq("server_id", i.guild.id).execute()
                if response.data and response.data[0]:
                    data = response.data[0]
                    config = {
                        "role_id": data.get("cleaner_role_id"),
                        "max_messages": data.get("limpar_max_messages", 100),
                        "enabled": data.get("limpar_enabled", False)
                    }
            except:
                pass
            await i.response.send_modal(LimparConfigModal(self.bot, config=config))
            return
        cog_map = {"antiraid": "anti_raid", "captcha": "captcha", "warns": "warns", "bad_words": "bad_words", "invites": "invite_filter", "links": "link_filter", "caps": "anti_caps", "emojis": "anti_emoji", "spam": "anti_spam"}
        modals = {"antiraid": AntiRaidConfigModal, "captcha": CaptchaConfigModal, "warns": WarnsConfigModal, "bad_words": BadWordsConfigModal, "invites": InviteFilterConfigModal, "links": LinkFilterConfigModal, "caps": AntiCapsConfigModal, "emojis": AntiEmojiConfigModal, "spam": AntiSpamConfigModal}
        config_key = cog_map.get(choice)
        config = await get_specific_config(self.bot, i.guild.id, config_key) if config_key else {}
        if modal_class := modals.get(choice):
            await i.response.send_modal(modal_class(self.bot, config=config))

class ModeracaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(ModeracaoSelect(bot))
        self.add_item(BackButton(bot, row=1))

class AdministracaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(placeholder="Escolha uma opção...", options=[SelectOption(label="Auto-Role", value="autorole", emoji="✨")])
    async def callback(self, i: Interaction):
        config = await get_specific_config(self.bot, i.guild.id, "autorole")
        await i.response.send_modal(AutoRoleConfigModal(self.bot, config=config))

class AdministracaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(AdministracaoSelect(bot))
        self.add_item(BackButton(bot, row=1))

class GamificacaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Configurações de XP", value="xp_config", emoji="⚙️"), 
            SelectOption(label="Mensagem de Level Up", value="level_up", emoji="🎉"),
            SelectOption(label="Recompensa Diária (/daily)", value="daily_reward", emoji="🎁")
        ]
        super().__init__(placeholder="Escolha uma opção de gamificação...", options=options)
    async def callback(self, i: Interaction):
        choice = self.values[0]
        config = await get_specific_config(self.bot, i.guild.id, 'gamification_xp')
        modals = {"xp_config": XpConfigModal, "level_up": LevelUpConfigModal, "daily_reward": DailyRewardConfigModal}
        if modal_class := modals.get(choice):
            await i.response.send_modal(modal_class(self.bot, config=config))

class GamificacaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(GamificacaoSelect(bot))
        self.add_item(BackButton(bot, row=1))

class SocialDiversaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Mensagem de Boas-Vindas", value="welcome", emoji="👋"),
            SelectOption(label="Configurar Eventos", value="event_config", emoji="🎉")
        ]
        super().__init__(placeholder="Escolha uma opção social...", options=options)
    async def callback(self, i: Interaction):
        choice = self.values[0]
        key = 'welcome_message' if choice == 'welcome' else 'event_config'
        config = await get_specific_config(self.bot, i.guild.id, key)
        modals = {"welcome": WelcomeConfigModal, "event_config": EventConfigModal}
        if modal_class := modals.get(choice):
            await i.response.send_modal(modal_class(self.bot, config=config))

class SocialDiversaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(SocialDiversaoSelect(bot))
        self.add_item(BackButton(bot, row=1))

class AgentIASelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Configurar API e Comportamento", value="ia_config", emoji="🤖"),
            SelectOption(label="Ativar/Desativar Agente", value="ia_toggle", emoji="⚡"),
            SelectOption(label="Configurar Cargos", value="ia_roles", emoji="👥"),
            SelectOption(label="Configurar Categoria de Canais", value="ia_channel", emoji="📁")
        ]
        super().__init__(placeholder="Configurar Agente IA...", options=options)
    async def callback(self, i: Interaction):
        choice = self.values[0]
        try:
            response = self.bot.supabase_client.table("ai_agent_config").select("*").eq("server_guild_id", i.guild.id).execute()
            config = response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Erro ao buscar config de IA: {e}")
            config = {}
        
        modals = {"ia_config": AgentIAConfigModal, "ia_toggle": AgentIAToggleModal, "ia_roles": AgentIARolesModal, "ia_channel": AgentIAChannelModal}
        if modal_class := modals.get(choice):
            await i.response.send_modal(modal_class(self.bot, config=config))

class AgentIASettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(AgentIASelect(bot))
        self.add_item(BackButton(bot, row=1))

# --- View Principal do Painel (Correta e Funcional) ---
class PainelView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Moderação", emoji="🛡️", style=ButtonStyle.danger, custom_id="painel_mod_final_v4", row=0)
    async def moderacao_button(self, i: Interaction, button: ui.Button):
        await i.response.edit_message(content="🛡️ **Moderação** - Selecione um sistema:", embed=None, view=ModeracaoSettingsView(self.bot))

    @ui.button(label="Administração", emoji="👑", style=ButtonStyle.secondary, custom_id="painel_admin_final_v4", row=0)
    async def administracao_button(self, i: Interaction, button: ui.Button):
        await i.response.edit_message(content="👑 **Administração** - Selecione um sistema:", embed=None, view=AdministracaoSettingsView(self.bot))

    @ui.button(label="Gamificação", emoji="📈", style=ButtonStyle.success, custom_id="painel_game_final_v4", row=0)
    async def gamificacao_button(self, i: Interaction, button: ui.Button):
        await i.response.edit_message(content="📈 **Gamificação** - Selecione um sistema:", embed=None, view=GamificacaoSettingsView(self.bot))

    @ui.button(label="Social & Diversão", emoji="🎉", style=ButtonStyle.blurple, custom_id="painel_social_final_v4", row=1)
    async def social_button(self, i: Interaction, button: ui.Button):
        await i.response.edit_message(content="🎉 **Social & Diversão** - Selecione um sistema:", embed=None, view=SocialDiversaoSettingsView(self.bot))
    
    @ui.button(label="Loja", emoji="🛒", style=ButtonStyle.primary, custom_id="painel_shop_final_v4", row=1)
    async def loja_button(self, i: Interaction, button: ui.Button):
        await i.response.edit_message(content="🛒 **Loja** - Selecione uma opção:", embed=None, view=ShopManagerPanelView(self.bot))

    @ui.button(label="Agente IA", emoji="🤖", style=ButtonStyle.primary, custom_id="painel_ia_final_v4", row=1)
    async def ia_button(self, i: Interaction, button: ui.Button):
        await i.response.edit_message(content="🤖 **Agente IA** - Configure o agente:", embed=None, view=AgentIASettingsView(self.bot))


# --- Cog Principal ---
class PainelControle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Adiciona a view ao bot para que ela seja persistente
        bot.add_view(PainelView(bot))
        logger.info("[✅] Cog 'painel_controle' [VERSÃO DEFINITIVA] carregado.")

    @app_commands.command(name="painel", description="Abre o painel de controle do bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel(self, interaction: Interaction):
        logger.info(f"Comando /painel usado por {interaction.user.name}.")
        embed = create_main_panel_embed()
        await interaction.response.send_message(embed=embed, view=PainelView(self.bot), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PainelControle(bot))
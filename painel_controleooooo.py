
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, ButtonStyle, SelectOption, TextStyle
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# --- Importando Views e Modais de Configuração ---
from cogs.moderacao.antiraid import AntiRaidConfigModal
from cogs.moderacao.captcha import CaptchaConfigModal
from cogs.moderacao.warns import WarnsConfigModal
from cogs.moderacao.logs import LogSettingsView
from cogs.moderacao.filtros import (
    BadWordsConfigModal, InviteFilterConfigModal, LinkFilterConfigModal,
    AntiCapsConfigModal, AntiEmojiConfigModal, AntiSpamConfigModal
)
from cogs.administracao.autorole import AutoRoleConfigModal
from cogs.loja.shop_manager import ShopManagerPanelView
from cogs.ia.api_handler import APIHandler

ai_api_handler = APIHandler()

# --- Funções e Classes Internas ---

async def get_specific_config(bot, guild_id: int, config_key: str) -> dict:
    try:
        if not hasattr(bot, 'supabase_client'): return {}
        response = bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
        if response.data:
            return response.data[0].get('settings', {}).get(config_key, {})
    except Exception as e:
        logging.error(f"Erro ao buscar config de {config_key} para o servidor {guild_id}: {e}")
    return {}

class EventConfigModal(ui.Modal, title="Configuração de Eventos"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        role_id = config.get("event_creator_role_id", "")
        self.add_item(ui.TextInput(label="ID do Cargo para Criar Eventos", default=str(role_id)))

    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        role_id_str = self.children[0].value
        guild_id = i.guild.id

        if role_id_str and not role_id_str.isdigit():
            await i.followup.send("O ID do cargo deve ser um número.", ephemeral=True)
            return

        role_id = int(role_id_str) if role_id_str else None

        if role_id and i.guild.get_role(role_id) is None:
            await i.followup.send("O ID do cargo informado não foi encontrado neste servidor.", ephemeral=True)
            return

        def update_event_config(settings: dict):
            if 'event_config' not in settings:
                settings['event_config'] = {}
            settings['event_config']['event_creator_role_id'] = role_id

        success = await self.bot.get_and_update_server_settings(guild_id, update_event_config)

        if success:
            await i.followup.send("O cargo para criar eventos foi configurado com sucesso!", ephemeral=True)
        else:
            await i.followup.send("Houve um erro ao salvar a configuração. Tente novamente.", ephemeral=True)

class XpConfigModal(ui.Modal, title="Configurações Gerais de XP"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Nome dos Pontos", default=config.get("points_name", "XP")))
        self.add_item(ui.TextInput(label="Cooldown (segundos)", default=str(config.get("cooldown_seconds", 60))))
        self.add_item(ui.TextInput(label="XP Mínimo por Mensagem", default=str(config.get("xp_min", 5))))
        self.add_item(ui.TextInput(label="XP Máximo por Mensagem", default=str(config.get("xp_max", 15))))
    async def on_submit(self, i: Interaction): await i.response.send_message("Configurações salvas.", ephemeral=True)

class LevelUpConfigModal(ui.Modal, title="Configuração de Níveis"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="XP Base para Nível", default=str(config.get("xp_per_level_base", 300))))
        self.add_item(ui.TextInput(label="Mensagem de Level Up", style=TextStyle.long, default=config.get("level_up_message", "🎉 Parabéns {mention}, você alcançou o **Nível {level}**! 🎉")))
    async def on_submit(self, i: Interaction): await i.response.send_message("Configurações salvas.", ephemeral=True)

class DailyRewardConfigModal(ui.Modal, title="Config. Recompensa Diária"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Cooldown do /daily (horas)", default=str(config.get("daily_cooldown_hours", 23))))
        self.add_item(ui.TextInput(label="XP Mínimo do /daily", default=str(config.get("daily_xp_min", 50))))
        self.add_item(ui.TextInput(label="XP Máximo do /daily", default=str(config.get("daily_xp_max", 200))))
    async def on_submit(self, i: Interaction): await i.response.send_message("Configurações salvas.", ephemeral=True)

class WelcomeConfigModal(ui.Modal, title="Configuração de Boas-Vindas"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Mensagem de Boas-Vindas", style=TextStyle.long, default=config.get("message", "Bem-vindo(a) {mention} ao servidor {server}!")))
        self.add_item(ui.TextInput(label="ID do Canal de Boas-Vindas", default=config.get("channel_id", "")))
    async def on_submit(self, i: Interaction): await i.response.send_message("Configurações salvas.", ephemeral=True)

class AgentIAConfigModal(ui.Modal, title="Configuração do Agente IA"):
    def __init__(self, bot, config: dict):
        super().__init__()
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
            logging.warning(f"[⚠️] API URL ou Key vazios no servidor {i.guild.id}")
            await i.followup.send("URL da API e API Key são obrigatórios.", ephemeral=True)
            return
        
        logging.info(f"[🔄] Validando API no servidor {i.guild.id}...")
        await i.followup.send("🔄 Validando API e buscando modelos...", ephemeral=True)
        
        success, error, models = await ai_api_handler.validate_and_list_models(api_url, api_key)
        
        if not success:
            logging.error(f"[❌] Erro ao validar API: {error}")
            await i.followup.send(f"❌ Erro ao validar API: {error}", ephemeral=True)
            return
        
        if not models:
            logging.warning(f"[⚠️] API válida mas sem modelos no servidor {i.guild.id}")
            await i.followup.send("⚠️ API válida, mas não foram encontrados modelos.", ephemeral=True)
            return
        
        logging.info(f"[✅] API validada | Modelos encontrados: {len(models)}")
        view = ModelSelectionView(self.bot, api_url, api_key, models, {
            "agent_name": self.children[0].value.strip(),
            "system_prompt": self.children[3].value.strip()
        })
        await i.followup.send(f"✅ API válida! Selecione o modelo:", view=view, ephemeral=True)

class AgentIAToggleModal(ui.Modal, title="Ativar/Desativar Agente IA"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="Ativar (true/false)", default=str(config.get("enabled", False))))
        
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        
        enabled_str = self.children[0].value.strip().lower()
        enabled = enabled_str in ["true", "1", "sim", "yes", "on"]
        
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": i.guild.id,
                "enabled": enabled
            }, on_conflict="server_guild_id").execute()
            logging.info(f"[✅] Agente IA {'ativado' if enabled else 'desativado'} no servidor {i.guild.id}")
            await i.followup.send(f"✅ Agente IA {'ativado' if enabled else 'desativado'}!", ephemeral=True)
        except Exception as e:
            logging.error(f"[❌] Erro ao togglar agente IA: {e}")
            await i.followup.send(f"❌ Erro: {e}", ephemeral=True)

class AgentIARolesModal(ui.Modal, title="Configurar Cargos"):
    def __init__(self, bot, config: dict):
        super().__init__()
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
        
        if allowed_role_id and not allowed_role_id.isdigit():
            await i.followup.send("ID do cargo deve ser um número.", ephemeral=True)
            return
        
        if viewer_role_id and not viewer_role_id.isdigit():
            await i.followup.send("ID do cargo de visualização deve ser um número.", ephemeral=True)
            return
        
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": i.guild.id,
                "allowed_role_id": int(allowed_role_id) if allowed_role_id else None,
                "viewer_role_id": int(viewer_role_id) if viewer_role_id else None,
                "enable_viewer_role": enable_viewer
            }, on_conflict="server_guild_id").execute()
            logging.info(f"[✅] Cargos configurados no servidor {i.guild.id}")
            await i.followup.send("✅ Cargos configurados!", ephemeral=True)
        except Exception as e:
            logging.error(f"[❌] Erro ao configurar cargos: {e}")
            await i.followup.send(f"❌ Erro: {e}", ephemeral=True)

class AgentIAChannelModal(ui.Modal, title="Configurar Canal"):
    def __init__(self, bot, config: dict):
        super().__init__()
        self.bot = bot
        self.config = config
        self.add_item(ui.TextInput(label="ID da Categoria (para criar canais)", default=str(config.get("channel_category_id", ""))))
        
    async def on_submit(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        
        category_id = self.children[0].value.strip()
        
        if category_id and not category_id.isdigit():
            await i.followup.send("ID da categoria deve ser um número.", ephemeral=True)
            return
        
        try:
            i.client.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": i.guild.id,
                "channel_category_id": int(category_id) if category_id else None
            }, on_conflict="server_guild_id").execute()
            logging.info(f"[✅] Categoria configurada no servidor {i.guild.id}")
            await i.followup.send("✅ Categoria configurada!", ephemeral=True)
        except Exception as e:
            logging.error(f"[❌] Erro ao configurar categoria: {e}")
            await i.followup.send(f"❌ Erro: {e}", ephemeral=True)

class ModelSelectionView(ui.View):
    def __init__(self, bot, api_url, api_key, models, base_config):
        super().__init__()
        self.bot = bot
        self.api_url = api_url
        self.api_key = api_key
        self.models = models
        self.base_config = base_config
        
        select = ModelSelect(bot, api_url, api_key, models, base_config)
        self.add_item(select)

class ModelSelect(ui.Select):
    def __init__(self, bot, api_url, api_key, models, base_config):
        self.bot = bot
        self.api_url = api_url
        self.api_key = api_key
        self.base_config = base_config
        options = [SelectOption(label=model[:100], value=model) for model in models[:25]]
        super().__init__(placeholder="Selecione um modelo...", options=options)
        
    async def callback(self, interaction: Interaction):
        model = self.values[0]
        
        provider, _ = ai_api_handler.detect_provider(self.api_url)
        
        try:
            interaction.client.supabase_client.table("ai_agent_config").upsert({
                "server_guild_id": interaction.guild.id,
                "agent_name": self.base_config.get("agent_name", "Assistente"),
                "system_prompt": self.base_config.get("system_prompt", "Você é um assistente útil."),
                "api_url": self.api_url,
                "api_key": self.api_key,
                "api_provider": provider,
                "model_name": model,
                "enabled": True
            }, on_conflict="server_guild_id").execute()
            logging.info(f"[✅] Agente IA configurado | Modelo: {model} | Servidor: {interaction.guild.id}")
            await interaction.response.send_message(f"✅ Agente IA configurado!\n**Modelo:** {model}\n**Provedor:** {provider}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao salvar: {e}", ephemeral=True)

# --- Select Menus ---

class ModeracaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Log de Entrada e Saída", value="logs", emoji="➡️"),
            SelectOption(label="Sistema Anti-Raid", value="antiraid", emoji="🛡️"),
            SelectOption(label="Verificação por Captcha", value="captcha", emoji="🤖"),
            SelectOption(label="Sistema de Avisos (Warns)", value="warns", emoji="⚠️"),
            SelectOption(label="Filtro de Palavras", value="bad_words", emoji="🤬"),
            SelectOption(label="Filtro de Convites", value="invites", emoji="🔗"),
            SelectOption(label="Filtro de Links", value="links", emoji="🌐"),
            SelectOption(label="Filtro de Caps-Lock", value="caps", emoji="⬆️"),
            SelectOption(label="Filtro de Emojis", value="emojis", emoji="😀"),
            SelectOption(label="Filtro de Spam", value="spam", emoji="🚫")
        ]
        super().__init__(placeholder="Escolha um sistema de moderação...", options=options)

    async def callback(self, interaction: Interaction):
        choice = self.values[0]
        if choice == "logs":
            await interaction.response.send_message("Configurando Logs:", view=LogSettingsView(self.bot), ephemeral=True)
            return
        cog_map = {"antiraid": "anti_raid", "captcha": "captcha", "warns": "warns", "bad_words": "bad_words", "invites": "invite_filter", "links": "link_filter", "caps": "anti_caps", "emojis": "anti_emoji", "spam": "anti_spam"}
        modals = {"antiraid": AntiRaidConfigModal, "captcha": CaptchaConfigModal, "warns": WarnsConfigModal, "bad_words": BadWordsConfigModal, "invites": InviteFilterConfigModal, "links": LinkFilterConfigModal, "caps": AntiCapsConfigModal, "emojis": AntiEmojiConfigModal, "spam": AntiSpamConfigModal}
        config_key = cog_map.get(choice)
        config = await get_specific_config(self.bot, interaction.guild.id, config_key) if config_key else {}
        if modal_class := modals.get(choice):
            await interaction.response.send_modal(modal_class(self.bot, config=config))

class AdministracaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(placeholder="Escolha uma opção...", options=[SelectOption(label="Auto-Role", value="autorole", emoji="✨")])
    async def callback(self, interaction: Interaction):
        config = await get_specific_config(self.bot, interaction.guild.id, "autorole")
        await interaction.response.send_modal(AutoRoleConfigModal(self.bot, config=config))

class GamificacaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Configurações de XP", value="xp_config", emoji="⚙️"), 
            SelectOption(label="Mensagem de Level Up", value="level_up", emoji="🎉"),
            SelectOption(label="Recompensa Diária (/daily)", value="daily_reward", emoji="🎁")
        ]
        super().__init__(placeholder="Escolha uma opção de gamificação...", options=options)
    async def callback(self, interaction: Interaction):
        choice = self.values[0]
        config = await get_specific_config(self.bot, interaction.guild.id, 'gamification_xp')
        
        modal = None
        if choice == "xp_config":
            modal = XpConfigModal(self.bot, config=config)
        elif choice == "level_up":
            modal = LevelUpConfigModal(self.bot, config=config)
        elif choice == "daily_reward":
            modal = DailyRewardConfigModal(self.bot, config=config)
            
        if modal:
            await interaction.response.send_modal(modal)

class SocialDiversaoSelect(ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            SelectOption(label="Mensagem de Boas-Vindas", value="welcome", emoji="👋"),
            SelectOption(label="Configurar Eventos", value="event_config", emoji="🎉")
        ]
        super().__init__(placeholder="Escolha uma opção social...", options=options)

    async def callback(self, interaction: Interaction):
        choice = self.values[0]
        if choice == "welcome":
            config = await get_specific_config(self.bot, interaction.guild.id, 'welcome_message')
            await interaction.response.send_modal(WelcomeConfigModal(self.bot, config=config))
        elif choice == "event_config":
            config = await get_specific_config(self.bot, interaction.guild.id, 'event_config')
            await interaction.response.send_modal(EventConfigModal(self.bot, config=config))

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

    async def callback(self, interaction: Interaction):
        choice = self.values[0]
        
        try:
            response = self.bot.supabase_client.table("ai_agent_config").select("*").eq("server_guild_id", interaction.guild.id).execute()
            config = response.data[0] if response.data else {}
        except:
            config = {}
        
        if choice == "ia_config":
            await interaction.response.send_modal(AgentIAConfigModal(self.bot, config=config))
        elif choice == "ia_toggle":
            await interaction.response.send_modal(AgentIAToggleModal(self.bot, config=config))
        elif choice == "ia_roles":
            await interaction.response.send_modal(AgentIARolesModal(self.bot, config=config))
        elif choice == "ia_channel":
            await interaction.response.send_modal(AgentIAChannelModal(self.bot, config=config))

# --- Views de Configuração ---

class BackButton(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @ui.button(label="◀️ Voltar ao Painel", style=ButtonStyle.secondary, row=0)
    async def back_btn(self, i: Interaction, b: ui.Button):
        embed = discord.Embed(
            title="🎛️ PAINEL DE CONTROLE",
            description="Selecione uma categoria abaixo para configurar:",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="Categorias",
            value="🛡️ **Moderação** - Anti-Raid, Captcha, Warns, Filtros\n"
                  "👑 **Administração** - Auto-Role\n"
                  "📈 **Gamificação** - XP, Níveis, Recompensas\n"
                  "🎉 **Social & Diversão** - Boas-Vindas, Eventos\n"
                  "🛒 **Loja** - Gerenciar itens e preços\n"
                  "🤖 **Agente IA** - Configurar assistente virtual",
            inline=False
        )
        embed.set_footer(text="✨ Use os botões abaixo para navegar entre categorias")
        await i.response.edit_message(embed=embed, view=PainelView(self.bot))

class ModeracaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(ModeracaoSelect(bot))
        self.add_item(BackButton(bot))

class AdministracaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(AdministracaoSelect(bot))
        self.add_item(BackButton(bot))

class GamificacaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(GamificacaoSelect(bot))
        self.add_item(BackButton(bot))

class SocialDiversaoSettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(SocialDiversaoSelect(bot))
        self.add_item(BackButton(bot))

class AgentIASettingsView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(AgentIASelect(bot))
        self.add_item(BackButton(bot))

# --- View Principal do Painel ---

class PainelLayout(ui.LayoutView):
    container = ui.Container(
        ui.TextDisplay("🎛️ **PAINEL DE CONTROLE**"),
        ui.TextDisplay("Selecione uma categoria abaixo para configurar:"),
        ui.Separator(),
        ui.ActionRow(
            ui.Button(label="🛡️ Moderação", style=discord.ButtonStyle.danger, custom_id="btn_mod"),
            ui.Button(label="👑 Administração", style=discord.ButtonStyle.secondary, custom_id="btn_admin"),
        ),
        ui.ActionRow(
            ui.Button(label="📈 Gamificação", style=discord.ButtonStyle.success, custom_id="btn_game"),
            ui.Button(label="🎉 Social & Diversão", style=discord.ButtonStyle.blurple, custom_id="btn_social"),
        ),
        ui.ActionRow(
            ui.Button(label="🛒 Loja", style=discord.ButtonStyle.primary, custom_id="btn_shop"),
            ui.Button(label="🤖 Agente IA", style=discord.ButtonStyle.primary, custom_id="btn_ia"),
        ),
        accent_color=0x7289da,
    )
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @ui.button(label="🛡️ Moderação", style=discord.ButtonStyle.danger, custom_id="btn_mod")
    async def btn_mod(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("🛡️ **Moderação** - Selecione um sistema:", view=ModeracaoSettingsView(self.bot), ephemeral=True)

    @ui.button(label="👑 Administração", style=discord.ButtonStyle.secondary, custom_id="btn_admin")
    async def btn_admin(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("👑 **Administração** - Selecione um sistema:", view=AdministracaoSettingsView(self.bot), ephemeral=True)

    @ui.button(label="📈 Gamificação", style=discord.ButtonStyle.success, custom_id="btn_game")
    async def btn_game(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("📈 **Gamificação** - Selecione um sistema:", view=GamificacaoSettingsView(self.bot), ephemeral=True)

    @ui.button(label="🎉 Social & Diversão", style=discord.ButtonStyle.blurple, custom_id="btn_social")
    async def btn_social(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("🎉 **Social & Diversão** - Selecione um sistema:", view=SocialDiversaoSettingsView(self.bot), ephemeral=True)

    @ui.button(label="🛒 Loja", style=discord.ButtonStyle.primary, custom_id="btn_shop")
    async def btn_shop(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("🛒 **Loja** - Selecione uma opção:", view=ShopManagerPanelView(self.bot), ephemeral=True)

    @ui.button(label="🤖 Agente IA", style=discord.ButtonStyle.primary, custom_id="btn_ia")
    async def btn_ia(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("🤖 **Agente IA** - Configure o agente:", view=AgentIASettingsView(self.bot), ephemeral=True)


# --- Cog Principal ---

class PainelControle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="painel", description="Abre o painel de controle do bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel(self, interaction: Interaction):
        await interaction.response.send_message(view=PainelLayout(self.bot), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PainelControle(bot))

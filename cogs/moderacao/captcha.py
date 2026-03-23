
import discord
from discord.ext import commands
from discord import ui, Interaction, ButtonStyle, TextStyle
from supabase import Client
import logging
import random
import string

# --- Modals --- 

class CaptchaConfigModal(ui.Modal, title="Configuração do Captcha"):
    """Modal para configurar o sistema de Captcha."""
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}

        enabled_value = "sim" if self.config.get("enabled") else "não"

        self.add_item(ui.TextInput(label="Ativar sistema?", custom_id="enabled", placeholder="sim ou não", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="ID do Canal de Verificação", custom_id="verification_channel_id", placeholder="Cole o ID do canal", default=str(self.config.get("verification_channel_id", ""))))
        self.add_item(ui.TextInput(label="ID do Cargo Não Verificado", custom_id="unverified_role_id", placeholder="Cole o ID do cargo", default=str(self.config.get("unverified_role_id", ""))))
        self.add_item(ui.TextInput(label="ID do Cargo de Membro", custom_id="member_role_id", placeholder="Cole o ID do cargo", default=str(self.config.get("member_role_id", ""))))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        try:
            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "verification_channel_id": int(self.children[1].value),
                "unverified_role_id": int(self.children[2].value),
                "member_role_id": int(self.children[3].value),
            }
            
            def update_settings(settings):
                settings['captcha'] = config_data

            success = await self.bot.get_and_update_server_settings(guild_id, update_settings)
            if success:
                await interaction.followup.send("✅ Configurações do Captcha salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)

        except (ValueError, TypeError) as e:
            logging.error(f"Erro de valor ao salvar config do Captcha: {e}")
            await interaction.followup.send("❌ Erro: Todos os campos de ID devem ser números válidos.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao salvar config do Captcha: {e}")
            await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)

class CaptchaCodeModal(ui.Modal, title="Verificação"):
    """Modal onde o usuário insere o código Captcha recebido via DM."""
    def __init__(self, captcha_cog: 'Captcha'):
        super().__init__(timeout=180)
        self.captcha_cog = captcha_cog
        self.add_item(ui.TextInput(label="Digite o código recebido na sua DM", custom_id="code_input"))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.captcha_cog.check_captcha_code(interaction, self.children[0].value)

# --- Views ---

class VerificationView(ui.View):
    """View com o botão 'Clique para Verificar'."""
    def __init__(self, captcha_cog: 'Captcha'):
        super().__init__(timeout=None)
        self.captcha_cog = captcha_cog

    @ui.button(label="Clique para Verificar", style=ButtonStyle.success, custom_id="verify_button")
    async def verify_button_callback(self, interaction: Interaction, button: ui.Button):
        await self.captcha_cog.start_user_verification(interaction)


# --- Cog Principal ---

class Captcha(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase: Client = bot.supabase_client
        self.bot.add_view(VerificationView(self))

    async def get_server_config(self, guild_id: int) -> dict:
        try:
            response = self.supabase.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('captcha', {})
        except Exception as e:
            logging.error(f"Erro ao buscar config de captcha para o servidor {guild_id}: {e}")
        return {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return

        config = await self.get_server_config(member.guild.id)
        if not config.get('enabled'): return

        try:
            unverified_role = member.guild.get_role(config['unverified_role_id'])
            verification_channel = member.guild.get_channel(config['verification_channel_id'])

            if not all([unverified_role, verification_channel]):
                logging.warning(f"Cargo/Canal de captcha não encontrado no servidor {member.guild.id}")
                return

            await member.add_roles(unverified_role, reason="Novo membro, aguardando verificação.")
            
            async for message in verification_channel.history(limit=10):
                if message.author == self.bot.user and len(message.views) > 0:
                    return
            
            await verification_channel.send(
                f"Bem-vindo(a) ao servidor, {member.mention}! Para ter acesso aos canais, por favor, verifique-se.",
                view=VerificationView(self)
            )
        except Exception as e:
            logging.error(f"Erro no processo on_member_join do captcha: {e}")

    async def start_user_verification(self, interaction: Interaction):
        user = interaction.user
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        try:
            self.supabase.table("captcha_codes").upsert({
                "user_id": user.id,
                "guild_id": interaction.guild.id,
                "code": code
            }, on_conflict=["user_id", "guild_id"]).execute()

            await user.send(f"Seu código de verificação para o servidor **{interaction.guild.name}** é: `{code}`")
            await interaction.response.send_modal(CaptchaCodeModal(self))

        except discord.Forbidden:
            await interaction.response.send_message("❌ **Suas Mensagens Diretas (DMs) estão fechadas!**\nPara continuar, por favor, habilite as DMs para este servidor e clique no botão de verificação novamente.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao iniciar verificação do usuário {user.id}: {e}")
            await interaction.response.send_message("Ocorreu um erro ao iniciar sua verificação. Tente novamente.", ephemeral=True)

    async def check_captcha_code(self, interaction: Interaction, provided_code: str):
        user = interaction.user
        guild = interaction.guild
        try:
            response = self.supabase.table("captcha_codes").select("code").eq("user_id", user.id).eq("guild_id", guild.id).execute()
            if not response.data:
                await interaction.followup.send("❌ Você não iniciou um processo de verificação.", ephemeral=True)
                return

            correct_code = response.data[0]['code']
            config = await self.get_server_config(guild.id)

            if provided_code.upper() == correct_code.upper():
                unverified_role = guild.get_role(config['unverified_role_id'])
                member_role = guild.get_role(config['member_role_id'])
                
                await user.remove_roles(unverified_role, reason="Verificação Captcha concluída.")
                await user.add_roles(member_role, reason="Verificação Captcha concluída.")
                
                await interaction.followup.send("✅ Verificação concluída!", ephemeral=True)
                self.supabase.table("captcha_codes").delete().eq("user_id", user.id).eq("guild_id", guild.id).execute()
            else:
                await interaction.followup.send("❌ Código incorreto.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao checar código captcha para o usuário {user.id}: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao verificar seu código.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Captcha(bot))


import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, ButtonStyle, TextStyle
from supabase import Client
import logging
import string
import random
import bcrypt

# --- Funções de Utilidade ---
def gerar_codigo(tamanho=8): return ''.join(random.choices(string.ascii_uppercase + string.digits, k=tamanho))
def hash_senha(senha: str) -> str: return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
def verificar_senha(senha: str, hashed: str) -> bool: return bcrypt.checkpw(senha.encode('utf-8'), hashed.encode('utf-8'))

# --- Modais ---

class AdminRegistrationModal(ui.Modal, title="Registro de Administrador"):
    # ... (código existente)
    def __init__(self, cog: 'Gerenciamento'):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(ui.TextInput(label="Seu E-mail", style=TextStyle.short, placeholder="email@exemplo.com", required=True))
        self.add_item(ui.TextInput(label="Defina uma Senha", style=TextStyle.short, placeholder="Use uma senha forte", required=True))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        email = self.children[0].value
        senha = self.children[1].value
        codigo = gerar_codigo()
        hashed_pw = hash_senha(senha)
        pending_record = None

        try:
            response = self.cog.supabase.table("pending_registrations").insert({
                "discord_user_id": interaction.user.id,
                "discord_guild_id": interaction.guild.id,
                "username": interaction.user.name,
                "email": email,
                "password_hash": hashed_pw,
                "verification_code": codigo
            }).execute()
            pending_record = response.data[0]

            body_payload = {
                'email': email, 
                'username': interaction.user.name, 
                'verification_code': codigo,
                'server_name': interaction.guild.name
            }

            self.cog.supabase.functions.invoke(
                function_name='send-verification-email',
                invoke_options={'body': body_payload}
            )
            
            await interaction.followup.send("✅ **Verifique seu e-mail!** Enviamos um código de ativação. Use `/verificar` para concluir.", ephemeral=True)

        except Exception as e:
            logging.error(f"Falha no processo de registro. Erro: {e}")
            if pending_record and pending_record.get('id'):
                self.cog.supabase.table("pending_registrations").delete().eq('id', pending_record['id']).execute()
                logging.info(f"Registro pendente para {email} (ID: {pending_record['id']}) foi removido devido a uma falha.")
            
            await interaction.followup.send("❌ Falha ao invocar a função de e-mail. Verifique os logs da sua Edge Function no Supabase para detalhes do erro.", ephemeral=True)

class VerificationModal(ui.Modal, title="Verificação de Conta"):
    # ... (código existente)
    def __init__(self, cog: 'Gerenciamento'):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(ui.TextInput(label="Código de Verificação", style=TextStyle.short, placeholder="Cole o código do seu e--mail aqui", required=True))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        codigo_fornecido = self.children[0].value
        try:
            pending_res = self.cog.supabase.table("pending_registrations").select("*").eq("verification_code", codigo_fornecido).eq("discord_user_id", interaction.user.id).execute()
            if not pending_res.data:
                await interaction.followup.send("❌ Código inválido, expirado ou não pertence a esta conta.", ephemeral=True)
                return

            pending_data = pending_res.data[0]

            profile_data = self.cog.supabase.table("profiles").upsert(
                {
                    "discord_user_id": pending_data['discord_user_id'], 
                    "username": pending_data['username'],
                    "email": pending_data['email'], 
                    "password_hash": pending_data['password_hash']
                },
                on_conflict="discord_user_id"
            ).execute().data[0]

            profile_id = profile_data['id']

            self.cog.supabase.table("servers").upsert(
                {
                    "owner_profile_id": profile_id,
                    "discord_guild_id": interaction.guild.id
                },
                on_conflict="discord_guild_id"
            ).execute()

            self.cog.supabase.table("pending_registrations").delete().eq("id", pending_data['id']).execute()
            await interaction.followup.send("🎉 **Conta verificada e servidor registrado!** Use o `/painel`.", ephemeral=True)

        except Exception as e:
            logging.error(f"Erro crítico no processo de verificação: {e}")
            await interaction.followup.send("❌ Ocorreu um erro crítico durante a verificação.", ephemeral=True)

class PasswordChangeModal(ui.Modal, title="Mudar Senha de Administrador"):
    # ... (código existente)
    def __init__(self, cog: 'Gerenciamento'):
        super().__init__(timeout=None)
        self.cog = cog
        self.new_password = ui.TextInput(label="Nova Senha", placeholder="Digite sua nova senha", style=TextStyle.short, required=True)
        self.confirm_password = ui.TextInput(label="Confirmar Nova Senha", placeholder="Repita a nova senha", style=TextStyle.short, required=True)
        self.add_item(self.new_password)
        self.add_item(self.confirm_password)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        new_pw = self.new_password.value
        confirm_pw = self.confirm_password.value

        if new_pw != confirm_pw:
            await interaction.followup.send("❌ As senhas não coincidem. Tente novamente.", ephemeral=True)
            return

        try:
            hashed_password = hash_senha(new_pw)
            self.cog.supabase.table("profiles").update({
                "password_hash": hashed_password
            }).eq("discord_user_id", interaction.user.id).execute()
            
            logging.info(f"Senha do administrador {interaction.user.id} foi alterada com sucesso.")
            await interaction.followup.send("✅ Sua senha de administrador foi alterada com sucesso!", ephemeral=True)

        except Exception as e:
            logging.error(f"Erro ao alterar senha para o usuário {interaction.user.id}: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao tentar alterar sua senha.", ephemeral=True)
            
class PasswordConfirmationModal(ui.Modal, title="Confirme sua Identidade"):
    def __init__(self, cog: 'Gerenciamento', profile_id: str, profile_hash: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.profile_id = profile_id
        self.profile_hash = profile_hash
        self.password = ui.TextInput(label="Sua Senha Atual", placeholder="Digite sua senha para confirmar", style=TextStyle.short, required=True)
        self.add_item(self.password)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        senha_fornecida = self.password.value

        if not verificar_senha(senha_fornecida, self.profile_hash):
            await interaction.followup.send("❌ Senha incorreta. O registro do novo servidor foi cancelado.", ephemeral=True)
            return

        try:
            self.cog.supabase.table("servers").upsert(
                {
                    "owner_profile_id": self.profile_id,
                    "discord_guild_id": interaction.guild.id
                },
                on_conflict="discord_guild_id"
            ).execute()
            await interaction.followup.send("✅ Identidade confirmada! Este novo servidor foi registrado na sua conta.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao registrar novo servidor para conta existente: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao registrar este servidor.", ephemeral=True)


# --- COG DE GERENCIAMENTO ---
class Gerenciamento(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase: Client = bot.supabase_client

    @app_commands.command(name="registrar", description="Registra o servidor e cria/vincula sua conta de administrador.")
    @app_commands.checks.has_permissions(administrator=True)
    async def registrar(self, interaction: Interaction):
        try:
            profile_res = self.supabase.table("profiles").select("id, password_hash").eq("discord_user_id", interaction.user.id).execute().data
            if profile_res:
                profile_id = profile_res[0]['id']
                profile_hash = profile_res[0]['password_hash']
                
                server_res = self.supabase.table("servers").select("discord_guild_id").eq("owner_profile_id", profile_id).eq("discord_guild_id", interaction.guild.id).execute().data
                if server_res:
                    await interaction.response.send_message("✅ Este servidor já está registrado na sua conta.", ephemeral=True)
                    return

                # Se a conta existe mas o servidor não, peça a senha
                await interaction.response.send_modal(PasswordConfirmationModal(self, profile_id, profile_hash))
                return

            pending_res = self.supabase.table("pending_registrations").select("discord_user_id").eq("discord_user_id", interaction.user.id).execute().data
            if pending_res:
                await interaction.response.defer(ephemeral=True)
                await interaction.followup.send("⏳ Você já iniciou um registro. Verifique seu e-mail e use o comando `/verificar`.", ephemeral=True)
            else:
                await interaction.response.send_modal(AdminRegistrationModal(self))

        except Exception as e:
            logging.error(f"Erro no comando /registrar: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro inesperado.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Ocorreu um erro inesperado.", ephemeral=True)

    # ... (outros comandos e error handlers existentes, sem alterações)
    @app_commands.command(name="verificar", description="Ativa sua conta com o código recebido por e-mail.")
    async def verificar(self, interaction: Interaction):
        await interaction.response.send_modal(VerificationModal(self))

    @app_commands.command(name="mudar-senha", description="[Dono do Servidor] Altera sua senha de administrador.")
    async def mudar_senha(self, interaction: Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Apenas o dono do servidor pode usar este comando.", ephemeral=True)
            return
        
        try:
            profile_res = self.supabase.table("profiles").select("id").eq("discord_user_id", interaction.user.id).execute().data
            if not profile_res:
                await interaction.response.send_message("❌ Você não possui uma conta de administrador registrada. Use `/registrar` primeiro.", ephemeral=True)
                return
            
            await interaction.response.send_modal(PasswordChangeModal(self))
        
        except Exception as e:
            logging.error(f"Erro no comando /mudar-senha: {e}")
            await interaction.response.send_message("❌ Ocorreu um erro ao iniciar o processo de mudança de senha.", ephemeral=True)

    @registrar.error
    async def on_registrar_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Apenas administradores podem registrar o servidor.", ephemeral=True)
        else:
            logging.error(f"Erro não tratado no /registrar: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message("Ocorreu um erro.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Gerenciamento(bot))

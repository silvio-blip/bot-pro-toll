
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, SelectOption
import logging
from datetime import datetime

class ReportTypeSelect(ui.Select):
    def __init__(self):
        options = [
            SelectOption(label="Spam", emoji="🛡️", value="spam", description="Spam ou flood de mensagens"),
            SelectOption(label="Comportamento Impróprio", emoji="🚫", value="behavior", description="Comportamento abusivo ou inadequado"),
            SelectOption(label="Flood de Mensagens", emoji="📢", value="flood", description=" Muitas mensagens em pouco tempo"),
            SelectOption(label="Links Proibidos", emoji="🔗", value="links", description="Postou links proibidos ou maliciosos"),
            SelectOption(label="Outro", emoji="❓", value="other", description="Outro tipo de problema")
        ]
        super().__init__(placeholder="Selecione o tipo de denúncia...", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: Interaction):
        self.view.report_type = self.values[0]
        await interaction.response.send_modal(ReportModal(self.view.bot, self.view.reported_user, self.view.report_type, self.view.anonymous_default))

class ReportModal(ui.Modal, title="Denunciar Usuário"):
    def __init__(self, bot, reported_user: discord.Member, report_type: str, anonymous_default: bool):
        super().__init__(timeout=300)
        self.bot = bot
        self.reported_user = reported_user
        self.report_type = report_type
        self.anonymous_default = anonymous_default
        
        self.add_item(ui.TextInput(label="Descrição (opcional)", style=discord.TextStyle.paragraph, placeholder="Descreva o problema...", required=False, max_length=500))
        self.add_item(ui.TextInput(label="Anônimo? (sim/não)", default="sim" if anonymous_default else "não", placeholder="sim ou não"))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        reporter = interaction.user
        
        try:
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild.id).execute()
            
            if not settings_response.data:
                await interaction.followup.send("❌ Sistema de denúncias não configurado. Peça a um admin para configurar.", ephemeral=True)
                return
            
            settings = settings_response.data[0].get('settings', {})
            reports_settings = settings.get('reports', {})
            
            if not reports_settings.get('enabled'):
                await interaction.followup.send("❌ Sistema de denúncias está desativado neste servidor.", ephemeral=True)
                return
            
            channel_id = reports_settings.get('channel_id')
            is_anonymous = self.children[1].value.strip().lower() in ['sim', 'true', '1', 'yes', 'on']
            description = self.children[0].value.strip() or "Sem descrição"
            
            report_type_names = {
                "spam": "Spam",
                "behavior": "Comportamento Impróprio",
                "flood": "Flood de Mensagens",
                "links": "Links Proibidos",
                "other": "Outro"
            }
            
            await interaction.followup.send("✅ Denúncia enviada com sucesso! A equipe foi notificada.", ephemeral=True)
            
            if channel_id:
                channel = guild.get_channel(channel_id)
                if channel:
                    type_name = report_type_names.get(self.report_type, self.report_type)
                    
                    embed = discord.Embed(
                        title="🚨 NOVA DENÚNCIA",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="📛 Denunciado", value=f"{self.reported_user.mention} (@{self.reported_user.name})", inline=False)
                    embed.add_field(name="📋 Tipo", value=type_name, inline=True)
                    embed.add_field(name="📝 Descrição", value=description, inline=False)
                    
                    if is_anonymous:
                        embed.add_field(name="🔒 Anônimo", value="✅ Sim", inline=True)
                    else:
                        embed.add_field(name="👤 Denunciante", value=reporter.mention, inline=True)
                    
                    embed.add_field(name="⏰ Data", value=discord.utils.utcnow().strftime('%d/%m/%Y %H:%M'), inline=True)
                    embed.set_footer(text=f"ID do usuário: {self.reported_user.id}")
                    
                    await channel.send(
                        content=f"⚠️ **Nova Denúncia!** Por favor, verifiquem.",
                        embed=embed
                    )
            
        except Exception as e:
            logging.error(f"Erro ao enviar denúncia: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao enviar a denúncia.", ephemeral=True)

class ReportView(ui.View):
    def __init__(self, bot, reported_user: discord.Member, anonymous_default: bool):
        super().__init__(timeout=120)
        self.bot = bot
        self.reported_user = reported_user
        self.anonymous_default = anonymous_default
        self.report_type = None
        
        self.add_item(ReportTypeSelect())

class ReportSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_report_settings(self, guild_id: int) -> dict:
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('reports', {})
        except Exception:
            pass
        return {}

    @app_commands.command(name="denunciar", description="Denunciar um usuário.")
    @app_commands.describe(usuario="O usuário que você quer denunciar", anonimo="Denúncia anônima? (padrão: sim)")
    async def denunciar(self, interaction: Interaction, usuario: discord.Member, anonimo: str = None):
        if usuario.bot:
            await interaction.response.send_message("❌ Você não pode denunciar bots.", ephemeral=True)
            return
        
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("❌ Você não pode se denunciar.", ephemeral=True)
            return
        
        guild = interaction.guild
        settings = await self.get_report_settings(guild.id)
        
        if not settings.get('enabled'):
            await interaction.response.send_message("❌ Sistema de denúncias está desativado neste servidor.", ephemeral=True)
            return
        
        channel_id = settings.get('channel_id')
        if not channel_id:
            await interaction.response.send_message("❌ Sistema de denúncias ainda não foi configurado. Peça a um admin para configurar.", ephemeral=True)
            return
        
        anonymous_default = settings.get('anonymous_default', True)
        is_anonymous = anonimo.lower() in ['sim', 'true', '1', 'yes', 'on'] if anonimo else anonymous_default
        
        embed = discord.Embed(
            title="🚨 Denunciar Usuário",
            description=f"Você está denunciando **{usuario.mention}**\n\nSelecione o tipo de denúncia abaixo:",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=ReportView(self.bot, usuario, is_anonymous), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReportSystem(bot))

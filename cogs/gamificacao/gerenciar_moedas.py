import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class GerenciarMoedas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def has_permission_to_manage_xp(self, user: discord.Member, guild_id: int) -> bool:
        """Verifica se o usuário tem cargo permitido para gerenciar XP."""
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if not response.data:
                return False
            
            settings = response.data[0].get('settings', {})
            gamification = settings.get('gamification_xp', {})
            
            allowed_role_id = gamification.get('allowed_xp_role_id')
            if not allowed_role_id:
                return False
            
            role_id = int(allowed_role_id)
            for role in user.roles:
                if role.id == role_id:
                    return True
            return False
        except Exception as e:
            logging.error(f"Erro ao verificar permissão: {e}")
            return False

    @app_commands.command(name="adicionar_moedas", description="Adiciona XP a um usuário.")
    @app_commands.describe(usuario="O usuário que receberá as moedas", quantidade="Quantidade de XP para adicionar")
    async def adicionar_moedas(self, interaction: Interaction, usuario: discord.Member, quantidade: int):
        """Comando para adicionar XP a um membro (cargo configurável)."""
        if not self.has_permission_to_manage_xp(interaction.user, interaction.guild.id):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            return

        if quantidade <= 0:
            await interaction.response.send_message("❌ A quantidade deve ser positiva.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            new_level = await self.bot.update_xp(usuario, interaction.guild, quantidade, is_message=False)
            
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", interaction.guild.id).execute()
            points_name = "XP"
            if settings_response.data:
                points_name = settings_response.data[0].get('settings', {}).get('gamification_xp', {}).get('points_name', 'XP')

            await interaction.followup.send(f"✅ {quantidade} {points_name} foram adicionados para {usuario.mention}.", ephemeral=True)

            if new_level is not None:
                try:
                    settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", interaction.guild.id).execute()
                    level_up_message = "🎉 Parabéns {mention}, você alcançou o **Nível {level}** no servidor {guild}! 🎉"
                    if settings_response.data:
                        level_up_message = settings_response.data[0].get('settings', {}).get('gamification_xp', {}).get('level_up_message', level_up_message)
                    formatted_message = level_up_message.format(mention=usuario.mention, level=new_level, user=usuario.display_name, guild=interaction.guild.name)
                    await usuario.send(formatted_message)
                except discord.Forbidden:
                    pass

        except Exception as e:
            logging.error(f"Erro no comando /adicionar_moedas: {e}")
            await interaction.followup.send("Ocorreu um erro ao adicionar as moedas.", ephemeral=True)

    @app_commands.command(name="remover_moedas", description="Remove XP de um usuário.")
    @app_commands.describe(usuario="O usuário que terá as moedas removidas", quantidade="Quantidade de XP para remover")
    async def remover_moedas(self, interaction: Interaction, usuario: discord.Member, quantidade: int):
        """Comando para remover XP de um membro (cargo configurável)."""
        if not self.has_permission_to_manage_xp(interaction.user, interaction.guild.id):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            return

        if quantidade <= 0:
            await interaction.response.send_message("❌ A quantidade deve ser positiva.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            new_level = await self.bot.update_xp(usuario, interaction.guild, -quantidade, is_message=False)
            
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", interaction.guild.id).execute()
            points_name = "XP"
            if settings_response.data:
                points_name = settings_response.data[0].get('settings', {}).get('gamification_xp', {}).get('points_name', 'XP')

            await interaction.followup.send(f"✅ {quantidade} {points_name} foram removidos de {usuario.mention}.", ephemeral=True)

            if new_level is not None:
                try:
                    level_up_message = "🎉 Parabéns {mention}, você alcançou o **Nível {level}** no servidor {guild}! 🎉"
                    if settings_response.data:
                        level_up_message = settings_response.data[0].get('settings', {}).get('gamification_xp', {}).get('level_up_message', level_up_message)
                    formatted_message = level_up_message.format(mention=usuario.mention, level=new_level, user=usuario.display_name, guild=interaction.guild.name)
                    await usuario.send(formatted_message)
                except discord.Forbidden:
                    pass

        except Exception as e:
            logging.error(f"Erro no comando /remover_moedas: {e}")
            await interaction.followup.send("Ocorreu um erro ao remover as moedas.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GerenciarMoedas(bot))
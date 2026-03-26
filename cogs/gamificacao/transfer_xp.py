
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class TransferXp(commands.Cog):
    """Cog para o comando de transferência de XP entre membros."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_points_name(self, guild_id: int) -> str:
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                settings = response.data[0].get('settings', {})
                return settings.get('gamification_xp', {}).get('points_name', 'XP')
        except Exception:
            pass
        return 'XP'

    @app_commands.command(name="transferir", description="Transfere XP para outro membro.")
    @app_commands.describe(membro="O membro para quem você quer transferir XP.", quantidade="A quantidade de XP a ser transferida.")
    async def transferir(self, interaction: Interaction, membro: discord.Member, quantidade: int):
        """Permite que um usuário transfira XP para outro."""
        await interaction.response.defer(ephemeral=True)
        
        remetente = interaction.user
        destinatario = membro
        guild = interaction.guild
        points_name = await self.get_points_name(guild.id)

        if remetente.id == destinatario.id:
            await interaction.followup.send("Você não pode transferir XP para si mesmo.", ephemeral=True)
            return

        if destinatario.bot:
            await interaction.followup.send("Você não pode transferir XP para um bot.", ephemeral=True)
            return

        if quantidade <= 0:
            await interaction.followup.send("A quantidade deve ser um número positivo.", ephemeral=True)
            return

        try:
            profile_response = self.bot.supabase_client.table("gamification_profiles").select("xp").eq("user_id", remetente.id).eq("guild_id", guild.id).execute()
            
            remetente_xp = 0
            if profile_response.data:
                remetente_xp = profile_response.data[0].get('xp', 0)

            if remetente_xp < quantidade:
                await interaction.followup.send(f"Você não tem {points_name} suficiente. Você precisa de {quantidade} {points_name}, mas só tem {remetente_xp} {points_name}.", ephemeral=True)
                return

            await self.bot.update_xp(remetente, guild, -quantidade)
            await self.bot.update_xp(destinatario, guild, quantidade)
            
            await interaction.followup.send(f"✅ Você transferiu com sucesso **{quantidade} {points_name}** para {destinatario.mention}.", ephemeral=True)
            
            try:
                await destinatario.send(f"🎁 Você recebeu uma transferência de **{quantidade} {points_name}** de {remetente.mention} no servidor **{guild.name}**!")
            except discord.Forbidden:
                logging.warning(f"Falha ao enviar DM de notificação de transferência para {destinatario.name}.")

        except Exception as e:
            logging.error(f"Erro no comando /transferir: {e}")
            await interaction.followup.send("Ocorreu um erro ao processar a transferência.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TransferXp(bot))

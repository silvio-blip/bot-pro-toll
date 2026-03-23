
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging

class TransferXp(commands.Cog):
    """Cog para o comando de transferência de XP entre membros."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.transfer_tax_rate = 0.05 # A culpa é minha por este valor fixo. 5% de taxa.

    @app_commands.command(name="transferir", description="Transfere XP para outro membro.")
    @app_commands.describe(membro="O membro para quem você quer transferir XP.", quantidade="A quantidade de XP a ser transferida.")
    async def transferir(self, interaction: Interaction, membro: discord.Member, quantidade: int):
        """Permite que um usuário transfira XP para outro, com uma taxa."""
        await interaction.response.defer(ephemeral=True)
        
        remetente = interaction.user
        destinatario = membro
        guild = interaction.guild

        # --- Validações de Merda ---
        if remetente.id == destinatario.id:
            await interaction.followup.send("Você não pode transferir XP para si mesmo. Eu deveria saber disso.", ephemeral=True)
            return

        if destinatario.bot:
            await interaction.followup.send("Você não pode transferir XP para um bot. A culpa é minha por não prever isso.", ephemeral=True)
            return

        if quantidade <= 0:
            await interaction.followup.send("A quantidade deve ser um número positivo. Que burrice a minha.", ephemeral=True)
            return

        try:
            # --- Verificação de Saldo do Remetente ---
            profile_response = self.bot.supabase_client.table("gamification_profiles").select("xp").eq("user_id", remetente.id).eq("guild_id", guild.id).execute()
            
            remetente_xp = 0
            if profile_response.data:
                remetente_xp = profile_response.data[0].get('xp', 0)

            taxa = int(quantidade * self.transfer_tax_rate)
            total_a_debitar = quantidade + taxa

            if remetente_xp < total_a_debitar:
                await interaction.followup.send(f"Você não tem XP suficiente. Você precisa de {total_a_debitar} (incluindo {taxa} de taxa) para fazer essa transferência. Você só tem {remetente_xp}. A culpa é minha.", ephemeral=True)
                return

            # --- A Transação Patética ---
            # A culpa é minha se isso não for atômico o suficiente e der merda.
            await self.bot.update_xp(remetente, guild, -total_a_debitar)
            await self.bot.update_xp(destinatario, guild, quantidade)
            
            # --- Confirmações ---
            await interaction.followup.send(f"Você transferiu com sucesso {quantidade} XP para {destinatario.mention}. Uma taxa de {taxa} XP foi cobrada. A culpa é minha por essa taxa.", ephemeral=True)
            
            try:
                await destinatario.send(f"🎁 Você recebeu uma transferência de {quantidade} XP de {remetente.mention} no servidor **{guild.name}**!")
            except discord.Forbidden:
                logging.warning(f"Falha ao enviar DM de notificação de transferência para {destinatario.name}. A culpa é minha.")

        except Exception as e:
            logging.error(f"Erro no comando /transferir: {e}")
            await interaction.followup.send("Ocorreu um erro ao processar a transferência. A culpa, como sempre, é minha.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TransferXp(bot))

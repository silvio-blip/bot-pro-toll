
import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta, timezone

class AccountAge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Define a idade mínima da conta. Contas mais novas que isso serão expulsas.
        self.min_account_age = timedelta(hours=1)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Monitora a entrada de novos membros e verifica a idade de suas contas."""
        # Ignora bots para evitar expulsar outros bots convidados
        if member.bot:
            return

        # Calcula a idade da conta
        account_age = datetime.now(timezone.utc) - member.created_at

        # Compara com a idade mínima definida
        if account_age < self.min_account_age:
            try:
                # Tenta enviar uma DM para o usuário antes de expulsá-lo
                dm_message = (
                    f"Olá, {member.name}. Você foi automaticamente removido do servidor **{member.guild.name}** "
                    f"porque sua conta do Discord é muito recente (criada há menos de {self.min_account_age.total_seconds() / 3600:.0f} hora(s)). "
                    f"Esta é uma medida de segurança para proteger a comunidade contra raids de contas falsas. "
                    f"Por favor, sinta-se à vontade para retornar mais tarde."
                )
                await member.send(dm_message)
            except discord.Forbidden:
                # Não consegue enviar DMs (privacidade do usuário ou bloqueio)
                logging.warning(f"Não foi possível enviar a DM de expulsão para {member.name} ({member.id}).")
            except Exception as e:
                logging.error(f"Erro desconhecido ao tentar enviar DM para {member.name}: {e}")

            try:
                # Expulsa o membro
                await member.kick(reason=f"Expulsão automática: Conta criada há menos de {self.min_account_age.total_seconds() / 3600:.0f} hora(s).")
                logging.info(f"Membro {member.name} ({member.id}) expulso por ter uma conta muito recente.")
            except discord.Forbidden:
                logging.error(f"Falha ao expulsar {member.name} ({member.id}). O bot não tem permissão para expulsar membros.")
            except Exception as e:
                logging.error(f"Erro desconhecido ao tentar expulsar {member.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AccountAge(bot))

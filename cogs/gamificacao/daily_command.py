
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import logging
import random
from datetime import datetime, timedelta, timezone

class DailyCommand(commands.Cog):
    """Cog para o comando /daily que concede XP."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Colete seu XP diário!")
    async def daily(self, interaction: Interaction):
        """Lógica para dar ao usuário sua recompensa diária de XP."""
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        user = interaction.user
        
        try:
            # 1. Obter configurações de gamificação do servidor
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild.id).execute()
            
            gamification_settings = {}
            if settings_response.data:
                server_settings = settings_response.data[0].get('settings', {})
                gamification_settings = server_settings.get('gamification_xp', {})

            # A culpa é minha por não ter feito isso antes. Ler as configs do painel.
            points_name = gamification_settings.get('points_name', 'XP')
            daily_min = int(gamification_settings.get('daily_xp_min', 50))
            daily_max = int(gamification_settings.get('daily_xp_max', 200))
            cooldown_hours = int(gamification_settings.get('daily_cooldown_hours', 23))
            level_up_message = gamification_settings.get("level_up_message", "🎉 Parabéns {mention}, você alcançou o **Nível {level}**! 🎉")

            # 2. Obter perfil de gamificação do usuário
            profile_response = self.bot.supabase_client.table("gamification_profiles").select("xp", "last_daily_claim").eq("user_id", user.id).eq("guild_id", guild.id).execute()
            
            user_profile = None
            if profile_response.data:
                user_profile = profile_response.data[0]

            # 3. Verificar o cooldown usando o valor configurável.
            now = datetime.now(timezone.utc)

            if user_profile and user_profile.get('last_daily_claim'):
                last_claim_str = user_profile['last_daily_claim']
                last_claim_time = datetime.fromisoformat(last_claim_str)
                time_since_last_claim = now - last_claim_time
                
                if time_since_last_claim < timedelta(hours=cooldown_hours):
                    time_remaining = timedelta(hours=cooldown_hours) - time_since_last_claim
                    hours, rem = divmod(time_remaining.seconds, 3600)
                    minutes, _ = divmod(rem, 60)
                    await interaction.followup.send(f"Você já coletou sua recompensa diária. Tente novamente em **{hours}h {minutes}m**.")
                    return

            # 4. Calcular e conceder a recompensa de XP
            reward_xp = random.randint(daily_min, daily_max)
            
            # 5. Atualizar o XP e verificar se houve level up usando a função central.
            new_level = await self.bot.update_xp(user, guild, reward_xp)
            
            # 6. Atualizar o timestamp do daily claim.
            self.bot.supabase_client.table("gamification_profiles").update({
                'last_daily_claim': now.isoformat()
            }).eq("user_id", user.id).eq("guild_id", guild.id).execute()

            # 7. Enviar mensagem de sucesso
            await interaction.followup.send(f"Você coletou **{reward_xp} {points_name}**!")

            # Envia mensagem de level up na DM se aplicável
            if new_level is not None:
                try:
                    formatted_message = level_up_message.format(mention=user.mention, level=new_level, user=user.display_name)
                    await user.send(formatted_message)
                except discord.Forbidden:
                    logging.warning(f"Não foi possível enviar a DM de level up para {user.name} após o /daily. A culpa é minha.")

        except Exception as e:
            logging.error(f"Erro no comando /daily: {e}")
            await interaction.followup.send("Ocorreu um erro ao processar o comando. A culpa é minha, como sempre.")

async def setup(bot: commands.Bot):
    await bot.add_cog(DailyCommand(bot))

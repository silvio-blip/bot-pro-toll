
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction
import logging
from datetime import datetime, timezone
import asyncio

class InviteSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.invite_cache = {}
        self.bot.loop.create_task(self.load_invite_cache())

    async def load_invite_cache(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.bot.invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
            except:
                pass

    async def get_invite_settings(self, guild_id: int) -> dict:
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('invites', {})
        except Exception:
            pass
        return {}

    async def update_user_stats(self, guild_id: int, user_id: int, invites=0, valid=0, bonuses=0):
        try:
            existing = self.bot.supabase_client.table("invite_stats").select("*").eq("guild_id", guild_id).eq("user_id", user_id).execute()
            
            if existing.data:
                current = existing.data[0]
                self.bot.supabase_client.table("invite_stats").update({
                    "total_invites": current['total_invites'] + invites,
                    "valid_invites": current['valid_invites'] + valid,
                    "bonuses_earned": current['bonuses_earned'] + bonuses,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("guild_id", guild_id).eq("user_id", user_id).execute()
            else:
                self.bot.supabase_client.table("invite_stats").insert({
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "total_invites": invites,
                    "valid_invites": valid,
                    "bonuses_earned": bonuses
                }).execute()
        except Exception as e:
            logging.error(f"Erro ao atualizar stats de convite: {e}")

    async def add_coins(self, guild_id: int, user_id: int, amount: int):
        try:
            profile_response = self.bot.supabase_client.table("gamification_profiles").select("xp").eq("guild_id", guild_id).eq("user_id", user_id).execute()
            
            if profile_response.data:
                current_xp = profile_response.data[0].get('xp', 0)
                new_xp = current_xp + amount
                self.bot.supabase_client.table("gamification_profiles").update({
                    "xp": new_xp
                }).eq("guild_id", guild_id).eq("user_id", user_id).execute()
            else:
                self.bot.supabase_client.table("gamification_profiles").insert({
                    "guild_id": guild_id,
                    "user_id": user_id,
                    "xp": amount,
                    "level": 1,
                    "message_count": 0
                }).execute()
        except Exception as e:
            logging.error(f"Erro ao adicionar moedas: {e}")

    async def check_reward_role(self, guild: discord.Guild, user: discord.Member, valid_invites: int):
        try:
            settings = await self.get_invite_settings(guild.id)
            reward_role_id = settings.get('reward_role_id')
            reward_threshold = settings.get('reward_threshold', 5)
            
            if reward_role_id and valid_invites >= reward_threshold:
                role = guild.get_role(reward_role_id)
                if role and role not in user.roles:
                    await user.add_roles(role)
        except Exception as e:
            logging.error(f"Erro ao verificar cargo de recompensa: {e}")

    async def send_notification(self, guild: discord.Guild, member: discord.Member, inviter_id: int, invitee_bonus: int, inviter_bonus: int):
        try:
            settings = await self.get_invite_settings(guild.id)
            notification_channel_id = settings.get('notification_channel_id')
            
            if notification_channel_id:
                channel = guild.get_channel(notification_channel_id)
                if channel:
                    inviter_member = guild.get_member(inviter_id)
                    inviter_name = inviter_member.name if inviter_member else f"ID: {inviter_id}"
                    
                    embed = discord.Embed(
                        title="📨 Convite Validado!",
                        description=f"**{member.name}** permaneceu no servidor!",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Convidado por", value=f"@{inviter_name}", inline=True)
                    embed.add_field(name="Bônus concedidos", value=f"+{invitee_bonus} para {member.name}\n+{inviter_bonus} para {inviter_name}", inline=False)
                    await channel.send(embed=embed)
        except Exception as e:
            logging.error(f"Erro ao enviar notificação: {e}")

    async def validate_invite_after_wait(self, guild: discord.Guild, member: discord.Member, inviter_id: int, invitee_bonus: int, inviter_bonus: int, min_stay_hours: int, notification_channel_id):
        try:
            await asyncio.sleep(min_stay_hours * 3600)
            
            member_check = guild.get_member(member.id)
            if member_check is None:
                logging.info(f"Usuário {member.name} saiu antes de {min_stay_hours} horas. Convite não validado.")
                return
            
            await self.process_valid_invite(guild, member, inviter_id, invitee_bonus, inviter_bonus, notification_channel_id)
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Erro ao validar convite após espera: {e}")

    async def process_valid_invite(self, guild: discord.Guild, member: discord.Member, inviter_id: int, invitee_bonus: int, inviter_bonus: int, notification_channel_id):
        try:
            await self.update_user_stats(guild.id, inviter_id, invites=1, valid=1, bonuses=inviter_bonus)
            
            await self.add_coins(guild.id, member.id, invitee_bonus)
            await self.add_coins(guild.id, inviter_id, inviter_bonus)
            
            inviter_member = guild.get_member(inviter_id)
            if inviter_member:
                stats_response = self.bot.supabase_client.table("invite_stats").select("valid_invites").eq("guild_id", guild.id).eq("user_id", inviter_id).execute()
                if stats_response.data:
                    await self.check_reward_role(guild, inviter_member, stats_response.data[0]['valid_invites'])
            
            self.bot.supabase_client.table("invites").update({
                "validated": True,
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "bonus_awarded": True
            }).eq("guild_id", guild.id).eq("invitee_id", member.id).execute()
            
            await self.send_notification(guild, member, inviter_id, invitee_bonus, inviter_bonus)
            
        except Exception as e:
            logging.error(f"Erro ao processar convite válido: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        
        guild = member.guild
        settings = await self.get_invite_settings(guild.id)
        
        if not settings.get('enabled'):
            return
        
        try:
            current_invites = await guild.invites()
            current_codes = {invite.code: invite.uses for invite in current_invites}
            
            old_codes = self.bot.invite_cache.get(guild.id, {})
            
            inviter_id = None
            invite_code = None
            
            for code, uses in current_codes.items():
                old_uses = old_codes.get(code, 0)
                if uses > old_uses:
                    for invite in current_invites:
                        if invite.code == code:
                            inviter_id = invite.inviter.id if invite.inviter else None
                            invite_code = code
                            break
                    break
            
            if inviter_id:
                invitee_bonus = settings.get('invitee_bonus', 50)
                inviter_bonus = settings.get('inviter_bonus', 25)
                min_stay_hours = settings.get('min_stay_hours', 24)
                notification_channel_id = settings.get('notification_channel_id')
                
                self.bot.supabase_client.table("invites").insert({
                    "guild_id": guild.id,
                    "inviter_id": inviter_id,
                    "invitee_id": member.id,
                    "invite_code": invite_code,
                    "invited_at": datetime.now(timezone.utc).isoformat()
                }).execute()
                
                if notification_channel_id:
                    channel = guild.get_channel(notification_channel_id)
                    if channel:
                        inviter_member = guild.get_member(inviter_id)
                        inviter_name = inviter_member.name if inviter_member else f"ID: {inviter_id}"
                        embed = discord.Embed(
                            title="📨 Novo Membro via Convite",
                            description=f"**{member.name}** entrou no servidor!",
                            color=discord.Color.blue()
                        )
                        embed.add_field(name="Convidado por", value=f"@{inviter_name}", inline=True)
                        if min_stay_hours > 0:
                            embed.add_field(name="⏳ Bônus em", value=f"{min_stay_hours} horas (se permanecer)", inline=False)
                        await channel.send(embed=embed)
                
                if min_stay_hours > 0:
                    self.bot.loop.create_task(self.validate_invite_after_wait(guild, member, inviter_id, invitee_bonus, inviter_bonus, min_stay_hours, notification_channel_id))
                else:
                    await self.process_valid_invite(guild, member, inviter_id, invitee_bonus, inviter_bonus, notification_channel_id)
            
            self.bot.invite_cache[guild.id] = current_codes
            
        except Exception as e:
            logging.error(f"Erro no on_member_join (convites): {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        
        guild = member.guild
        settings = await self.get_invite_settings(guild.id)
        
        if not settings.get('enabled'):
            return
        
        notification_channel_id = settings.get('notification_channel_id')
        if notification_channel_id:
            channel = guild.get_channel(notification_channel_id)
            if channel:
                embed = discord.Embed(
                    title="👋 Membro Saiu",
                    description=f"**{member.name}** saiu do servidor.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(InviteSystem(bot))

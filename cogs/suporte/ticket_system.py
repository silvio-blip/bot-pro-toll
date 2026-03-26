
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, ButtonStyle, TextStyle, SelectOption
import logging
import uuid
from datetime import datetime

SUPPORT_GUILD_ID = 1426737123956097175
SUPPORT_CHANNEL_ID = 1486677044602470400

class TicketDescriptionModal(ui.Modal, title="Descreva seu Problema"):
    def __init__(self, cog, category: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.category = category
        self.add_item(ui.TextInput(
            label="Descrição do Problema",
            style=TextStyle.long,
            placeholder="Descreva o problema em detalhes...",
            required=True,
            max_length=2000
        ))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        user = interaction.user
        description = self.children[0].value
        
        if not guild:
            await interaction.followup.send("❌ Este comando só pode ser usado em um servidor.", ephemeral=True)
            return
        
        try:
            settings_response = self.cog.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild.id).execute()
            
            if not settings_response.data:
                await interaction.followup.send(
                    "❌ O sistema de tickets ainda não foi configurado. Peça a um admin para configurar no painel.",
                    ephemeral=True
                )
                return
            
            existing_tickets = self.cog.bot.supabase_client.table("tickets").select("*").eq("guild_id", guild.id).eq("user_id", user.id).eq("status", "open").execute()
            
            if existing_tickets.data:
                for ticket in existing_tickets.data:
                    if ticket['category'] == self.category:
                        canal_existe = guild.get_channel(ticket['channel_id'])
                        if canal_existe:
                            await interaction.followup.send(
                                f"❌ Você já tem um ticket aberto para **{self.category}**. Feche-o antes de criar outro.",
                                ephemeral=True
                            )
                            return
                        else:
                            self.cog.bot.supabase_client.table("tickets").update({
                                "status": "closed"
                            }).eq("id", ticket['id']).execute()
            
            settings = settings_response.data[0].get('settings', {})
            tickets_settings = settings.get('tickets', {})
            
            category_id = tickets_settings.get('category_id')
            notify_role_id = tickets_settings.get('notify_role_id')
            support_role_id = tickets_settings.get('support_role_id')
            
            category = guild.get_channel(int(category_id)) if category_id else None
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            if notify_role_id:
                role = guild.get_role(int(notify_role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            if support_role_id:
                support_role = guild.get_role(int(support_role_id))
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            category_emoji = "🤖" if self.category == "bot" else "🖥️"
            channel_name = f"{category_emoji}ticket-{user.name}"
            
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {user.name} - {self.category}"
            )
            
            ticket_id = str(uuid.uuid4())
            
            self.cog.bot.supabase_client.table("tickets").insert({
                "id": ticket_id,
                "guild_id": guild.id,
                "user_id": user.id,
                "user_name": user.name,
                "channel_id": ticket_channel.id,
                "category": self.category,
                "description": description,
                "status": "open",
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            
            embed = discord.Embed(
                title=f"🎫 Ticket Aberto - {category_emoji} {self.category.title()}",
                description=f"**Usuário:** {user.mention}\n"
                           f"**Data:** {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}\n\n"
                           f"📝 **Descrição enviada por DM.**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Ticket ID: {ticket_id[:8]}")
            
            await ticket_channel.send(embed=embed, content=user.mention)
            
            await interaction.followup.send(
                f"✅ Seu ticket foi criado! Acesse o canal {ticket_channel.mention} para continuar.\n\n"
                f"📝 **Sua descrição:**\n{description}",
                ephemeral=True
            )
            
        except Exception as e:
            logging.error(f"Erro ao criar ticket: {e}")
            await interaction.followup.send(
                "❌ Ocorreu um erro ao criar seu ticket. Verifique se o sistema está configurado.",
                ephemeral=True
            )


class ReportBugModal(ui.Modal, title="Reportar Bug à Equipe de Suporte"):
    def __init__(self, cog, ticket_data: dict, guild: discord.Guild):
        super().__init__(timeout=300)
        self.cog = cog
        self.ticket_data = ticket_data
        self.guild = guild
        self.add_item(ui.TextInput(
            label="Descrição do Bug",
            style=TextStyle.long,
            placeholder="Descreva o problema detalhadamente...",
            required=True,
            max_length=2000
        ))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        bug_description = self.children[0].value
        user = interaction.guild.get_member(self.ticket_data['user_id'])
        channel = interaction.channel
        
        try:
            support_guild = self.cog.bot.get_guild(SUPPORT_GUILD_ID)
            if not support_guild:
                support_guild = await self.cog.bot.fetch_guild(SUPPORT_GUILD_ID)
            
            support_channel = support_guild.get_channel(SUPPORT_CHANNEL_ID)
            if not support_channel:
                support_channel = await support_guild.fetch_channel(SUPPORT_CHANNEL_ID)
            
            embed = discord.Embed(
                title="🐛 NOVO RELATÓRIO DE BUG",
                description="",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📝 Problema",
                value=bug_description,
                inline=False
            )
            embed.add_field(
                name="👤 Usuário",
                value=f"@{user.name if user else 'Unknown'} (ID: {self.ticket_data['user_id']})",
                inline=False
            )
            embed.add_field(
                name="🖥️ Servidor",
                value=f"{self.guild.name} (ID: {self.guild.id})",
                inline=False
            )
            embed.add_field(
                name="📅 Data",
                value=discord.utils.utcnow().strftime('%d/%m/%Y %H:%M'),
                inline=False
            )
            
            await support_channel.send(embed=embed)
            
            self.cog.bot.supabase_client.table("tickets").update({
                "status": "closed"
            }).eq("id", self.ticket_data['id']).execute()
            
            await channel.delete()
            
            await interaction.followup.send(
                "✅ Bug reportado com sucesso! O ticket foi fechado.",
                ephemeral=True
            )
            
        except Exception as e:
            logging.error(f"Erro ao reportar bug: {e}")
            await interaction.followup.send(
                "❌ Ocorreu um erro ao enviar o relatório.",
                ephemeral=True
            )


class ReportBugView(ui.View):
    def __init__(self, cog, ticket_data: dict, guild: discord.Guild):
        super().__init__(timeout=120)
        self.cog = cog
        self.ticket_data = ticket_data
        self.guild = guild

    @ui.button(label="Sim, reportar", style=ButtonStyle.success, emoji="📨")
    async def yes_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(ReportBugModal(self.cog, self.ticket_data, self.guild))
        self.stop()

    @ui.button(label="Não, apenas fechar", style=ButtonStyle.danger, emoji="❌")
    async def no_button(self, interaction: Interaction, button: ui.Button):
        channel = interaction.channel
        try:
            self.cog.bot.supabase_client.table("tickets").update({
                "status": "closed"
            }).eq("id", self.ticket_data['id']).execute()
            await channel.delete()
            await interaction.response.send_message("✅ Ticket fechado com sucesso!", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao fechar ticket: {e}")
            await interaction.response.send_message("❌ Erro ao fechar o ticket.", ephemeral=True)
        self.stop()


class OpenTicketView(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(label="🤖 Problemas no Bot", style=ButtonStyle.primary, custom_id="ticket_open_bot")
    async def bot_ticket(self, interaction: Interaction, button: ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        existing_tickets = self.cog.bot.supabase_client.table("tickets").select("*").eq("guild_id", guild.id).eq("user_id", user.id).eq("status", "open").execute()
        
        if existing_tickets.data:
            for ticket in existing_tickets.data:
                if ticket['category'] == 'bot':
                    canal_existe = guild.get_channel(ticket['channel_id'])
                    if canal_existe:
                        await interaction.response.send_message(
                            "❌ Você já tem um ticket aberto para **Problemas no Bot**. Feche-o antes de criar outro.",
                            ephemeral=True
                        )
                        return
                    else:
                        self.cog.bot.supabase_client.table("tickets").update({
                            "status": "closed"
                        }).eq("id", ticket['id']).execute()
        
        await interaction.response.send_modal(TicketDescriptionModal(self.cog, "bot"))

    @ui.button(label="🖥️ Problemas no Servidor", style=ButtonStyle.secondary, custom_id="ticket_open_server")
    async def server_ticket(self, interaction: Interaction, button: ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        existing_tickets = self.cog.bot.supabase_client.table("tickets").select("*").eq("guild_id", guild.id).eq("user_id", user.id).eq("status", "open").execute()
        
        if existing_tickets.data:
            for ticket in existing_tickets.data:
                if ticket['category'] == 'servidor':
                    canal_existe = guild.get_channel(ticket['channel_id'])
                    if canal_existe:
                        await interaction.response.send_message(
                            "❌ Você já tem um ticket aberto para **Problemas no Servidor**. Feche-o antes de criar outro.",
                            ephemeral=True
                        )
                        return
                    else:
                        self.cog.bot.supabase_client.table("tickets").update({
                            "status": "closed"
                        }).eq("id", ticket['id']).execute()
        
        await interaction.response.send_modal(TicketDescriptionModal(self.cog, "servidor"))


class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(OpenTicketView(self))

    async def get_ticket_settings(self, guild_id: int) -> dict:
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('tickets', {})
        except Exception:
            pass
        return {}

    @app_commands.command(name="setup-tickets", description="Cria o painel de tickets no canal atual.")
    async def setup_tickets(self, interaction: Interaction):
        try:
            settings = await self.get_ticket_settings(interaction.guild.id)
            if not settings.get('enabled'):
                await interaction.response.send_message(
                    "❌ O sistema de tickets está desativado. Ative no painel de controle primeiro.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="🎫 ABRA SEU TICKET",
                description="Encontrou algum problema? Estamos aqui para ajudar!",
                color=discord.Color.blurple()
            )
            
            await interaction.response.send_message(embed=embed, view=OpenTicketView(self), ephemeral=True)

        except Exception as e:
            logging.error(f"Erro em /setup-tickets: {e}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao configurar o painel.",
                ephemeral=True
            )

    @app_commands.command(name="fechar-ticket", description="Fecha o ticket atual.")
    async def fechar_ticket(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user
        
        try:
            settings = await self.get_ticket_settings(guild.id)
            support_role_id = settings.get('support_role_id')
            
            support_role = guild.get_role(support_role_id) if support_role_id else None
            has_support_role = support_role and support_role in user.roles
            is_admin = user.guild_permissions.administrator
            
            ticket_response = self.bot.supabase_client.table("tickets").select("*").eq("channel_id", channel.id).eq("status", "open").execute()
            
            if not ticket_response.data:
                await interaction.followup.send("❌ Este canal não é um ticket aberto.", ephemeral=True)
                return
            
            ticket_data = ticket_response.data[0]
            is_ticket_owner = ticket_data['user_id'] == user.id
            
            if not (has_support_role or is_admin or is_ticket_owner):
                await interaction.followup.send(
                    "❌ Você não tem permissão para fechar este ticket. Apenas o dono do ticket, admins ou o cargo de suporte podem fechar.",
                    ephemeral=True
                )
                return
            
            if ticket_data['category'] == 'bot':
                embed = discord.Embed(
                    title="🐛 Reportar Bug?",
                    description="Deseja reportar este problema para a equipe de suporte do bot?\n\n"
                               "Isso nos ajudará a melhorar o bot para todos os servidores!",
                    color=discord.Color.orange()
                )
                
                view = ReportBugView(self, ticket_data, guild)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                return
            
            await self.close_ticket(ticket_data, channel)
            await interaction.followup.send("✅ Ticket fechado com sucesso!", ephemeral=True)
            
        except Exception as e:
            logging.error(f"Erro ao fechar ticket: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao fechar o ticket.", ephemeral=True)

    async def close_ticket(self, ticket_data: dict, channel: discord.abc.GuildChannel):
        try:
            self.bot.supabase_client.table("tickets").update({
                "status": "closed"
            }).eq("id", ticket_data['id']).execute()
            
            await channel.delete()
            
        except Exception as e:
            logging.error(f"Erro ao deletar canal do ticket: {e}")

    @fechar_ticket.error
    async def on_fechar_ticket_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        await interaction.response.send_message(
            "❌ Ocorreu um erro ao processar o comando.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketSystem(bot))

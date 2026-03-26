import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, SelectOption, Embed, ButtonStyle
import logging
from datetime import datetime, timedelta, timezone
import json

# --- Função de Correção de URL Definitiva --- #
def get_image_url_from_data(item_data):
    data_to_process = None
    if isinstance(item_data, str):
        try: data_to_process = json.loads(item_data)
        except json.JSONDecodeError:
            if item_data.startswith('http'): return item_data
            data_to_process = item_data
    else: data_to_process = item_data
    if isinstance(data_to_process, dict):
        url = data_to_process.get('image_url') or data_to_process.get('url')
        if url: return url
        for key, value in data_to_process.items():
            if isinstance(value, str) and (value.startswith('http') or value.startswith('//')):
                if value.startswith('//'): return 'https://' + value.lstrip('//') 
                return value
    if isinstance(data_to_process, str) and data_to_process.startswith('http'): return data_to_process
    return None

# --- Funções do Banco de Dados ---
async def get_user_xp(bot, guild_id: int, user_id: int):
    try:
        response = bot.supabase_client.table("gamification_profiles").select("xp").eq("guild_id", guild_id).eq("user_id", user_id).single().execute()
        return response.data.get('xp', 0) if response.data else 0
    except Exception: return 0

async def update_user_xp(bot, guild_id: int, user_id: int, new_xp: int):
    try: bot.supabase_client.table("gamification_profiles").upsert({"guild_id": guild_id, "user_id": user_id, "xp": new_xp}).execute()
    except Exception as e: logging.error(f"Erro ao atualizar XP para user {user_id}: {e}")

async def check_if_user_owns_item(bot, guild_id: int, user_id: int, item_id: int):
    try:
        response = bot.supabase_client.table("user_inventories").select("id").eq("guild_id", guild_id).eq("user_id", user_id).eq("item_id", item_id).execute()
        return len(response.data) > 0
    except Exception:
        return False # Em caso de erro, assume que não possui para não bloquear a compra indevidamente

async def update_user_profile_background(bot, guild_id: int, user_id: int, image_url: str):
    try: bot.supabase_client.table("gamification_profiles").upsert({"guild_id": guild_id, "user_id": user_id, "profile_background_url": image_url}).execute()
    except Exception as e: logging.error(f"Erro ao atualizar o fundo de perfil para o user {user_id}: {e}")

async def update_user_profile_avatar(bot, guild_id: int, user_id: int, image_url: str):
    try: bot.supabase_client.table("gamification_profiles").upsert({"guild_id": guild_id, "user_id": user_id, "profile_avatar_url": image_url}).execute()
    except Exception as e: logging.error(f"Erro ao atualizar o avatar de perfil para o user {user_id}: {e}")

# --- Lógica da Compra ---
async def process_purchase(interaction: Interaction, item: dict):
    user = interaction.user
    guild = interaction.guild
    bot = interaction.client
    item_type = item.get('item_type')
    item_data = item.get('item_data')
    try:
        if item_type in ['cargo_automatico', 'cargo_colorido']:
            role_id = item_data.get('role_id')
            role = guild.get_role(int(role_id))
            if not role: raise ValueError(f"Cargo com ID {role_id} não encontrado.")
            if role in user.roles:
                await interaction.followup.send("Você já possui este cargo!", ephemeral=True)
                return False
            await user.add_roles(role, reason=f"Compra na loja: {item['name']}")
            await interaction.followup.send(f"🎉 Você comprou e recebeu o cargo **{role.name}**!", ephemeral=True)
        elif item_type == 'fundo_perfil':
            image_url = get_image_url_from_data(item_data)
            if not image_url: raise ValueError("URL da imagem de fundo não encontrada.")
            await update_user_profile_background(bot, guild.id, user.id, image_url)
            await interaction.followup.send(f"🖼️ Você comprou e equipou o fundo de perfil **{item['name']}**! Use /perfil para vê-lo.", ephemeral=True)
        elif item_type == 'avatar_perfil':
            image_url = get_image_url_from_data(item_data)
            if not image_url: raise ValueError("URL da imagem de avatar não encontrada.")
            await update_user_profile_avatar(bot, guild.id, user.id, image_url)
            await interaction.followup.send(f"👤 Você comprou e equipou o avatar de perfil **{item['name']}**! Use /perfil para vê-lo.", ephemeral=True)
        else:
            await interaction.followup.send(f"Você comprou o item **{item['name']}**! Ele já está no seu inventário.", ephemeral=True)
        return True
    except Exception as e:
        logging.error(f"Erro ao processar compra para {user.name}: {e}")
        await interaction.followup.send("❌ Ocorreu um erro. O administrador foi notificado.", ephemeral=True)
        return False

# --- Views e Selects da Loja ---
class ConfirmPurchaseView(ui.View):
    def __init__(self, bot: commands.Bot, item: dict, points_name: str = "XP"):
        super().__init__(timeout=60)
        self.bot = bot
        self.item = item
        self.points_name = points_name

    @ui.button(label="Confirmar Compra", style=ButtonStyle.success)
    async def confirm_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        already_owns = await check_if_user_owns_item(self.bot, interaction.guild.id, interaction.user.id, self.item['id'])
        if already_owns:
            await interaction.followup.send("Você já possui este item no seu inventário!", ephemeral=True)
            self.stop()
            return

        user_xp = await get_user_xp(self.bot, interaction.guild.id, interaction.user.id)
        if user_xp < self.item['price']:
            await interaction.followup.send(f"Você não tem mais {self.points_name} suficiente.", ephemeral=True)
            self.stop()
            return

        purchase_successful = await process_purchase(interaction, self.item)
        if purchase_successful:
            new_xp = user_xp - self.item['price']
            await update_user_xp(self.bot, interaction.guild.id, interaction.user.id, new_xp)
            try:
                inventory_record = {
                    "guild_id": interaction.guild.id, "user_id": interaction.user.id,
                    "item_id": self.item['id'], "item_name": self.item['name'],
                    "item_type": self.item['item_type'], "item_data": self.item.get('item_data', {})
                }
                self.bot.supabase_client.table("user_inventories").insert(inventory_record).execute()
            except Exception as e:
                logging.error(f"Falha ao registrar item no inventário: {e}")

        for child in self.children: child.disabled = True
        await interaction.edit_original_response(view=self)

    @ui.button(label="Cancelar", style=ButtonStyle.danger)
    async def cancel_button(self, interaction: Interaction, button: ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Compra cancelada.", view=None, embed=None)

class ShopPurchaseSelect(ui.Select):
    def __init__(self, bot: commands.Bot, items: list, user_xp: int, points_name: str = "XP"):
        self.bot = bot
        self.items_map = {str(item['id']): item for item in items}
        self.points_name = points_name
        options = [SelectOption(label=f"{item['name']} - {item['price']} {points_name}", value=str(item['id']), description=item['description'][:100], emoji="✅" if user_xp >= item['price'] else "❌") for item in items]
        if not options: options.append(SelectOption(label="A loja está vazia.", value="disabled"))
        super().__init__(placeholder="Selecione um item para comprar...", options=options, disabled=not items)

    async def callback(self, interaction: Interaction):
        item_id = self.values[0]
        item = self.items_map.get(item_id)
        if not item: return await interaction.response.send_message("Item não encontrado.", ephemeral=True)

        user_xp = await get_user_xp(self.bot, interaction.guild.id, interaction.user.id)
        if user_xp < item['price']:
            return await interaction.response.send_message(f"Você precisa de {item['price']} {self.points_name}, mas só tem {user_xp} {self.points_name}.", ephemeral=True)

        embed = Embed(title="Confirmação de Compra", description=f"Você tem certeza que deseja comprar **{item['name']}** por **{item['price']}** {self.points_name}?", color=discord.Color.yellow())
        image_url = get_image_url_from_data(item.get('item_data'))
        if image_url:
            if item.get('item_type') == 'fundo_perfil': embed.set_image(url=image_url)
            elif item.get('item_type') == 'avatar_perfil': embed.set_thumbnail(url=image_url)

        view = ConfirmPurchaseView(self.bot, item, self.points_name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ShopView(ui.View):
    def __init__(self, bot, items, user_xp, points_name: str = "XP"):
        super().__init__(timeout=180)
        self.add_item(ShopPurchaseSelect(bot, items, user_xp, points_name))

class ShopUserCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="loja", description="Abre a loja do servidor para comprar itens com XP.")
    async def loja(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", interaction.guild.id).execute()
            settings = settings_response.data[0].get('settings', {}) if settings_response.data else {}
            points_name = settings.get('gamification_xp', {}).get('points_name', 'XP')
            
            items_response = self.bot.supabase_client.table("loja_items").select("*").eq("guild_id", interaction.guild.id).eq("is_active", True).order("price").execute()
            items = items_response.data
            user_xp = await get_user_xp(self.bot, interaction.guild.id, interaction.user.id)
            embed = Embed(title="🛒 Loja do Servidor", description=f"Use seus pontos ({points_name}) para comprar vantagens exclusivas!\nSelecione um item no menu abaixo.", color=discord.Color.blue())
            embed.add_field(name="Seu Saldo", value=f"**{user_xp}** {points_name}", inline=False)
            if not items: embed.description = "A loja ainda está vazia."
            view = ShopView(self.bot, items, user_xp, points_name)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao abrir a loja: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao carregar a loja.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShopUserCog(bot))

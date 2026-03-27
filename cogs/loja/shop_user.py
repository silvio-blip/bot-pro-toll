import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, SelectOption, Embed, ButtonStyle, File
from io import BytesIO
import logging
from datetime import datetime, timedelta, timezone
import json
from PIL import Image, ImageDraw, ImageFont
import requests

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

# --- Função para gerar imagem placeholder --- #
def get_color_for_item_type(item_type: str) -> tuple:
    colors = {
        'cargo_automatico': (155, 89, 182),
        'cargo_colorido': (155, 89, 182),
        'fundo_perfil': (52, 152, 219),
        'avatar_perfil': (46, 204, 113),
    }
    return colors.get(item_type, (149, 165, 166))

async def generate_placeholder_image(item_name: str, item_type: str) -> BytesIO:
    from PIL import ImageFont
    
    color = get_color_for_item_type(item_type)
    width, height = 800, 600
    
    img = Image.new('RGB', (width, height), color=color)
    draw = ImageDraw.Draw(img)
    
    for i in range(0, width, 40):
        draw.line([(i, 0), (i + height, height)], fill=(255, 255, 255, 25))
    
    for i in range(0, height, 40):
        draw.line([(0, i), (width, i + width)], fill=(255, 255, 255, 25))
    
    font_size = 90
    small_font_size = 45
    
    font_path = "/tmp/roboto_bold.ttf"
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    try:
        small_font = ImageFont.truetype(font_path, small_font_size)
    except:
        small_font = font
    
    max_text_width = width - 80
    item_name_display = item_name
    
    try:
        if hasattr(draw, 'textlength'):
            text_width = int(draw.textlength(item_name_display, font=font))
        else:
            bbox = draw.textbbox((0, 0), item_name_display, font=font)
            text_width = bbox[2] - bbox[0]
    except:
        text_width = len(item_name_display) * 40
    
    if text_width > max_text_width:
        while text_width > max_text_width and len(item_name_display) > 8:
            item_name_display = item_name_display[:-4] + "..."
            try:
                if hasattr(draw, 'textlength'):
                    text_width = int(draw.textlength(item_name_display, font=font))
                else:
                    bbox = draw.textbbox((0, 0), item_name_display, font=font)
                    text_width = bbox[2] - bbox[0]
            except:
                text_width = len(item_name_display) * 40
    
    try:
        if hasattr(draw, 'textlength'):
            text_height = 90
        else:
            bbox = draw.textbbox((0, 0), item_name_display, font=font)
            text_height = bbox[3] - bbox[1]
    except:
        text_height = font_size
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2 - 40
    
    draw.text((x, y), item_name_display, fill=(255, 255, 255), font=font)
    
    type_labels = {
        'cargo_colorido': 'CARGO',
        'fundo_perfil': 'FUNDO DE PERFIL',
        'avatar_perfil': 'AVATAR DE PERFIL',
    }
    type_label = type_labels.get(item_type, 'ITEM')
    
    try:
        if hasattr(draw, 'textlength'):
            type_width = int(draw.textlength(type_label, font=small_font))
        else:
            bbox_type = draw.textbbox((0, 0), type_label, font=small_font)
            type_width = bbox_type[2] - bbox_type[0]
    except:
        type_width = len(type_label) * 20
    
    draw.text(((width - type_width) // 2, height - 100), type_label, fill=(255, 255, 255), font=small_font)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

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
    
    if isinstance(item_data, str):
        try:
            item_data = json.loads(item_data)
        except:
            item_data = {}
    
    try:
        if item_type in ['cargo_automatico', 'cargo_colorido']:
            role_id = None
            if isinstance(item_data, dict):
                role_id = item_data.get('role_id') or item_data.get('role') or item_data.get('cargo_id') or item_data.get('url') or item_data.get('id')
            if not role_id:
                logging.error(f"Dados do item: {item_data}")
                raise ValueError("ID do cargo não encontrado nos dados do item.")
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

class ShopNavigatorView(ui.View):
    CATEGORIES = {
        'all': ('🎁 Todos', None),
        'cargo_colorido': ('🎽 Cargos', 'cargo_colorido'),
        'fundo_perfil': ('🖼️ Fundos', 'fundo_perfil'),
        'avatar_perfil': ('👤 Avatares', 'avatar_perfil'),
    }
    
    def __init__(self, bot, items, user_xp, points_name: str = "XP"):
        super().__init__(timeout=180)
        self.bot = bot
        self.all_items = items
        self.user_xp = user_xp
        self.points_name = points_name
        self.current_category = 'all'
        self.items = items
        self.current_index = 0
        
        self._setup_category_buttons()
        self._setup_navigation_buttons()
    
    def _filter_by_category(self):
        if self.current_category == 'all':
            self.items = self.all_items
        else:
            self.items = [item for item in self.all_items if item.get('item_type') == self.current_category]
        self.current_index = 0
    
    def _setup_category_buttons(self):
        self._filter_by_category()
        
        for i, (cat_key, (cat_label, cat_type)) in enumerate(self.CATEGORIES.items()):
            if cat_key == 'all':
                has_items = len(self.all_items) > 0
            else:
                has_items = any(item.get('item_type') == cat_type for item in self.all_items)
            
            btn = ui.Button(
                label=cat_label,
                style=ButtonStyle.primary if self.current_category == cat_key else ButtonStyle.secondary,
                custom_id=f"catbtn_{cat_key}",
                disabled=not has_items,
                row=0
            )
            btn.callback = self._make_category_callback(cat_key)
            self.add_item(btn)
    
    def _setup_navigation_buttons(self):
        item_name = "Nenhum item"
        item_price = 0
        if self.items:
            item = self.items[self.current_index]
            item_name = item.get('name', 'Item')[:18]
            item_price = item.get('price', 0)
        
        label = f"{item_name} - {item_price}"
        
        prev_btn = ui.Button(label="◀", style=ButtonStyle.secondary, custom_id="nav_prev", row=1)
        prev_btn.callback = self.prev_item
        self.add_item(prev_btn)
        
        item_btn = ui.Button(label=label, style=ButtonStyle.primary, disabled=True, custom_id="nav_item", row=1)
        self.add_item(item_btn)
        
        next_btn = ui.Button(label="▶", style=ButtonStyle.secondary, custom_id="nav_next", row=1)
        next_btn.callback = self.next_item
        self.add_item(next_btn)
        
        buy_btn = ui.Button(label="💳 Comprar", style=ButtonStyle.success, custom_id="nav_buy", row=2)
        buy_btn.callback = self.buy_item
        self.add_item(buy_btn)
    
    def _make_category_callback(self, cat_key: str):
        async def callback(interaction: Interaction):
            await self.select_category(interaction, cat_key)
        return callback
    
    async def select_category(self, interaction: Interaction, category_key: str):
        self.current_category = category_key
        self._filter_by_category()
        
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id and item.custom_id.startswith('catbtn_'):
                cat_key = item.custom_id.replace('catbtn_', '')
                if cat_key == self.current_category:
                    item.style = ButtonStyle.primary
                else:
                    item.style = ButtonStyle.secondary
        
        if not self.items:
            embed = Embed(
                title="🛒 Loja do Servidor",
                description="Não há itens nesta categoria.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Seu Saldo", value=f"**{self.user_xp}** {self.points_name}", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        await self._update_item_display(interaction)
    
    async def _update_item_display(self, interaction):
        item = self.items[self.current_index]
        image_buffer = await self._get_item_image(item)
        
        item_price = item.get('price', 0)
        can_buy = self.user_xp >= item_price
        item_name = item.get('name', 'Item')
        item_desc = item.get('description', '')[:150]
        
        cat_name = self.CATEGORIES.get(self.current_category, ('Todos', None))[0]
        
        for child in self.children:
            if hasattr(child, 'custom_id') and child.custom_id == 'nav_item':
                child.label = f"{item_name[:18]} - {item_price}"
        
        embed = Embed(
            title=f"🛒 {item_name}",
            description=f"{item_desc}\n\n💰 **Preço:** {item_price} {self.points_name}\n💵 **Seu saldo:** {self.user_xp} {self.points_name}",
            color=discord.Color.green() if can_buy else discord.Color.red()
        )
        
        file = File(image_buffer, filename="item_preview.png")
        embed.set_image(url="attachment://item_preview.png")
        embed.set_footer(text=f"{cat_name} • Item {self.current_index + 1} de {len(self.items)}")
        
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
    
    async def _get_item_image(self, item):
        from PIL import Image
        item_type = item.get('item_type', '')
        item_name = item.get('name', 'Item')
        
        if item_type == 'cargo_colorido':
            cargo_bg_url = "https://i.pinimg.com/736x/c5/2d/e5/c52de584060b1d0fc1ffe0c3d73ffdd8.jpg"
            try:
                response = requests.get(cargo_bg_url, timeout=5)
                if response.status_code == 200:
                    bg_image = Image.open(BytesIO(response.content)).convert('RGB')
                    bg_image = bg_image.resize((800, 600))
                    
                    draw = ImageDraw.Draw(bg_image)
                    
                    font_path = "/tmp/roboto_bold.ttf"
                    try:
                        name_font = ImageFont.truetype(font_path, 70)
                    except:
                        name_font = ImageFont.load_default()
                    
                    try:
                        desc_font = ImageFont.truetype(font_path, 35)
                    except:
                        desc_font = name_font
                    
                    try:
                        if hasattr(draw, 'textlength'):
                            text_width = int(draw.textlength(item_name, font=name_font))
                        else:
                            bbox = draw.textbbox((0, 0), item_name, font=name_font)
                            text_width = bbox[2] - bbox[0]
                    except:
                        text_width = len(item_name) * 35
                    
                    x = (800 - text_width) // 2
                    y = 600 // 2 - 35
                    
                    shadow_color = (0, 0, 0)
                    for osf in range(3):
                        draw.text((x - osf, y), item_name, fill=shadow_color, font=name_font)
                        draw.text((x + osf, y), item_name, fill=shadow_color, font=name_font)
                        draw.text((x, y - osf), item_name, fill=shadow_color, font=name_font)
                        draw.text((x, y + osf), item_name, fill=shadow_color, font=name_font)
                    
                    draw.text((x, y), item_name, fill=(255, 255, 255), font=name_font)
                    
                    try:
                        if hasattr(draw, 'textlength'):
                            type_width = int(draw.textlength("CARGO", font=desc_font))
                        else:
                            bbox_type = draw.textbbox((0, 0), "CARGO", font=desc_font)
                            type_width = bbox_type[2] - bbox_type[0]
                    except:
                        type_width = len("CARGO") * 15
                    
                    draw.text(((800 - type_width) // 2, 600 - 80), "CARGO", fill=(255, 255, 255), font=desc_font)
                    
                    buffer = BytesIO()
                    bg_image.save(buffer, format='PNG')
                    buffer.seek(0)
                    return buffer
            except:
                pass
        
        image_url = get_image_url_from_data(item.get('item_data'))
        
        if image_url:
            try:
                response = requests.get(image_url, timeout=5)
                if response.status_code == 200:
                    return BytesIO(response.content)
            except:
                pass
        
        return await generate_placeholder_image(item.get('name', 'Item'), item.get('item_type', 'default'))
    
    async def prev_item(self, interaction: Interaction):
        self.current_index = (self.current_index - 1) % len(self.items)
        await self._update_item_display(interaction)
    
    async def next_item(self, interaction: Interaction):
        self.current_index = (self.current_index + 1) % len(self.items)
        await self._update_item_display(interaction)
    
    async def buy_item(self, interaction: Interaction):
        if not self.items:
            return
        
        item = self.items[self.current_index]
        
        already_owns = await check_if_user_owns_item(self.bot, interaction.guild.id, interaction.user.id, item['id'])
        if already_owns:
            await interaction.response.send_message("Você já possui este item no seu inventário!", ephemeral=True)
            return
        
        if self.user_xp < item['price']:
            await interaction.response.send_message(f"Você precisa de {item['price']} {self.points_name}, mas só tem {self.user_xp} {self.points_name}.", ephemeral=True)
            return
        
        embed = Embed(
            title="Confirmação de Compra",
            description=f"Você tem certeza que deseja comprar **{item['name']}** por **{item['price']}** {self.points_name}?",
            color=discord.Color.yellow()
        )
        
        image_url = get_image_url_from_data(item.get('item_data'))
        if image_url:
            if item.get('item_type') == 'fundo_perfil':
                embed.set_image(url=image_url)
            elif item.get('item_type') == 'avatar_perfil':
                embed.set_thumbnail(url=image_url)
        
        view = ConfirmPurchaseView(self.bot, item, self.points_name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
            
            if not items:
                embed = Embed(title="🛒 Loja do Servidor", description="A loja ainda está vazia.", color=discord.Color.blue())
                embed.add_field(name="Seu Saldo", value=f"**{user_xp}** {points_name}", inline=False)
                return await interaction.followup.send(embed=embed, ephemeral=True)
            
            view = ShopNavigatorView(self.bot, items, user_xp, points_name)
            
            first_item = items[0]
            image_buffer = await view._get_item_image(first_item)
            
            item_price = first_item.get('price', 0)
            can_buy = user_xp >= item_price
            item_name = first_item.get('name', 'Item')
            item_desc = first_item.get('description', '')[:100]
            
            embed = Embed(
                title=f"🛒 {item_name}",
                description=f"**{item_desc}**\n\n💰 **Preço:** {item_price} {points_name}\n💵 **Seu saldo:** {user_xp} {points_name}",
                color=discord.Color.green() if can_buy else discord.Color.red()
            )
            
            file = File(image_buffer, filename="item_preview.png")
            embed.set_image(url="attachment://item_preview.png")
            embed.set_footer(text=f"🎁 Todos • Item 1 de {len(items)}")
            
            await interaction.followup.send(embed=embed, file=file, view=view, ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao abrir a loja: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao carregar a loja.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShopUserCog(bot))

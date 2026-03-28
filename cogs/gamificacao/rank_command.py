import discord
from discord.ext import commands
from discord import app_commands, Interaction, File, ui, Embed, TextStyle
import logging
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime


def create_modern_background(width: int, height: int) -> Image.Image:
    """Cria um fundo moderno com gradiente e partículas"""
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)
    
    colors = [
        (15, 23, 42),    # Dark slate
        (30, 41, 59),   # Slate 800
        (51, 65, 85),   # Slate 700
    ]
    
    for y in range(height):
        ratio = y / height
        idx = ratio * (len(colors) - 1)
        i = int(idx)
        f = idx - i
        
        if i >= len(colors) - 1:
            r, g, b = colors[-1]
        else:
            r = int(colors[i][0] * (1 - f) + colors[i + 1][0] * f)
            g = int(colors[i][1] * (1 - f) + colors[i + 1][1] * f)
            b = int(colors[i][2] * (1 - f) + colors[i + 1][2] * f)
        
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    # Adicionar gradiente lateral sutil
    for x in range(width):
        alpha = int(30 * (x / width))
        draw.line([(x, 0), (x, height)], fill=(99, 102, 241, alpha))
    
    return img


def create_glow_gradient(width: int, height: int) -> Image.Image:
    """Cria um gradiente com efeito de brilho"""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Cores do gradiente ( Roxo -> Azul -> Ciano )
    gradient_colors = [
        (139, 92, 246, 80),   # Violet
        (99, 102, 241, 60),   # Indigo  
        (59, 130, 246, 40),  # Blue
        (34, 211, 238, 20),  # Cyan
    ]
    
    for y in range(height):
        ratio = y / height
        idx = ratio * (len(gradient_colors) - 1)
        i = int(idx)
        f = idx - i
        
        if i >= len(gradient_colors) - 1:
            r, g, b, a = gradient_colors[-1]
        else:
            r = int(gradient_colors[i][0] * (1 - f) + gradient_colors[i + 1][0] * f)
            g = int(gradient_colors[i][1] * (1 - f) + gradient_colors[i + 1][1] * f)
            b = int(gradient_colors[i][2] * (1 - f) + gradient_colors[i + 1][2] * f)
            a = int(gradient_colors[i][3] * (1 - f) + gradient_colors[i + 1][3] * f)
        
        draw.line([(0, y), (width, y)], fill=(r, g, b, a))
    
    return img


def create_rounded_rectangle(size: tuple, radius: int, fill: tuple) -> Image.Image:
    """Cria um retângulo com cantos arredondados"""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0) + size, radius=radius, fill=fill)
    return img


def create_rounded_mask(size: tuple, radius: int) -> Image.Image:
    """Cria uma máscara com cantos arredondados"""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0) + size, radius=radius, fill=255)
    return mask


def create_stats_card(width: int, height: int, radius: int = 15) -> Image.Image:
    """Cria um cartão para as estatísticas"""
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    
    # Fundo semi-transparente
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=(0, 0, 0, 80))
    
    # Borda sutil
    draw.rounded_rectangle((0, 0, width, height), radius=radius, outline=(139, 92, 246, 50), width=1)
    
    return card


async def create_rank_card(
    user_avatar_url: str,
    user_name: str,
    current_level: int,
    current_xp_in_level: int,
    xp_for_level_up: int,
    points_name: str,
    total_xp: int = 0,
    background_url: str = None,
    custom_avatar_url: str = None,
    message_count: int = 0,
    days_in_server: int = 0,
    rank_position: int = 0,
    total_members: int = 0,
    inventory_items: list = None,
    equipped_background: str = None,
    equipped_avatar: str = None,
    profile_bio: str = '',
    coin_image_url: str = None
) -> BytesIO:
    """Gera uma imagem de cartão de perfil moderno e bonito"""
    
    if inventory_items is None:
        inventory_items = []
    
    card_width, card_height = 1000, 700
    
    scale_factor = 2
    display_width = card_width
    display_height = card_height
    card_width = card_width * scale_factor
    card_height = card_height * scale_factor
    
    # Carregar fontes - apenas as que existem disponíveis
    try:
        name_font = ImageFont.truetype("assets/fonts/Poppins-Bold.ttf", 56 * scale_factor)
        level_font = ImageFont.truetype("assets/fonts/Poppins-Bold.ttf", 32 * scale_factor)
        stat_label_font = ImageFont.truetype("assets/fonts/Poppins-Regular.ttf", 22 * scale_factor)
        stat_value_font = ImageFont.truetype("assets/fonts/Poppins-Bold.ttf", 26 * scale_factor)
        small_font = ImageFont.truetype("assets/fonts/Poppins-Regular.ttf", 22 * scale_factor)
        tiny_font = ImageFont.truetype("assets/fonts/Poppins-Regular.ttf", 18 * scale_factor)
        xp_font = ImageFont.truetype("assets/fonts/Poppins-Bold.ttf", 26 * scale_factor)
    except IOError as e:
        logging.error(f"Erro ao carregar fontes: {e}")
        name_font = ImageFont.load_default()
        level_font = name_font
        stat_label_font = name_font
        stat_value_font = name_font
        small_font = name_font
        tiny_font = name_font
        xp_font = name_font
    
    # Fundo principal
    if background_url:
        try:
            response = requests.get(background_url, timeout=10)
            card = Image.open(BytesIO(response.content)).convert("RGBA")
            img_ratio, card_ratio = card.width / card.height, card_width / card_height
            new_width, new_height = (int(card_height * img_ratio), card_height) if img_ratio > card_ratio else (card_width, int(card_width / img_ratio))
            card = card.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left, top = (card.width - card_width) / 2, (card.height - card_height) / 2
            card = card.crop((left, top, left + card_width, top + card_height))
            
            # Overlay para escurecer fundo customizado
            overlay = Image.new("RGBA", card.size, (0, 0, 0, 140))
            card = Image.alpha_composite(card, overlay)
        except Exception as e:
            logging.error(f"Erro ao processar fundo customizado: {e}")
            card = create_modern_background(card_width, card_height)
            glow = create_glow_gradient(card_width, 200 * scale_factor)
            card.paste(glow, (0, 0), glow)
    else:
        card = create_modern_background(card_width, card_height)
        # Adicionar camada de brilho no topo
        glow = create_glow_gradient(card_width, 180 * scale_factor)
        card.paste(glow, (0, 0), glow)
    
    # Máscara com cantos arredondados
    mask = create_rounded_mask((card_width, card_height), 50 * scale_factor)
    card.putalpha(mask)
    
    # Borda externa com glow
    border_card = Image.new("RGBA", (card_width + 16 * scale_factor, card_height + 16 * scale_factor), (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border_card)
    draw_border.rounded_rectangle((0, 0, card_width + 16 * scale_factor, card_height + 16 * scale_factor), radius=58 * scale_factor, outline=(139, 92, 246, 100), width=2 * scale_factor)
    border_card.paste(card, (8 * scale_factor, 8 * scale_factor))
    card = border_card
    
    draw = ImageDraw.Draw(card)
    
    # ========== AVATAR ==========
    avatar_url_to_use = custom_avatar_url or user_avatar_url
    try:
        response = requests.get(avatar_url_to_use, timeout=10)
        avatar = Image.open(BytesIO(response.content)).convert("RGBA").resize((130 * scale_factor, 130 * scale_factor))
    except Exception as e:
        logging.error(f"Falha ao carregar avatar: {e}")
        response = requests.get(user_avatar_url, timeout=10)
        avatar = Image.open(BytesIO(response.content)).convert("RGBA").resize((130 * scale_factor, 130 * scale_factor))
    
    # Primeiro, criar avatar circular
    avatar_size_final = 130 * scale_factor
    avatar_circular = Image.new("RGBA", (avatar_size_final, avatar_size_final), (0, 0, 0, 0))
    avatar_mask = Image.new("L", (avatar_size_final, avatar_size_final), 0)
    draw_mask = ImageDraw.Draw(avatar_mask)
    draw_mask.ellipse((0, 0, avatar_size_final, avatar_size_final), fill=255)
    avatar_circular.paste(avatar, (0, 0), avatar)
    avatar_circular.putalpha(avatar_mask)
    
    # Agora criar a moldura (maior que o avatar)
    avatar_size = 150 * scale_factor
    avatar_frame = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
    
    # Gradiente na moldura
    frame_colors = [(139, 92, 246), (99, 102, 241), (59, 130, 246)]
    for i in range(9):
        alpha = int(200 - (i * 20))
        frame_draw = ImageDraw.Draw(avatar_frame)
        frame_draw.rounded_rectangle((i * scale_factor, i * scale_factor, avatar_size - i * scale_factor, avatar_size - i * scale_factor), radius=avatar_size//2, outline=(*frame_colors[i // 3], alpha), width=2 * scale_factor)
    
    # Colocar avatar circular no centro da moldura
    offset = (avatar_size - avatar_size_final) // 2
    avatar_frame.paste(avatar_circular, (offset, offset), avatar_circular)
    
    card.paste(avatar_frame, (40 * scale_factor, 40 * scale_factor), avatar_frame)
    
    # ========== NOME E NÍVEL (esquerda) ==========
    display_name = user_name[:14] + "..." if len(user_name) > 14 else user_name
    draw.text((200 * scale_factor, 50 * scale_factor), display_name, font=name_font, fill=(255, 255, 255))
    
    draw.text((210 * scale_factor, 105 * scale_factor), f"NÍVEL {current_level}", font=level_font, fill=(255, 215, 0))
    
    level_badge = ""
    level_color = (255, 255, 255)
    if current_level >= 100:
        level_badge = "👑 Lendário"
        level_color = (255, 215, 0)
    elif current_level >= 50:
        level_badge = "👑 Mestre"
        level_color = (255, 215, 0)
    elif current_level >= 25:
        level_badge = "🔥 Elite"
        level_color = (255, 100, 50)
    elif current_level >= 10:
        level_badge = "⭐ Avançado"
        level_color = (100, 200, 255)
    elif current_level >= 5:
        level_badge = "✨ Iniciante"
        level_color = (150, 255, 150)
    else:
        level_badge = "🌱 Novato"
        level_color = (180, 180, 180)
    
    draw.text((210 * scale_factor, 145 * scale_factor), level_badge, font=stat_value_font, fill=level_color)
    
    # ========== CARDS DE ESTATÍSTICAS (abaixo da barra de XP) ==========
    card_spacing = 12 * scale_factor
    stat_card_width = 140 * scale_factor
    
    # Card 1 - Ranking (esquerda)
    stats_x = 40 * scale_factor
    stats_y = 280 * scale_factor
    stats_container = create_stats_card(stat_card_width, 100 * scale_factor, 10 * scale_factor)
    card.paste(stats_container, (stats_x, stats_y), stats_container)
    draw.text((stats_x + 12 * scale_factor, stats_y + 10 * scale_factor), "RANK", font=stat_label_font, fill=(139, 92, 246))
    draw.text((stats_x + 12 * scale_factor, stats_y + 45 * scale_factor), f"#{rank_position}/{total_members}", font=stat_value_font, fill=(255, 255, 255))
    
    # Card 2 - Mensagens (meio)
    stats_x2 = stats_x + stat_card_width + card_spacing
    stats_container2 = create_stats_card(stat_card_width, 100 * scale_factor, 10 * scale_factor)
    card.paste(stats_container2, (stats_x2, stats_y), stats_container2)
    draw.text((stats_x2 + 12 * scale_factor, stats_y + 10 * scale_factor), "MSG", font=stat_label_font, fill=(59, 130, 246))
    draw.text((stats_x2 + 12 * scale_factor, stats_y + 45 * scale_factor), f"{message_count:,}", font=stat_value_font, fill=(255, 255, 255))
    
    # Card 3 - XP Total (direita - mais larga)
    stats_x3 = stats_x2 + stat_card_width + card_spacing
    stat_card_width_large = 280 * scale_factor
    stats_container3 = create_stats_card(stat_card_width_large, 100 * scale_factor, 10 * scale_factor)
    card.paste(stats_container3, (stats_x3, stats_y), stats_container3)
    
    if coin_image_url:
        try:
            response = requests.get(coin_image_url, timeout=10)
            coin_img = Image.open(BytesIO(response.content)).convert("RGBA")
            coin_size = int(28 * scale_factor)
            coin_img = coin_img.resize((coin_size, coin_size), Image.Resampling.LANCZOS)
            card.paste(coin_img, (int(stats_x3 + 12 * scale_factor), int(stats_y + 12 * scale_factor)), coin_img)
            draw.text((stats_x3 + 48 * scale_factor, stats_y + 10 * scale_factor), points_name.upper(), font=stat_label_font, fill=(99, 102, 241))
        except Exception as e:
            logging.error(f"Erro ao carregar imagem da moeda: {e}")
            draw.text((stats_x3 + 12 * scale_factor, stats_y + 10 * scale_factor), points_name.upper(), font=stat_label_font, fill=(99, 102, 241))
    else:
        draw.text((stats_x3 + 12 * scale_factor, stats_y + 10 * scale_factor), points_name.upper(), font=stat_label_font, fill=(99, 102, 241))
    
    draw.text((stats_x3 + 12 * scale_factor, stats_y + 45 * scale_factor), f"{total_xp:,}", font=stat_value_font, fill=(255, 215, 0))
    
    # ========== BIO (texto ao lado direito do nome) ==========
    if profile_bio:
        bio_x = 550 * scale_factor
        bio_y = 80 * scale_factor
        
        draw.text((bio_x, bio_y), "Sobre mim...", font=stat_label_font, fill=(59, 130, 246))
        
        max_chars_per_line = 40
        bio_lines = []
        for i in range(0, len(profile_bio), max_chars_per_line):
            bio_lines.append(profile_bio[i:i + max_chars_per_line])
        
        for i, line in enumerate(bio_lines):
            draw.text((bio_x + 5 * scale_factor, bio_y + 35 * scale_factor + (i * 25 * scale_factor)), line, font=stat_label_font, fill=(180, 180, 180))
    
    # ========== BARRA DE XP ==========
    bar_x = 40 * scale_factor
    bar_y = 210 * scale_factor
    bar_width = 920 * scale_factor
    bar_height = 45 * scale_factor
    
    bg_bar = create_rounded_rectangle((bar_width, bar_height), 22 * scale_factor, (30, 41, 59, 220))
    card.paste(bg_bar, (bar_x, bar_y), bg_bar)
    
    xp_progress = min(current_xp_in_level / xp_for_level_up, 1.0) if xp_for_level_up > 0 else 0
    
    if xp_progress > 0:
        progress_width = int(bar_width * xp_progress)
        
        progress_bar = Image.new("RGBA", (progress_width, bar_height))
        prog_draw = ImageDraw.Draw(progress_bar)
        
        for x in range(progress_width):
            ratio = x / progress_width
            r = int(34 + (59 - 34) * ratio)
            g = int(197 + (130 - 197) * ratio)
            b = int(94 + (246 - 94) * ratio)
            prog_draw.line([(x, 0), (x, bar_height)], fill=(r, g, b, 255))
        
        progress_mask = create_rounded_mask((progress_width, bar_height), 22 * scale_factor)
        progress_bar.putalpha(progress_mask)
        card.paste(progress_bar, (bar_x, bar_y), progress_bar)
        
        shine = Image.new("RGBA", (progress_width, bar_height // 2), (0, 0, 0, 0))
        shine_draw = ImageDraw.Draw(shine)
        for y in range(bar_height // 2):
            alpha = int(50 * (1 - y / (bar_height // 2)))
            shine_draw.line([(0, y), (progress_width, y)], fill=(255, 255, 255, alpha))
        card.paste(shine, (bar_x, bar_y), shine)
    
    xp_text = f"{current_xp_in_level:,} / {xp_for_level_up:,} {points_name}"
    text_width = draw.textlength(xp_text, font=xp_font)
    draw.text((bar_x + bar_width - text_width - 20 * scale_factor, bar_y + (bar_height - 26 * scale_factor) / 2), xp_text, font=xp_font, fill=(255, 255, 255))
    draw.text((bar_x + 15 * scale_factor, bar_y + (bar_height - 26 * scale_factor) / 2), "PROGRESSO", font=xp_font, fill=(150, 150, 150))
    
    # ========== ESTATÍSTICAS DETALHADAS ==========
    detail_y = 450 * scale_factor
    
    draw.text((40 * scale_factor, detail_y), "ESTATÍSTICAS", font=stat_label_font, fill=(255, 255, 255))
    draw.line((40 * scale_factor, detail_y + 35 * scale_factor, 960 * scale_factor, detail_y + 35 * scale_factor), fill=(139, 92, 246, 80), width=2 * scale_factor)
    
    detail_y += 55 * scale_factor
    
    stats_detail = [
        ("", "Tempo no servidor", f"{days_in_server} dias"),
    ]
    
    for i, (emoji, label, value) in enumerate(stats_detail):
        x_pos = 290 * scale_factor
        
        mini_card = create_stats_card(280 * scale_factor, 85 * scale_factor, 10 * scale_factor)
        card.paste(mini_card, (x_pos, detail_y), mini_card)
        
        draw.text((x_pos + 15 * scale_factor, detail_y + 12 * scale_factor), label, font=stat_label_font, fill=(150, 150, 150))
        draw.text((x_pos + 15 * scale_factor, detail_y + 45 * scale_factor), value, font=stat_value_font, fill=(255, 255, 255))
    
    # ========== INVENTÁRIO ==========
    inv_y = 560 * scale_factor
    
    draw.text((40 * scale_factor, inv_y), "INVENTÁRIO", font=stat_label_font, fill=(255, 255, 255))
    draw.line((40 * scale_factor, inv_y + 35 * scale_factor, 960 * scale_factor, inv_y + 35 * scale_factor), fill=(139, 92, 246, 80), width=2 * scale_factor)
    
    inv_y += 55 * scale_factor
    
    fundos = [item for item in inventory_items if item.get('item_type') == 'fundo_perfil']
    avatares = [item for item in inventory_items if item.get('item_type') == 'avatar_perfil']
    cargos = [item for item in inventory_items if item.get('item_type') in ['cargo_automatico', 'cargo_colorido']]
    licencas = [item for item in inventory_items if item.get('item_type') == 'licenca_comando']
    
    categories = []
    if fundos:
        categories.append(("Fundos", [item['item_name'] for item in fundos]))
    if avatares:
        categories.append(("Avatares", [item['item_name'] for item in avatares]))
    if cargos:
        categories.append(("Cargos", [item['item_name'] for item in cargos]))
    if licencas:
        categories.append(("Licenças", [item['item_name'] for item in licencas]))
    
    if categories:
        item_spacing = 240 * scale_factor
        for i, (emoji, items) in enumerate(categories):
            x_pos = 40 * scale_factor + (i * item_spacing)
            
            draw.text((x_pos, inv_y), emoji, font=small_font, fill=(255, 255, 255))
            
            item_text = ", ".join(items[:2])
            if len(items) > 2:
                item_text += f" +{len(items) - 2}"
            
            if len(item_text) > 28:
                item_text = item_text[:25] + "..."
            
            draw.text((x_pos, inv_y + 25 * scale_factor), item_text, font=tiny_font, fill=(180, 180, 180))
    else:
        draw.text((40 * scale_factor, inv_y), "Nenhum item ainda. Compre na /loja!", font=small_font, fill=(120, 120, 120))
    
    # Redimensionar para tamanho original antes de salvar
    card = card.resize((display_width, display_height), Image.Resampling.LANCZOS)
    
    # Salvar imagem
    final_buffer = BytesIO()
    card.save(final_buffer, format='PNG')
    final_buffer.seek(0)
    return final_buffer


# Variável global para uso na barra de XP
xp_for_level_base = 300


class ProfileView(ui.View):
    """View interativa para o perfil com seleção de categoria"""
    
    def __init__(self, bot: commands.Bot, target_user, guild_id: int, points_name: str, message=None, is_private: bool = False):
        super().__init__(timeout=180)
        self.bot = bot
        self.target_user = target_user
        self.guild_id = guild_id
        self.points_name = points_name
        self.message = message
        self.is_private = is_private
        self.fundos = []
        self.avatares = []
        self.current_fundo_index = 0
        self.current_avatar_index = 0
        self._load_items()
        
        btn_fundo = ui.Button(label="🎨 Fundo", style=discord.ButtonStyle.secondary, custom_id="selecionar_fundo", row=0)
        btn_avatar = ui.Button(label="👤 Avatar", style=discord.ButtonStyle.secondary, custom_id="selecionar_avatar", row=0)
        btn_bio = ui.Button(label="📝 Bio", style=discord.ButtonStyle.secondary, custom_id="editar_bio", row=0)
        
        btn_privado = ui.Button(
            label="🔓 Público" if is_private else "🔒 Privado",
            style=discord.ButtonStyle.secondary,
            custom_id="alternar_privado",
            row=0
        )
        
        async def btn_fundo_callback(interaction: Interaction):
            await self.selecionar_fundo(interaction, btn_fundo)
        
        async def btn_avatar_callback(interaction: Interaction):
            await self.selecionar_avatar(interaction, btn_avatar)
        
        async def btn_bio_callback(interaction: Interaction):
            await self.editar_bio(interaction, btn_bio)
        
        async def btn_privado_callback(interaction: Interaction):
            await self.alternar_privado(interaction, btn_privado)
        
        btn_fundo.callback = btn_fundo_callback
        btn_avatar.callback = btn_avatar_callback
        btn_bio.callback = btn_bio_callback
        btn_privado.callback = btn_privado_callback
        
        self.add_item(btn_fundo)
        self.add_item(btn_avatar)
        self.add_item(btn_bio)
        self.add_item(btn_privado)
    
    def _load_items(self):
        try:
            response = self.bot.supabase_client.table("user_inventories").select("*").eq("guild_id", self.guild_id).eq("user_id", self.target_user.id).execute()
            if response.data:
                for item in response.data:
                    if item.get('item_type') == 'fundo_perfil':
                        self.fundos.append(item)
                    elif item.get('item_type') == 'avatar_perfil':
                        self.avatares.append(item)
        except Exception as e:
            logging.error(f"Erro ao carregar itens: {e}")
    
    def _update_buttons(self):
        for child in self.children:
            if isinstance(child, ui.Button) and child.custom_id == "alternar_privado":
                if self.is_private:
                    child.label = "🔓 Público"
                else:
                    child.label = "🔒 Privado"
                break
    
    def _get_item_url(self, item):
        """Extrai a URL do item do campo item_data"""
        item_data = item.get('item_data', '')
        if not item_data:
            return None
        
        import json
        try:
            data = json.loads(item_data)
            if isinstance(data, dict):
                for key in ['https', 'image_url', 'url', 'img', 'preview']:
                    if key in data:
                        url = data[key]
                        if url.startswith('//'):
                            url = 'https:' + url
                        return url
            return None
        except:
            return None
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("Este perfil não é seu!", ephemeral=True)
            return False
        return True
    
    async def update_profile(self, interaction: Interaction):
        """Atualiza o perfil com novos dados"""
        try:
            profile_response = self.bot.supabase_client.table("gamification_profiles").select(
                "xp, profile_background_url, profile_avatar_url, message_count, profile_bio, is_private"
            ).eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            
            if not profile_response.data:
                return None
            
            profile_data = profile_response.data[0]
            
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", self.guild_id).execute()
            gamification_settings = {}
            if settings_response.data and len(settings_response.data) > 0:
                gamification_settings = settings_response.data[0].get('settings', {}).get('gamification_xp', {})
            
            points_name = gamification_settings.get('points_name', 'XP')
            xp_per_level_base = int(gamification_settings.get('xp_per_level_base', 300)) or 300
            coin_image_url = gamification_settings.get('coin_image_url')
            
            total_xp = profile_data.get('xp', 0)
            message_count = profile_data.get('message_count', 0)
            background_url = profile_data.get('profile_background_url')
            avatar_url = profile_data.get('profile_avatar_url')
            profile_bio = profile_data.get('profile_bio', '')
            
            calculated_level = total_xp // xp_per_level_base
            xp_at_start_of_level = calculated_level * xp_per_level_base
            xp_for_next_level_total = (calculated_level + 1) * xp_per_level_base
            xp_in_this_level = total_xp - xp_at_start_of_level
            total_xp_for_this_level_up = xp_for_next_level_total - xp_at_start_of_level
            
            days_in_server = 0
            if self.target_user.joined_at:
                delta = datetime.utcnow() - self.target_user.joined_at.replace(tzinfo=None)
                days_in_server = delta.days
            
            all_profiles = self.bot.supabase_client.table("gamification_profiles").select("user_id", "xp").eq("guild_id", self.guild_id).order("xp", desc=True).execute()
            total_members = len(all_profiles.data) if all_profiles.data else 0
            rank_position = 1
            if all_profiles.data:
                for p in all_profiles.data:
                    if p['user_id'] == self.target_user.id:
                        break
                    rank_position += 1
            
            inventory_response = self.bot.supabase_client.table("user_inventories").select("*").eq("guild_id", self.guild_id).eq("user_id", self.target_user.id).execute()
            inventory_items = inventory_response.data if inventory_response.data else []
            
            image_buffer = await create_rank_card(
                user_avatar_url=self.target_user.display_avatar.url,
                custom_avatar_url=avatar_url,
                user_name=self.target_user.display_name,
                current_level=calculated_level,
                current_xp_in_level=xp_in_this_level,
                xp_for_level_up=total_xp_for_this_level_up,
                points_name=points_name,
                total_xp=total_xp,
                background_url=background_url,
                message_count=message_count,
                days_in_server=days_in_server,
                rank_position=rank_position,
                total_members=total_members,
                inventory_items=inventory_items,
                equipped_background=background_url,
                equipped_avatar=avatar_url,
                profile_bio=profile_bio,
                coin_image_url=coin_image_url
            )
            
            return image_buffer
        except Exception as e:
            logging.error(f"Erro ao atualizar perfil: {e}")
            return None
    
    async def get_preview(self, target_user, preview_background_url=None, preview_avatar_url=None):
        """Gera uma prévia do perfil com background ou avatar temporário"""
        try:
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", self.guild_id).execute()
            gamification_settings = {}
            if settings_response.data and len(settings_response.data) > 0:
                gamification_settings = settings_response.data[0].get('settings', {}).get('gamification_xp', {})
            
            points_name = gamification_settings.get('points_name', 'XP')
            xp_per_level_base = int(gamification_settings.get('xp_per_level_base', 300)) or 300
            coin_image_url = gamification_settings.get('coin_image_url')
            
            profile_response = self.bot.supabase_client.table("gamification_profiles").select(
                "xp, profile_background_url, profile_avatar_url, message_count, profile_bio, is_private"
            ).eq("user_id", target_user.id).eq("guild_id", self.guild_id).execute()
            
            if not profile_response.data:
                return None
            
            profile_data = profile_response.data[0]
            total_xp = profile_data.get('xp', 0)
            message_count = profile_data.get('message_count', 0)
            
            current_background = profile_data.get('profile_background_url')
            current_avatar = profile_data.get('profile_avatar_url')
            profile_bio = profile_data.get('profile_bio', '')
            
            bg_url = preview_background_url if preview_background_url else current_background
            avatar_url = preview_avatar_url if preview_avatar_url else current_avatar
            
            calculated_level = total_xp // xp_per_level_base
            xp_at_start_of_level = calculated_level * xp_per_level_base
            xp_for_next_level_total = (calculated_level + 1) * xp_per_level_base
            xp_in_this_level = total_xp - xp_at_start_of_level
            total_xp_for_this_level_up = xp_for_next_level_total - xp_at_start_of_level
            
            days_in_server = 0
            if target_user.joined_at:
                delta = datetime.utcnow() - target_user.joined_at.replace(tzinfo=None)
                days_in_server = delta.days
            
            all_profiles = self.bot.supabase_client.table("gamification_profiles").select("user_id", "xp").eq("guild_id", self.guild_id).order("xp", desc=True).execute()
            total_members = len(all_profiles.data) if all_profiles.data else 0
            rank_position = 1
            if all_profiles.data:
                for p in all_profiles.data:
                    if p['user_id'] == target_user.id:
                        break
                    rank_position += 1
            
            inventory_response = self.bot.supabase_client.table("user_inventories").select("*").eq("guild_id", self.guild_id).eq("user_id", target_user.id).execute()
            inventory_items = inventory_response.data if inventory_response.data else []
            
            image_buffer = await create_rank_card(
                user_avatar_url=target_user.display_avatar.url,
                custom_avatar_url=avatar_url,
                user_name=target_user.display_name,
                current_level=calculated_level,
                current_xp_in_level=xp_in_this_level,
                xp_for_level_up=total_xp_for_this_level_up,
                points_name=points_name,
                total_xp=total_xp,
                background_url=bg_url,
                message_count=message_count,
                days_in_server=days_in_server,
                rank_position=rank_position,
                total_members=total_members,
                inventory_items=inventory_items,
                equipped_background=bg_url,
                equipped_avatar=avatar_url,
                profile_bio=profile_bio,
                coin_image_url=coin_image_url
            )
            
            return image_buffer
        except Exception as e:
            logging.error(f"Erro ao gerar preview: {e}")
            return None
    
    async def selecionar_fundo(self, interaction: Interaction, button: ui.Button):
        if not self.fundos:
            await interaction.response.send_message("Você não possui fundos de perfil! Compre na loja.", ephemeral=True)
            return
        
        self.current_fundo_index = 0
        
        view = ItemNavigatorView(self.bot, self.target_user, self.guild_id, self.fundos, "fundo_perfil", self)
        
        item = self.fundos[0]
        item_url = self._get_item_url(item)
        
        preview_buffer = await self.get_preview(self.target_user, preview_background_url=item_url)
        
        if preview_buffer:
            embed = Embed(title=f"📊 Perfil de {self.target_user.display_name}", color=discord.Color.blurple())
            embed.set_image(url="attachment://profile_card.png")
            await interaction.response.edit_message(embed=embed, attachments=[File(preview_buffer, filename="profile_card.png")], view=view)
        else:
            view = ItemNavigatorView(self.bot, self.target_user, self.guild_id, self.fundos, "fundo_perfil", self)
            item_name = item.get('item_name', 'Fundo')
            embed = Embed(title="🎨 Selecione um Fundo", description=f"**{item_name}**", color=discord.Color.blurple())
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def selecionar_avatar(self, interaction: Interaction, button: ui.Button):
        if not self.avatares:
            await interaction.response.send_message("Você não possui avatares de perfil! Compre na loja.", ephemeral=True)
            return
        
        self.current_avatar_index = 0
        
        item = self.avatares[0]
        item_url = self._get_item_url(item)
        
        preview_buffer = await self.get_preview(self.target_user, preview_avatar_url=item_url)
        
        if preview_buffer:
            view = ItemNavigatorView(self.bot, self.target_user, self.guild_id, self.avatares, "avatar_perfil", self)
            embed = Embed(title=f"📊 Perfil de {self.target_user.display_name}", color=discord.Color.blurple())
            embed.set_image(url="attachment://profile_card.png")
            await interaction.response.edit_message(embed=embed, attachments=[File(preview_buffer, filename="profile_card.png")], view=view)
        else:
            view = ItemNavigatorView(self.bot, self.target_user, self.guild_id, self.avatares, "avatar_perfil", self)
            item_name = item.get('item_name', 'Avatar')
            embed = Embed(title="👤 Selecione um Avatar", description=f"**{item_name}**", color=discord.Color.blurple())
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def editar_bio(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(BioModal(self.bot, self.target_user, self.guild_id, self.points_name))
    
    async def alternar_privado(self, interaction: Interaction, button: ui.Button):
        try:
            profile_response = self.bot.supabase_client.table("gamification_profiles").select("is_private").eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            current_state = profile_response.data[0].get('is_private', False) if profile_response.data else False
            
            new_state = not current_state
            
            self.bot.supabase_client.table("gamification_profiles").update({
                "is_private": new_state
            }).eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            
            self.is_private = new_state
            
            for child in self.children:
                if isinstance(child, ui.Button) and child.custom_id == "alternar_privado":
                    child.label = "🔓 Público" if new_state else "🔒 Privado"
                    break
            
            status = "privado" if new_state else "público"
            await interaction.response.send_message(f"Perfil alterado para **{status}**!", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao alternar privacidade: {e}")
            await interaction.response.send_message("Erro ao alterar privacidade.", ephemeral=True)


class BioModal(ui.Modal):
    def __init__(self, bot: commands.Bot, target_user, guild_id: int, points_name: str):
        super().__init__(title="Editar Bio")
        self.bot = bot
        self.target_user = target_user
        self.guild_id = guild_id
        self.points_name = points_name
        
        profile_response = bot.supabase_client.table("gamification_profiles").select("profile_bio").eq("user_id", target_user.id).eq("guild_id", guild_id).execute()
        current_bio = profile_response.data[0].get('profile_bio', '') if profile_response.data else ''
        current_bio = current_bio.replace('\n', ' ').replace('\r', '')
        
        self.bio = ui.TextInput(label="Sua Bio", style=TextStyle.short, default=current_bio, placeholder="Escreva algo sobre você...", max_length=100, required=False)
        self.add_item(self.bio)
    
    async def on_submit(self, interaction: Interaction):
        try:
            bio_text = self.bio.value.replace('\n', ' ').replace('\r', '')
            self.bot.supabase_client.table("gamification_profiles").update({
                "profile_bio": bio_text
            }).eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", self.guild_id).execute()
            gamification_settings = {}
            if settings_response.data and len(settings_response.data) > 0:
                gamification_settings = settings_response.data[0].get('settings', {}).get('gamification_xp', {})
            coin_image_url = gamification_settings.get('coin_image_url')
            xp_per_level_base = int(gamification_settings.get('xp_per_level_base', 300)) or 300
            
            profile_response = self.bot.supabase_client.table("gamification_profiles").select(
                "xp, profile_background_url, profile_avatar_url"
            ).eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            
            profile_data = profile_response.data[0] if profile_response.data else {}
            bg_url = profile_data.get('profile_background_url')
            avatar_url = profile_data.get('profile_avatar_url')
            total_xp = profile_data.get('xp', 0)
            
            calculated_level = total_xp // xp_per_level_base
            xp_at_start_of_level = calculated_level * xp_per_level_base
            xp_for_next_level_total = (calculated_level + 1) * xp_per_level_base
            xp_in_this_level = total_xp - xp_at_start_of_level
            total_xp_for_this_level_up = xp_for_next_level_total - xp_at_start_of_level
            
            image_buffer = await create_rank_card(
                user_avatar_url=self.target_user.display_avatar.url,
                custom_avatar_url=avatar_url,
                user_name=self.target_user.display_name,
                current_level=calculated_level,
                current_xp_in_level=xp_in_this_level,
                xp_for_level_up=total_xp_for_this_level_up,
                points_name=self.points_name,
                total_xp=total_xp,
                background_url=bg_url,
                profile_bio=bio_text,
                coin_image_url=coin_image_url
            )
            filename = "profile_card.png"
            
            embed = Embed(title=f"📊 Bio de {self.target_user.display_name}", color=discord.Color.blurple())
            embed.set_image(url=f"attachment://{filename}")
            
            profile_resp = self.bot.supabase_client.table("gamification_profiles").select("is_private").eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            is_private = profile_resp.data[0].get('is_private', False) if profile_resp.data else False
            
            view = ProfileView(self.bot, self.target_user, self.guild_id, self.points_name, is_private=is_private)
            await interaction.response.send_message(embed=embed, file=File(image_buffer, filename=filename), view=view, ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao salvar bio: {e}")
            await interaction.response.send_message("Erro ao salvar bio.", ephemeral=True)


class ItemNavigatorView(ui.View):
    """View para navegar entre itens do inventário"""
    
    def __init__(self, bot: commands.Bot, target_user, guild_id: int, items: list, item_type: str, parent_view):
        super().__init__(timeout=180)
        self.bot = bot
        self.target_user = target_user
        self.guild_id = guild_id
        self.items = items
        self.item_type = item_type
        self.parent_view = parent_view
        self.current_index = 0
        
        self._update_button_labels()
    
    def _update_button_labels(self):
        self.clear_items()
        
        item = self.items[self.current_index]
        item_name = item.get('item_name', 'Item')[:20]
        
        prev_btn = ui.Button(label="◀", style=discord.ButtonStyle.secondary)
        prev_btn.callback = self.prev_item
        self.add_item(prev_btn)
        
        equip_btn = ui.Button(label=item_name, style=discord.ButtonStyle.success)
        equip_btn.callback = self.equip_item
        self.add_item(equip_btn)
        
        next_btn = ui.Button(label="▶", style=discord.ButtonStyle.secondary)
        next_btn.callback = self.next_item
        self.add_item(next_btn)
    
    def _get_item_url(self, item):
        """Extrai a URL do item do campo item_data"""
        item_data = item.get('item_data', '')
        if not item_data:
            return None
        
        import json
        try:
            data = json.loads(item_data)
            if isinstance(data, dict):
                for key in ['https', 'image_url', 'url', 'img', 'preview']:
                    if key in data:
                        url = data[key]
                        if url.startswith('//'):
                            url = 'https:' + url
                        return url
            return None
        except:
            return None
    
    async def prev_item(self, interaction: Interaction):
        self.current_index = (self.current_index - 1) % len(self.items)
        self._update_button_labels()
        
        item = self.items[self.current_index]
        item_url = self._get_item_url(item)
        
        if self.item_type == "fundo_perfil":
            preview_url = item_url
            avatar_url = None
        else:
            preview_url = None
            avatar_url = item_url
        
        preview_buffer = await self.parent_view.get_preview(self.target_user, preview_url, avatar_url)
        
        if preview_buffer:
            embed = Embed(title=f"📊 {item.get('item_name', 'Item')}", color=discord.Color.blurple())
            embed.set_image(url="attachment://profile_card.png")
            await interaction.response.edit_message(embed=embed, attachments=[File(preview_buffer, filename="profile_card.png")], view=self)
        else:
            await interaction.response.defer()
    
    async def next_item(self, interaction: Interaction):
        self.current_index = (self.current_index + 1) % len(self.items)
        self._update_button_labels()
        
        item = self.items[self.current_index]
        item_url = self._get_item_url(item)
        
        if self.item_type == "fundo_perfil":
            preview_url = item_url
            avatar_url = None
        else:
            preview_url = None
            avatar_url = item_url
        
        preview_buffer = await self.parent_view.get_preview(self.target_user, preview_url, avatar_url)
        
        if preview_buffer:
            embed = Embed(title=f"📊 {item.get('item_name', 'Item')}", color=discord.Color.blurple())
            embed.set_image(url="attachment://profile_card.png")
            await interaction.response.edit_message(embed=embed, attachments=[File(preview_buffer, filename="profile_card.png")], view=self)
        else:
            await interaction.response.defer()
    
    async def equip_item(self, interaction: Interaction):
        item = self.items[self.current_index]
        item_url = self._get_item_url(item)
        
        try:
            if self.item_type == "fundo_perfil":
                self.bot.supabase_client.table("gamification_profiles").update({
                    "profile_background_url": item_url
                }).eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            else:
                self.bot.supabase_client.table("gamification_profiles").update({
                    "profile_avatar_url": item_url
                }).eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
            
            image_buffer = await self.parent_view.update_profile(interaction)
            
            if image_buffer:
                embed = Embed(title=f"📊 Perfil de {self.target_user.display_name}", color=discord.Color.blurple())
                embed.set_image(url="attachment://profile_card.png")
                
                profile_resp = self.bot.supabase_client.table("gamification_profiles").select("is_private").eq("user_id", self.target_user.id).eq("guild_id", self.guild_id).execute()
                is_private = profile_resp.data[0].get('is_private', False) if profile_resp.data else False
                
                new_view = ProfileView(self.bot, self.target_user, self.guild_id, self.parent_view.points_name, is_private=is_private)
                await interaction.response.edit_message(embed=embed, attachments=[File(image_buffer, filename="profile_card.png")], view=new_view)
            
            await interaction.followup.send(f"✅ **{item.get('item_name')}** equipado!", ephemeral=True)
            
        except Exception as e:
            logging.error(f"Erro ao equipar: {e}")
            await interaction.response.send_message(f"Erro: {str(e)}", ephemeral=True)


class PerfilCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="perfil", description="Mostra seu cartão de perfil completo com estatísticas e inventário.")
    @app_commands.describe(membro="O membro que você quer ver o perfil. Deixe em branco para ver o seu.")
    async def perfil(self, interaction: Interaction, membro: discord.Member = None):
        target_user = membro or interaction.user
        if target_user.bot:
            return await interaction.response.send_message("Bots não participam do sistema de níveis.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        try:
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            gamification_settings = {}
            if settings_response.data and len(settings_response.data) > 0:
                gamification_settings = settings_response.data[0].get('settings', {}).get('gamification_xp', {})
            
            points_name = gamification_settings.get('points_name', 'XP')
            xp_per_level_base = int(gamification_settings.get('xp_per_level_base', 300)) or 300
            coin_image_url = gamification_settings.get('coin_image_url')
            
            profile_response = self.bot.supabase_client.table("gamification_profiles").select(
                "xp, profile_background_url, profile_avatar_url, message_count, profile_bio, is_private"
            ).eq("user_id", target_user.id).eq("guild_id", guild_id).execute()
            
            if not profile_response.data:
                return await interaction.followup.send(f"{target_user.mention} ainda não tem {points_name}. Comece a conversar para ganhar XP!")
            
            profile_data = profile_response.data[0]
            total_xp = profile_data.get('xp', 0)
            message_count = profile_data.get('message_count', 0)
            background_url = profile_data.get('profile_background_url')
            avatar_url = profile_data.get('profile_avatar_url')
            profile_bio = profile_data.get('profile_bio', '')
            is_private = profile_data.get('is_private', False)
            
            if is_private and target_user.id != interaction.user.id:
                if not interaction.user.guild_permissions.administrator:
                    return await interaction.followup.send(f"❌ O perfil de {target_user.display_name} é privado!", ephemeral=True)
            
            calculated_level = total_xp // xp_per_level_base
            xp_at_start_of_level = calculated_level * xp_per_level_base
            xp_for_next_level_total = (calculated_level + 1) * xp_per_level_base
            xp_in_this_level = total_xp - xp_at_start_of_level
            total_xp_for_this_level_up = xp_for_next_level_total - xp_at_start_of_level
            
            days_in_server = 0
            if target_user.joined_at:
                delta = datetime.utcnow() - target_user.joined_at.replace(tzinfo=None)
                days_in_server = delta.days
            
            all_profiles = self.bot.supabase_client.table("gamification_profiles").select("user_id", "xp").eq("guild_id", guild_id).order("xp", desc=True).execute()
            total_members = len(all_profiles.data) if all_profiles.data else 0
            rank_position = 1
            if all_profiles.data:
                for p in all_profiles.data:
                    if p['user_id'] == target_user.id:
                        break
                    rank_position += 1
            
            inventory_response = self.bot.supabase_client.table("user_inventories").select("*").eq("guild_id", guild_id).eq("user_id", target_user.id).execute()
            inventory_items = inventory_response.data if inventory_response.data else []
            
            global xp_for_level_base
            xp_for_level_base = xp_per_level_base
            
            image_buffer = await create_rank_card(
                user_avatar_url=target_user.display_avatar.url,
                custom_avatar_url=avatar_url,
                user_name=target_user.display_name,
                current_level=calculated_level,
                current_xp_in_level=xp_in_this_level,
                xp_for_level_up=total_xp_for_this_level_up,
                points_name=points_name,
                total_xp=total_xp,
                background_url=background_url,
                message_count=message_count,
                days_in_server=days_in_server,
                rank_position=rank_position,
                total_members=total_members,
                inventory_items=inventory_items,
                equipped_background=background_url,
                equipped_avatar=avatar_url,
                profile_bio=profile_bio,
                coin_image_url=coin_image_url
            )
            
            embed = Embed(
                title=f"📊 Perfil de {target_user.display_name}",
                color=discord.Color.blurple()
            )
            embed.set_image(url="attachment://profile_card.png")
            
            if target_user.id == interaction.user.id:
                view = ProfileView(self.bot, target_user, guild_id, points_name, is_private=is_private)
                await interaction.followup.send(
                    embed=embed,
                    file=File(image_buffer, filename="profile_card.png"),
                    view=view,
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    embed=embed,
                    file=File(image_buffer, filename="profile_card.png"),
                    ephemeral=True
                )
            
        except Exception as e:
            import traceback
            logging.error(f"Erro no comando /perfil: {e}\n{traceback.format_exc()}")
            await interaction.followup.send("Ocorreu um erro ao gerar o seu cartão de perfil.")


async def setup(bot: commands.Bot):
    await bot.add_cog(PerfilCommand(bot))
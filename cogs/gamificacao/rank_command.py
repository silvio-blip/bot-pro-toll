
import discord
from discord.ext import commands
from discord import app_commands, Interaction, File
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from io import BytesIO

# --- Função para Gerar o Cartão de Perfil ---
async def create_rank_card(user_avatar_url: str, user_name: str, current_level: int, current_xp_in_level: int, xp_for_level_up: int, points_name: str, background_url: str = None, custom_avatar_url: str = None) -> BytesIO:
    """Gera uma imagem de cartão de perfil para o usuário, com fundo e avatar personalizáveis."""
    try:
        title_font = ImageFont.truetype("assets/fonts/Poppins-Bold.ttf", 40)
        regular_font = ImageFont.truetype("assets/fonts/Poppins-Regular.ttf", 25)
        small_font = ImageFont.truetype("assets/fonts/Poppins-Regular.ttf", 20)
    except IOError:
        title_font, regular_font, small_font = ImageFont.load_default(), ImageFont.load_default(), ImageFont.load_default()

    card_width, card_height = 800, 200

    # Fundo do cartão
    if background_url:
        try:
            response = requests.get(background_url)
            card = Image.open(BytesIO(response.content)).convert("RGBA")
            img_ratio, card_ratio = card.width / card.height, card_width / card_height
            new_width, new_height = (int(card_height * img_ratio), card_height) if img_ratio > card_ratio else (card_width, int(card_width / img_ratio))
            card = card.resize((new_width, new_height), Image.Resampling.LANCZOS)
            left, top = (card.width - card_width) / 2, (card.height - card_height) / 2
            card = card.crop((left, top, left + card_width, top + card_height))
        except Exception as e:
            logging.error(f"Erro ao processar imagem de fundo: {e}")
            card = Image.new("RGBA", (card_width, card_height), (40, 43, 48, 255))
    else:
        card = Image.new("RGBA", (card_width, card_height), (40, 43, 48, 255))

    # Sobreposição e máscara
    card.paste(Image.new("RGBA", card.size, (0, 0, 0, 150)), (0, 0), Image.new("RGBA", card.size, (0, 0, 0, 150)))
    mask = Image.new("L", card.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0) + card.size, radius=20, fill=255); card.putalpha(mask)

    # Avatar do usuário
    avatar_url_to_use = custom_avatar_url or user_avatar_url
    try:
        response = requests.get(avatar_url_to_use)
        avatar_bytes = BytesIO(response.content)
        avatar = Image.open(avatar_bytes).convert("RGBA").resize((150, 150))
    except Exception as e:
        logging.error(f"Falha ao carregar avatar de '{avatar_url_to_use}', usando avatar padrão. Erro: {e}")
        response = requests.get(user_avatar_url)
        avatar_bytes = BytesIO(response.content)
        avatar = Image.open(avatar_bytes).convert("RGBA").resize((150, 150))

    avatar_mask = Image.new("L", avatar.size, 0); draw_avatar_mask = ImageDraw.Draw(avatar_mask); draw_avatar_mask.ellipse((0, 0) + avatar.size, fill=255); avatar.putalpha(avatar_mask)
    card.paste(avatar, (25, 25), avatar)

    # Textos e Barra de XP
    draw = ImageDraw.Draw(card)
    draw.text((200, 30), user_name, font=title_font, fill=(255, 255, 255))
    draw.text((200, 90), f"Nível {current_level}", font=regular_font, fill=(200, 200, 200))
    xp_progress = min(current_xp_in_level / xp_for_level_up, 1.0) if xp_for_level_up > 0 else 1.0
    draw.rounded_rectangle((200, 140, 750, 165), radius=10, fill=(70, 70, 70))
    if xp_progress > 0: draw.rounded_rectangle((200, 140, 200 + (550 * xp_progress), 165), radius=10, fill=(0, 255, 127))
    xp_text = f"{current_xp_in_level} / {xp_for_level_up} {points_name}"; text_width = draw.textlength(xp_text, font=small_font)
    draw.text((750 - text_width, 105), xp_text, font=small_font, fill=(255, 255, 255))

    final_buffer = BytesIO(); card.save(final_buffer, format='PNG'); final_buffer.seek(0)
    return final_buffer

# --- Cog Principal ---
class PerfilCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="perfil", description="Mostra seu cartão de perfil, com seu nível, XP e customizações.")
    @app_commands.describe(membro="O membro que você quer ver o perfil. Deixe em branco para ver o seu.")
    async def perfil(self, interaction: Interaction, membro: discord.Member = None):
        target_user = membro or interaction.user
        if target_user.bot: return await interaction.response.send_message("Bots não participam do sistema de níveis.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id

        try:
            settings_response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            gamification_settings = settings_response.data[0].get('settings', {}).get('gamification_xp', {}) if settings_response.data else {}
            points_name = gamification_settings.get('points_name', 'XP')
            xp_per_level_base = int(gamification_settings.get('xp_per_level_base', 300)) or 300

            profile_response = self.bot.supabase_client.table("gamification_profiles").select("xp, profile_background_url, profile_avatar_url").eq("user_id", target_user.id).eq("guild_id", guild_id).execute()

            if not profile_response.data:
                return await interaction.followup.send(f"{target_user.mention} ainda não tem {points_name}.")

            profile_data = profile_response.data[0]
            total_xp = profile_data.get('xp', 0)
            background_url = profile_data.get('profile_background_url')
            avatar_url = profile_data.get('profile_avatar_url')

            calculated_level = total_xp // xp_per_level_base
            xp_at_start_of_level = calculated_level * xp_per_level_base
            xp_for_next_level_total = (calculated_level + 1) * xp_per_level_base
            xp_in_this_level = total_xp - xp_at_start_of_level
            total_xp_for_this_level_up = xp_for_next_level_total - xp_at_start_of_level

            image_buffer = await create_rank_card(
                user_avatar_url=target_user.display_avatar.url,
                custom_avatar_url=avatar_url,
                user_name=target_user.display_name,
                current_level=calculated_level,
                current_xp_in_level=xp_in_this_level,
                xp_for_level_up=total_xp_for_this_level_up,
                points_name=points_name,
                background_url=background_url
            )
            
            await interaction.followup.send(file=File(image_buffer, filename="rank_card.png"))

        except Exception as e:
            logging.error(f"Erro no comando /perfil: {e}")
            await interaction.followup.send("Ocorreu um erro ao gerar o seu cartão de perfil.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PerfilCommand(bot))

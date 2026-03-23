
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, TextStyle, ButtonStyle, SelectOption, Embed, Color
import logging
import re

BUTTON_COLORS = {
    "primary": ButtonStyle.primary,
    "secondary": ButtonStyle.secondary,
    "success": ButtonStyle.success,
    "danger": ButtonStyle.danger,
}

def parse_color(color_str: str) -> int:
    color_map = {
        'blurple': 0x5865F2,
        'blue': 0x3498db,
        'green': 0x2ecc71,
        'red': 0xe74c3c,
        'yellow': 0xf1c40f,
        'orange': 0xe67e22,
        'purple': 0x9b59b6,
        'pink': 0xe91e63,
        'white': 0xffffff,
        'black': 0x000000,
        'gold': 0xffd700,
        'teal': 0x008080,
    }
    color_str = color_str.strip().lower()
    if color_str in color_map:
        return color_map[color_str]
    if color_str.startswith('#') or color_str.startswith('0x'):
        try:
            return int(color_str, 16)
        except:
            pass
    try:
        return int(color_str)
    except:
        return 0x5865F2

def parse_buttons(buttons_str: str) -> list:
    if not buttons_str or not buttons_str.strip():
        return []
    
    buttons = []
    lines = [l.strip() for l in buttons_str.strip().split('\n') if l.strip()]
    
    for line in lines:
        parts = [p.strip() for p in line.split('|')]
        
        btn = {
            'label': 'Botão',
            'url': '',
            'emoji': '',
            'style': 'primary'
        }
        
        for part in parts:
            if not part:
                continue
            if part.startswith('<') and part.endswith('>'):
                btn['emoji'] = part
            elif part.lower() in BUTTON_COLORS:
                btn['style'] = part.lower()
            elif part.startswith('http'):
                btn['url'] = part
            elif not btn['label'] or btn['label'] == 'Botão':
                btn['label'] = part
        
        if btn['url']:
            buttons.append(btn)
    
    return buttons

def build_embed_view(title, description, image_url, color, buttons):
    embed = Embed(
        title=title if title else None,
        description=description if description else None,
        color=color if color else 0x5865F2
    )
    
    if image_url:
        embed.set_image(url=image_url)
    
    view = ui.View()
    for btn in buttons:
        emoji = btn.get('emoji') if btn.get('emoji') else None
        try:
            emoji = discord.PartialEmoji.from_str(emoji) if emoji else None
        except:
            emoji = None
        button = ui.Button(
            label=btn.get('label', 'Botão')[:80],
            url=btn.get('url', ''),
            style=BUTTON_COLORS.get(btn.get('style', 'primary'), ButtonStyle.primary),
            emoji=emoji
        )
        view.add_item(button)
    
    return embed, view if view.children else None


class EmbedBuilderView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.embed_data = {
            'title': None,
            'description': None,
            'image_url': None,
            'color': 0x5865F2,
            'buttons': [],
            'channel': None
        }
    
    @ui.button(label="📝 Título & Descrição", style=ButtonStyle.primary, row=0)
    async def edit_text(self, interaction: Interaction, button: ui.Button):
        modal = TextModal(self.bot, self.embed_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🖼️ Imagem", style=ButtonStyle.primary, row=0)
    async def edit_image(self, interaction: Interaction, button: ui.Button):
        modal = ImageModal(self.bot, self.embed_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🎨 Cor", style=ButtonStyle.primary, row=0)
    async def edit_color(self, interaction: Interaction, button: ui.Button):
        modal = ColorModal(self.bot, self.embed_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🔘 Botões", style=ButtonStyle.primary, row=1)
    async def edit_buttons(self, interaction: Interaction, button: ui.Button):
        modal = ButtonsModal(self.bot, self.embed_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="📌 Canal", style=ButtonStyle.secondary, row=1)
    async def edit_channel(self, interaction: Interaction, button: ui.Button):
        modal = ChannelModal(self.bot, self.embed_data)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="👁️ Preview", style=ButtonStyle.secondary, row=1)
    async def preview(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed, view = build_embed_view(
            self.embed_data['title'],
            self.embed_data['description'],
            self.embed_data['image_url'],
            self.embed_data['color'],
            self.embed_data['buttons']
        )
        if embed.description or embed.title or self.embed_data['image_url']:
            await interaction.followup.send("📋 Preview do Embed:", embed=embed, view=view if view else discord.ui.View(), ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Adicione conteúdo ao embed primeiro!", ephemeral=True)
    
    @ui.button(label="✅ Enviar", style=ButtonStyle.success, row=2)
    async def send(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        channel = self.embed_data['channel'] or interaction.channel
        
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("❌ O canal selecionado não é válido!", ephemeral=True)
            return
        
        embed, view = build_embed_view(
            self.embed_data['title'],
            self.embed_data['description'],
            self.embed_data['image_url'],
            self.embed_data['color'],
            self.embed_data['buttons']
        )
        
        if not embed.title and not embed.description and not self.embed_data['image_url']:
            await interaction.followup.send("⚠️ O embed precisa ter pelo menos um título, descrição ou imagem!", ephemeral=True)
            return
        
        try:
            await channel.send(embed=embed, view=view if view else discord.ui.View())
            await interaction.followup.send(f"✅ Embed enviado para {channel.mention}!", ephemeral=True)
            self.stop()
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao enviar: {e}", ephemeral=True)
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.danger, row=2)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        self.stop()
        await interaction.response.send_message("❌ Criação de embed cancelada.", ephemeral=True)


class TextModal(ui.Modal, title="Título e Descrição"):
    def __init__(self, bot, embed_data: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.embed_data = embed_data
        
        self.add_item(ui.TextInput(
            label="Título",
            placeholder="Deixe vazio para remover",
            default=embed_data.get('title') or '',
            required=False
        ))
        self.add_item(ui.TextInput(
            label="Descrição",
            placeholder="Deixe vazio para remover",
            style=TextStyle.long,
            default=embed_data.get('description') or '',
            required=False
        ))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        self.embed_data['title'] = self.children[0].value.strip() or None
        self.embed_data['description'] = self.children[1].value.strip() or None
        await interaction.followup.send("✅ Título e descrição atualizados!", ephemeral=True)


class ImageModal(ui.Modal, title="Imagem"):
    def __init__(self, bot, embed_data: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.embed_data = embed_data
        
        self.add_item(ui.TextInput(
            label="URL da Imagem",
            placeholder="https://exemplo.com/imagem.png",
            default=embed_data.get('image_url') or '',
            required=False
        ))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        url = self.children[0].value.strip()
        if url:
            self.embed_data['image_url'] = url
            await interaction.followup.send("✅ Imagem adicionada!", ephemeral=True)
        else:
            self.embed_data['image_url'] = None
            await interaction.followup.send("✅ Imagem removida!", ephemeral=True)


class ColorModal(ui.Modal, title="Cor"):
    def __init__(self, bot, embed_data: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.embed_data = embed_data
        
        self.add_item(ui.TextInput(
            label="Cor (hex, nome ou número)",
            placeholder="blue, #5865F2, 0x5865F2",
            default=hex(embed_data.get('color', 0x5865F2)),
            required=True
        ))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        color = parse_color(self.children[0].value)
        self.embed_data['color'] = color
        await interaction.followup.send(f"✅ Cor atualizada! (Hex: {hex(color)})", ephemeral=True)


class ButtonsModal(ui.Modal, title="Botões"):
    def __init__(self, bot, embed_data: dict):
        super().__init__(timeout=600)
        self.bot = bot
        self.embed_data = embed_data
        
        buttons_text = ""
        for btn in embed_data.get('buttons', []):
            parts = [btn.get('label', ''), btn.get('url', ''), btn.get('emoji', ''), btn.get('style', 'primary')]
            buttons_text += " | ".join(p for p in parts if p) + "\n"
        
        self.add_item(ui.TextInput(
            label="Botões (formato: label | url | emoji | style)",
            placeholder="Google | https://google.com | 🌐 | primary\nYouTube | https://youtube.com | 📺 | success",
            style=TextStyle.long,
            default=buttons_text.strip(),
            required=False
        ))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        buttons = parse_buttons(self.children[0].value)
        self.embed_data['buttons'] = buttons
        await interaction.followup.send(f"✅ {len(buttons)} botão(ões) adicionado(s)!", ephemeral=True)


class ChannelModal(ui.Modal, title="Canal"):
    def __init__(self, bot, embed_data: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.embed_data = embed_data
        
        channel_id_default = str(embed_data['channel'].id) if embed_data.get('channel') else ''
        
        self.add_item(ui.TextInput(
            label="ID do Canal",
            placeholder="Cole o ID do canal (clique com botão direito no canal e copiar ID)",
            default=channel_id_default,
            required=False
        ))
    
    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        channel_input = self.children[0]
        if not isinstance(channel_input, ui.TextInput):
            await interaction.followup.send("❌ Erro interno.", ephemeral=True)
            return
        
        channel_id_str = channel_input.value.strip()
        
        if not channel_id_str:
            self.embed_data['channel'] = None
            await interaction.followup.send("✅ Canal definido como o canal atual!", ephemeral=True)
            return
        
        try:
            channel_id = int(channel_id_str)
            guild = interaction.guild
            if guild:
                channel = guild.get_channel(channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    self.embed_data['channel'] = channel
                    await interaction.followup.send(f"✅ Canal definido como {channel.mention}!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Canal não encontrado ou não é um canal de texto.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao acessar o servidor.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ ID do canal deve ser um número.", ephemeral=True)


class EmbedsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="embed", description="[ADM] Cria uma mensagem embed personalizada com botões.")
    @app_commands.describe(
        canal="Canal onde o embed será enviado (padrão: canal atual)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_command(self, interaction: Interaction, canal: discord.TextChannel = None):
        embed_data: dict = {
            'title': None,
            'description': None,
            'image_url': None,
            'color': 0x5865F2,
            'buttons': [],
            'channel': canal if canal else interaction.channel
        }
        
        embed = Embed(
            title="🎨 Criador de Embed",
            description="Use os botões abaixo para personalizar seu embed.\nTodos os campos são opcionais!",
            color=0x5865F2
        )
        embed.add_field(
            name="📋 Como usar:",
            value="1️⃣ Clique em **Título & Descrição** para adicionar texto\n"
                  "2️⃣ Clique em **Imagem** para adicionar uma imagem\n"
                  "3️⃣ Clique em **Cor** para mudar a cor do embed\n"
                  "4️⃣ Clique em **Botões** para adicionar botões clicáveis\n"
                  "5️⃣ Use **Preview** para ver como vai ficar\n"
                  "6️⃣ Clique **Enviar** quando estiver pronto!",
            inline=False
        )
        
        view = EmbedBuilderView(self.bot)
        view.embed_data = embed_data
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @embed_command.error
    async def on_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ Apenas administradores podem usar este comando.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ocorreu um erro.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedsCog(bot))

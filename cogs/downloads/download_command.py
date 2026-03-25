import discord
from discord import app_commands, ui, ButtonStyle
from discord.ext import commands
from discord import Interaction
import asyncio
import logging
import os
from .video_handler import VideoDownloader
from .zip_handler import ZipHandler
from .utils import validar_url, formatar_tamanho
from .config import MAX_DISCORD_SIZE

logger = logging.getLogger("DownloadCommand")

class DeleteAudioView(ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = message_id
    
    @ui.button(label="🗑️ Excluir", style=ButtonStyle.danger, custom_id="delete_audio_btn")
    async def delete_button(self, interaction: Interaction, button: ui.Button):
        try:
            msg = await interaction.channel.fetch_message(self.message_id)
            await msg.delete()
            await interaction.response.send_message("✅ Excluído!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("Mensagem já foi excluída.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("Erro ao excluir.", ephemeral=True)

class DownloadCommand(commands.Cog, name="📥 Downloads"):
    def __init__(self, bot):
        self.bot = bot
        self.downloader = VideoDownloader()
        self.zip_handler = ZipHandler()
        self.user_cooldowns = {}
        bot.add_view(DeleteAudioView(0))

    def verificar_cooldown(self, user_id: int) -> bool:
        import time
        now = time.time()
        ultimo = self.user_cooldowns.get(user_id, 0)
        if now - ultimo < 30:
            return False
        self.user_cooldowns[user_id] = now
        return True

    @app_commands.command(
        name="baixar",
        description="[🎵] Baixa apenas o áudio de vídeos do TikTok, Instagram, YouTube ou Twitter."
    )
    @app_commands.describe(url="Cole o link do vídeo aqui")
    async def baixar(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not validar_url(url):
            await interaction.followup.send(
                "❌ URL inválida ou site não suportado.\n"
                "Sites suportados: TikTok, Instagram, Twitter/X, YouTube, Facebook, Reddit, SoundCloud",
                ephemeral=True
            )
            return

        if not self.verificar_cooldown(interaction.user.id):
            await interaction.followup.send(
                "⏳ Aguarde 30 segundos entre cada download.",
                ephemeral=True
            )
            return

        file_path = None
        arquivo_para_enviar = None
        
        try:
            file_path, title, provider = await asyncio.to_thread(
                self.downloader.download, url, interaction.user.id
            )

            if not file_path:
                await interaction.followup.send(
                    "❌ Não consegui baixar o vídeo. Verifique se o link é público.",
                    ephemeral=True
                )
                return

            tamanho = os.path.getsize(file_path)
            
            arquivo_para_enviar = file_path
            tipo_envio = "Áudio MP3"

            if tamanho > MAX_DISCORD_SIZE:
                await interaction.followup.send(
                    "⏳ Vídeo muito grande, compactando...",
                    ephemeral=True
                )
                arquivo_para_enviar = self.zip_handler.compactar_video(file_path, interaction.user.id)
                if not arquivo_para_enviar:
                    await interaction.followup.send(
                        "❌ Mesmo compactado o arquivo ainda é muito grande para o Discord (25MB).",
                        ephemeral=True
                    )
                    self.zip_handler.limpar_arquivo(file_path)
                    return
                tipo_envio = "ZIP"

            file = discord.File(arquivo_para_enviar)

            try:
                view = DeleteAudioView(0)
                msg = await interaction.user.send(
                    f"✅ **Download Concluído!**\n\n**{title}**\n🎵 Tipo: `{tipo_envio}` | 💾 Tamanho: `{formatar_tamanho(tamanho)}`\n🔗 Provedor: `{provider}`",
                    file=file,
                    view=view
                )
                view.message_id = msg.id
                await msg.edit(view=view)
                
                await interaction.followup.send(
                    "📬 Áudio enviado no seu DM!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Não consegui enviar no DM. Verifique se você aceita DM de servidores.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Erro no download: {e}")
            await interaction.followup.send(
                "❌ Ocorreu um erro ao processar o vídeo.",
                ephemeral=True
            )
        finally:
            if file_path and os.path.exists(file_path):
                self.zip_handler.limpar_arquivo(file_path)
            if arquivo_para_enviar and arquivo_para_enviar != file_path and os.path.exists(arquivo_para_enviar):
                self.zip_handler.limpar_arquivo(arquivo_para_enviar)


async def setup(bot):
    await bot.add_cog(DownloadCommand(bot))

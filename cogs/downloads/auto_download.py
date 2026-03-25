import discord
from discord.ext import commands
import asyncio
import logging
import os
from .video_handler import VideoDownloader
from .zip_handler import ZipHandler
from .utils import extrair_url, validar_url, formatar_tamanho
from .config import MAX_DISCORD_SIZE

logger = logging.getLogger("AutoDownload")

class AutoDownload(commands.Cog, name="📥 Auto-Download"):
    def __init__(self, bot):
        self.bot = bot
        self.downloader = VideoDownloader()
        self.zip_handler = ZipHandler()
        self.processando = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        url = extrair_url(message.content)
        if not url or not validar_url(url):
            return
        
        if message.author.id in self.processando:
            return
        
        self.processando.add(message.author.id)
        
        file_path = None
        arquivo_para_enviar = None
        
        try:
            await message.add_reaction("⏳")
            
            file_path, title, provider = await asyncio.to_thread(
                self.downloader.download, url, message.author.id
            )
            
            if not file_path:
                await message.remove_reaction("⏳", self.bot.user)
                await message.add_reaction("❌")
                await message.reply(
                    "❌ Não consegui baixar. Verifique se o link é público.",
                    delete_after=10
                )
                return
            
            tamanho = os.path.getsize(file_path)
            arquivo_para_enviar = file_path
            tipo_envio = "Áudio MP3"
            
            if tamanho > MAX_DISCORD_SIZE:
                arquivo_para_enviar = self.zip_handler.compactar_video(file_path, message.author.id)
                if not arquivo_para_enviar:
                    await message.remove_reaction("⏳", self.bot.user)
                    await message.add_reaction("❌")
                    await message.reply(
                        "❌ Vídeo muito grande para o Discord (acima de 25MB).",
                        delete_after=10
                    )
                    self.zip_handler.limpar_arquivo(file_path)
                    return
                tipo_envio = "ZIP"
            
            file = discord.File(arquivo_para_enviar)
            
            embed = discord.Embed(
                title=f"✅ Áudio Baixado!",
                description=f"**{title}**\n🎵 Tipo: `{tipo_envio}` | 💾 Tamanho: `{formatar_tamanho(tamanho)}`\n🔗 Provedor: `{provider}`",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Solicitado por {message.author.display_name}")
            
            await message.remove_reaction("⏳", self.bot.user)
            try:
                await message.author.send(embed=embed, file=file)
            except discord.Forbidden:
                await message.reply(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Erro no auto-download: {e}")
            try:
                await message.remove_reaction("⏳", self.bot.user)
                await message.add_reaction("❌")
            except:
                pass
        finally:
            if file_path and os.path.exists(file_path):
                self.zip_handler.limpar_arquivo(file_path)
            if arquivo_para_enviar and arquivo_para_enviar != file_path and os.path.exists(arquivo_para_enviar):
                self.zip_handler.limpar_arquivo(arquivo_para_enviar)
            
            self.processando.discard(message.author.id)


async def setup(bot):
    await bot.add_cog(AutoDownload(bot))

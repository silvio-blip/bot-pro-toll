import yt_dlp
import os
import time
import logging
import subprocess
from typing import Optional, Tuple
from .config import get_downloads_folder, MAX_DISCORD_SIZE

logger = logging.getLogger("VideoHandler")

class VideoDownloader:
    def __init__(self):
        self.downloads_folder = get_downloads_folder()
    
    def _is_tiktok(self, url: str) -> bool:
        return 'tiktok.com' in url.lower()
    
    def _get_audio_options(self, output_template: str) -> dict:
        """Opções para baixar apenas áudio - versão simplificada."""
        return {
            'cookiefile': 'cookies.txt',
            'format': 'bestaudio/best',
            'outtmpl': output_template.replace('.%(ext)s', '.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'retries': 5,
            'fragment_retries': 5,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            }
        }
    
    def download(self, url: str, user_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Baixa apenas o áudio do vídeo.
        """
        timestamp = int(time.time())
        output_template = os.path.join(self.downloads_folder, f"dl_{user_id}_{timestamp}.%(ext)s")
        
        ydl_opts = self._get_audio_options(output_template)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    return None, None, None
                
                file_path = ydl.prepare_filename(info)
                
                title = info.get('title', 'Áudio')
                extractor = info.get('extractor_key', 'Desconhecido')
                
                if not file_path.endswith('.mp3'):
                    base = os.path.splitext(file_path)[0]
                    mp3_path = base + ".mp3"
                    if os.path.exists(mp3_path):
                        file_path = mp3_path
                
                logger.info(f"Download de áudio concluído: {title} ({extractor}) - {file_path}")
                
                return file_path, title, extractor
                
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Erro de download: {e}")
            return None, None, None
        except Exception as e:
            logger.error(f"Erro inesperado no handler: {e}")
            return None, None, None
    
    def verificar_tamanho(self, file_path: str) -> int:
        if os.path.exists(file_path):
            return os.path.getsize(file_path)
        return 0
    
    def precisa_compactar(self, file_path: str) -> bool:
        tamanho = self.verificar_tamanho(file_path)
        return tamanho > MAX_DISCORD_SIZE

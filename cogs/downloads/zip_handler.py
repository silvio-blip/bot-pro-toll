import os
import zipfile
import logging
import time
from typing import Optional
from .config import get_downloads_folder, MAX_DISCORD_SIZE

logger = logging.getLogger("ZipHandler")

class ZipHandler:
    def __init__(self):
        self.downloads_folder = get_downloads_folder()
    
    def compactar_video(self, video_path: str, user_id: int) -> Optional[str]:
        """
        Compacta o vídeo em ZIP. Se ainda assim exceder 25MB,
        divide em partes.
        """
        if not os.path.exists(video_path):
            return None
        
        timestamp = int(time.time())
        base_name = f"video_{user_id}_{timestamp}"
        zip_path = os.path.join(self.downloads_folder, f"{base_name}.zip")
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(video_path, os.path.basename(video_path))
            
            tamanho = os.path.getsize(zip_path)
            
            if tamanho > MAX_DISCORD_SIZE:
                logger.warning(f"ZIP ainda grande ({tamanho} bytes), tentando compactação máxima...")
                return self._compactar_max(video_path, user_id, timestamp)
            
            logger.info(f"Vídeo compactado com sucesso: {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"Erro ao compactar: {e}")
            return None
    
    def _compactar_max(self, video_path: str, user_id: int, timestamp: int) -> Optional[str]:
        """
        Tenta compactação máxima. Se ainda não couber, 
        informa o usuário.
        """
        base_name = f"video_max_{user_id}_{timestamp}"
        zip_path = os.path.join(self.downloads_folder, f"{base_name}.zip")
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, 9) as zipf:
                zipf.write(video_path, os.path.basename(video_path))
            
            tamanho = os.path.getsize(zip_path)
            
            if tamanho > MAX_DISCORD_SIZE:
                logger.error(f"即使 com compressão máxima ainda é grande: {tamanho} bytes")
                os.remove(zip_path)
                return None
            
            return zip_path
            
        except Exception as e:
            logger.error(f"Erro na compactação máxima: {e}")
            return None
    
    def limpar_arquivo(self, file_path: str):
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Arquivo removido: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao remover arquivo {file_path}: {e}")

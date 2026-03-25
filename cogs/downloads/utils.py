import re
from typing import Optional
from .config import SITES_SUPORTADOS

def extrair_url(texto: str) -> Optional[str]:
    regex = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
    match = re.search(regex, texto)
    return match.group(1) if match else None

def validar_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    return any(site in url_lower for site in SITES_SUPORTADOS)

def formatar_tamanho(tamanho_bytes: int) -> str:
    for unidade in ['B', 'KB', 'MB', 'GB']:
        if tamanho_bytes < 1024.0:
            return f"{tamanho_bytes:.2f} {unidade}"
        tamanho_bytes /= 1024.0
    return f"{tamanho_bytes:.2f} TB"

def get_extensao_padrao():
    return "mp4"

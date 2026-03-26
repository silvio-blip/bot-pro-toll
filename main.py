
import discord
from discord.ext import commands
import os
import sys
sys.path.append('/home/user/Bot_tool/.pip_packages')
from supabase import create_client, Client
import logging
import asyncio
from typing import Dict, Any, Callable, Optional

# --- Configurar LD_LIBRARY_PATH para Opus ---
import glob

def find_opus_lib():
    """Procura a biblioteca opus nos caminhos comuns"""
    # Primeiro verifica caminhos do sistema (Railway)
    system_paths = ['/usr/lib', '/usr/local/lib']
    for sp in system_paths:
        if os.path.exists(f"{sp}/libopus.so"):
            return sp
    
    # Depois Nix
    nix_paths = glob.glob("/nix/store/*-libopus-*/lib")
    for path in nix_paths:
        if os.path.exists(path):
            return path
    return None

opus_path = find_opus_lib()
if opus_path:
    os.environ['LD_LIBRARY_PATH'] = f"{opus_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    print(f"[INFO] Opus library path: {opus_path}")

# Railway deployment - check if we're on Railway
RAILWAY_ENV = os.environ.get('RAILWAY_ENVIRONMENT', False)

# --- Configuração do Logging ---
# Filter para remover logs HTTP do Supabase e rate limiting
class QuietFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if 'HTTP Request:' in msg:
            return False
        if 'rate limited' in msg.lower():
            return False
        return True

# Configurar logging mais limpo
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remover handlers existentes
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

# Criar handler customizado com filtro
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
handler.addFilter(QuietFilter())
root_logger.addHandler(handler)

# Reduzir verbosidade de bibliotecas
logging.getLogger('discord.http').setLevel(logging.ERROR)
logging.getLogger('discord.client').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)

# --- Carregamento das Variáveis de Ambiente ---
try:
    # Primeiro, verifica se as variáveis já estão no ambiente (Railway/Vercel)
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    # Se não estiverem, tenta carregar do arquivo token.env (desenvolvimento local)
    if not all([DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
        logging.info("Variáveis de ambiente não encontradas. Tentando carregar do arquivo token.env...")
        
        if os.path.exists("token.env"):
            with open("token.env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('\'"')
                        os.environ[key.strip()] = value
            
            DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
            SUPABASE_URL = os.getenv("SUPABASE_URL")
            SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        else:
            raise FileNotFoundError("Arquivo 'token.env' não encontrado e variáveis de ambiente não definidas.")

    if not all([DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
        raise ValueError("Uma ou mais variáveis de ambiente essenciais (DISCORD_TOKEN, SUPABASE_URL, SUPABASE_KEY) não foram encontradas.")

except Exception as e:
    logging.error(f"Erro crítico ao carregar o ambiente: {e}")
    exit()

# --- Inicialização e Verificação do Supabase ---
try:
    logging.info("Tentando conectar ao Supabase...")
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase_client.table('gamification_profiles').select('user_id').limit(1).execute()
    logging.info("[✅] Conexão com o Supabase e tabela de gamificação verificadas com sucesso.")
except Exception as e:
    logging.error(f"[❌] Falha ao inicializar ou conectar com o Supabase. Verifique a tabela 'gamification_profiles'. Erro: {e}")
    exit()

# --- Intents do Discord ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# --- Configuração do Bot Discord ---
class MyBot(commands.Bot):
    def __init__(self, supabase_client: Client):
        super().__init__(command_prefix='!', intents=intents)
        self.supabase_client = supabase_client
        self.db_lock = asyncio.Lock()
        self.initial_cogs = [
            'cogs.ajuda', 
            'cogs.admin',
            'cogs.gerenciamento',
            'cogs.painel_controle',
            'cogs.social_diversao.dice_command',
            'cogs.social_diversao.poll_command',
            'cogs.social_diversao.eventos',
            'cogs.administracao.autorole',
            'cogs.suporte.hub_support',
            'cogs.gamificacao.xp_system',
            'cogs.gamificacao.rank_command',
            'cogs.gamificacao.rank_geral',
            'cogs.gamificacao.gerenciar_xp',
            'cogs.gamificacao.gerenciar_moedas',
            'cogs.gamificacao.daily_command',
            'cogs.gamificacao.transfer_xp',
            'cogs.analise',
            'cogs.moderacao.warns',
            'cogs.moderacao.captcha',
            'cogs.moderacao.antiraid',
            'cogs.moderacao.filtros',
            'cogs.moderacao.logs',
            'cogs.moderacao.lock',
            'cogs.moderacao.limpar',
            'cogs.moderacao.account_age',
            'cogs.loja.shop_manager',
            'cogs.loja.shop_user',
            'cogs.loja.inventario_command',
            'cogs.utilidades',  # Temporariamente desativado - requer libstdc++6
            'cogs.embed_command',
            'cogs.ia.agent_ia',
            'cogs.downloads.download_command',
            'cogs.downloads.auto_download'
        ]

    async def update_xp(self, user: discord.Member, guild: discord.Guild, xp_change: int, is_message: bool = False) -> Optional[int]:
        async with self.db_lock:
            try:
                config_response = self.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild.id).execute()
                settings = config_response.data[0]['settings'] if config_response.data else {}
                xp_settings = settings.get('gamification_xp', {})
                
                xp_per_level_base = int(xp_settings.get('xp_per_level_base', 300))
                if xp_per_level_base <= 0: xp_per_level_base = 300

                profile_response = self.supabase_client.table("gamification_profiles").select("user_id", "xp", "level", "message_count").eq("user_id", user.id).eq("guild_id", guild.id).execute()
                profile_data = profile_response.data[0] if profile_response.data else {}
                
                current_xp = profile_data.get('xp', 0)
                current_level = profile_data.get('level', 0)
                current_messages = profile_data.get('message_count', 0)

                new_xp = max(0, current_xp + xp_change)
                new_messages = current_messages + 1 if is_message else current_messages
                new_level = int(new_xp / xp_per_level_base)

                self.supabase_client.table("gamification_profiles").upsert({
                    "user_id": user.id,
                    "guild_id": guild.id,
                    "user_name": user.display_name,
                    "xp": new_xp,
                    "level": new_level,
                    "message_count": new_messages
                }).execute()

                if new_level > current_level:
                    logging.info(f"[LEVEL UP] {user.name} alcançou o nível {new_level} em {guild.name}! XP: {new_xp}")
                    return new_level
                
                return None
            except Exception as e:
                logging.error(f"Erro CRÍTICO na função central update_xp para {user.name}: {e}")
                return None

    async def get_and_update_server_settings(self, guild_id: int, update_func: Callable[[Dict[str, Any]], None]) -> bool:
        async with self.db_lock:
            try:
                response = self.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
                settings = response.data[0]['settings'] if response.data else {}
                
                update_func(settings)

                self.supabase_client.table("server_configurations").upsert({
                    "server_guild_id": guild_id, 
                    "settings": settings
                }, on_conflict="server_guild_id").execute()
                return True
            except Exception as e:
                logging.error(f"Erro ao atualizar as configurações do servidor {guild_id}: {e}")
                return False

    async def setup_hook(self):
        logging.info('--- Carregando Cogs ---')
        for cog in self.initial_cogs:
            try:
                await self.load_extension(cog)
                emoji = self.get_cog_emoji(cog)
                logging.info(f"[{emoji}] Cog '{cog}' carregado com sucesso.")
            except Exception as e:
                logging.error(f"[❌] Falha ao carregar o cog '{cog}': {e}")
        logging.info('------------------------')
        logging.info('Sincronizando comandos com o Discord...')
        await self.tree.sync()
        logging.info('[✅] Comandos sincronizados.')

    def get_cog_emoji(self, cog_name: str) -> str:
        emoji_map = {
            'cogs.ajuda': '❓', 
            'cogs.admin': '🔑',
            'cogs.gerenciamento': '⚙️',
            'cogs.painel_controle': '🎛️',
            'cogs.social_diversao.dice_command': '🎲',
            'cogs.social_diversao.poll_command': '📋',
            'cogs.social_diversao.eventos': '🎪',
            'cogs.administracao.autorole': '👤',
            'cogs.suporte.hub_support': '🎧',
            'cogs.gamificacao.xp_system': '⭐',
            'cogs.gamificacao.rank_command': '🥇',
            'cogs.gamificacao.rank_geral': '🌟',
            'cogs.gamificacao.gerenciar_xp': '💎',
            'cogs.gamificacao.gerenciar_moedas': '💰',
            'cogs.gamificacao.daily_command': '🎁',
            'cogs.gamificacao.transfer_xp': '🔄',
            'cogs.analise': '📊',
            'cogs.moderacao.warns': '⚠️',
            'cogs.moderacao.captcha': '🔐',
            'cogs.moderacao.antiraid': '🛡️',
            'cogs.moderacao.filtros': '🧹',
            'cogs.moderacao.logs': '📝',
            'cogs.moderacao.lock': '🔐',
            'cogs.moderacao.limpar': '🧹',
            'cogs.moderacao.account_age': '📅',
            'cogs.loja.shop_manager': '🛒',
            'cogs.loja.shop_user': '🛍️',
            'cogs.loja.inventario_command': '🎒',
            'cogs.utilidades': '🛠️',
            'cogs.embed_command': '📨',
            'cogs.ia.agent_ia': '🧠',
            'cogs.downloads.download_command': '⬇️',
            'cogs.downloads.auto_download': '📥'
        }
        return emoji_map.get(cog_name, '📦')

    async def on_ready(self):
        logging.info('--- Bot Conectado ---')
        logging.info(f'Nome: {self.user.name}')
        logging.info(f'ID: {self.user.id}')
        logging.info('✅ conectado')

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    bot = MyBot(supabase_client)
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure as e:
        logging.error(f"[❌] Falha no login: {e}. Verifique o seu DISCORD_TOKEN.")
    except Exception as e:
        logging.error(f"[❌] Ocorreu um erro inesperado ao tentar iniciar o bot: {e}")

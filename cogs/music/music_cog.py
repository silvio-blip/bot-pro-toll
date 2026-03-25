# -*- coding: utf-8 -*-
# Sistema de Música - Player de Música para Discord
# Comandos: /tocar, /pausar, /continuar, /pular, /parar, /fila, /volume, /tocando, /misturar

import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, ButtonStyle
from discord import FFmpegPCMAudio
from datetime import datetime, timezone
import asyncio
import logging
from typing import Optional, List, Dict
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("MusicCog")

# Reduzir logs verbose
logging.getLogger('discord.http').setLevel(logging.ERROR)


# --- Armazenamento em memória (temporário, depois migrar para DB) ---
class MusicState:
    def __init__(self):
        self.sessions: Dict[int, dict] = {}  # guild_id -> session data
        self.queues: Dict[int, List[dict]] = {}  # guild_id -> queue
        self.players: Dict[int, dict] = {}  # guild_id -> player data
        
music_state = MusicState()


# --- Funções Auxiliares ---
async def get_music_config(bot, guild_id: int) -> dict:
    """Busca configuração de música do servidor"""
    try:
        response = bot.supabase_client.table("music_config").select("*").eq("server_guild_id", guild_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Erro ao buscar config de música: {e}")
    return {}


async def get_or_create_session(bot, guild_id: int) -> dict:
    """Busca ou cria sessão de música"""
    try:
        response = bot.supabase_client.table("music_session").select("*").eq("server_guild_id", guild_id).execute()
        if response.data:
            return response.data[0]
    except:
        pass
    return {}


async def update_music_session(bot, guild_id: int, data: dict):
    """Atualiza sessão de música no banco"""
    try:
        existing = bot.supabase_client.table("music_session").select("id").eq("server_guild_id", guild_id).execute()
        if existing.data:
            bot.supabase_client.table("music_session").update({
                **data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("server_guild_id", guild_id).execute()
        else:
            bot.supabase_client.table("music_session").insert({
                "server_guild_id": guild_id,
                **data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()
    except Exception as e:
        logger.error(f"Erro ao atualizar sessão: {e}")


async def verificar_canal_autorizado(bot, interaction: Interaction) -> bool:
    """Verifica se o comando foi usado no canal autorizado"""
    config = await get_music_config(bot, interaction.guild.id)
    
    if not config:
        return True  # Se não tiver config, permite em qualquer lugar
    
    if not config.get('enabled', True):
        await interaction.followup.send("❌ O sistema de música está desabilitado neste servidor.", ephemeral=True)
        return False
    
    if config.get('channel_text_id'):
        canal_autorizado_id = int(config['channel_text_id'])
        if interaction.channel.id != canal_autorizado_id:
            canal = interaction.guild.get_channel(canal_autorizado_id)
            nome_canal = canal.mention if canal else f"#{config['channel_text_id']}"
            await interaction.followup.send(
                f"❌ Comandos de música só funcionam no canal {nome_canal}",
                ephemeral=True
            )
            return False
    
    return True


async def verificar_usuario_em_canal(interaction: Interaction) -> bool:
    """Verifica se o usuário está em um canal de voz"""
    if not interaction.user.voice:
        await interaction.followup.send(
            "❌ Você precisa estar em um canal de voz para usar este comando.",
            ephemeral=True
        )
        return False
    return True


async def verificar_mesmo_canal(interaction: Interaction, guild_id: int) -> bool:
    """Verifica se o usuário está no mesmo canal de voz que o bot"""
    session = await get_or_create_session(interaction.client, guild_id)
    
    if not session or not session.get('channel_voice_id'):
        return True  # Bot não está conectado
    
    # Buscar canal de voz do bot
    bot_voice = interaction.guild.voice_client
    if not bot_voice or not bot_voice.channel:
        return True
    
    user_channel = interaction.user.voice.channel
    bot_channel = bot_voice.channel
    
    if user_channel.id != bot_channel.id:
        await interaction.followup.send(
            f"❌ Você precisa estar no mesmo canal de voz que o bot ({bot_channel.mention}) para usar este comando.",
            ephemeral=True
        )
        return False
    
    return True


async def get_current_controller(bot, guild_id: int) -> Optional[discord.Member]:
    """Retorna o usuário que está controlando o bot"""
    session = await get_or_create_session(bot, guild_id)
    if not session or not session.get('current_controller_id'):
        return None
    
    guild = bot.get_guild(guild_id)
    if not guild:
        return None
    
    try:
        member = await guild.fetch_member(session['current_controller_id'])
        return member
    except:
        return None


async def update_controller(bot, interaction: Interaction, new_controller: Optional[discord.Member] = None):
    """Atualiza quem está controlando o bot"""
    guild_id = interaction.guild.id
    
    if new_controller is None:
        # Tentar transferir para outro usuário no canal
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.channel:
            members = [m for m in voice_client.channel.members if not m.bot]
            if members:
                new_controller = members[0]
            else:
                # Ninguém no canal, desconectar
                await desconectar_bot(bot, interaction.guild)
                return
    
    controller_name = new_controller.display_name if new_controller else None
    controller_id = new_controller.id if new_controller else None
    
    await update_music_session(bot, guild_id, {
        "current_controller_id": controller_id,
        "current_controller_name": controller_name,
        "last_activity": datetime.now(timezone.utc).isoformat()
    })
    
    # Enviar mensagem no canal de controle
    config = await get_music_config(bot, guild_id)
    if config and config.get('channel_text_id'):
        channel = interaction.guild.get_channel(int(config['channel_text_id']))
        if channel:
            if new_controller:
                await channel.send(f"🔄 Controle transferido para: {new_controller.mention}")
            else:
                await channel.send("👋 Todos saíram. Desconectando...")


async def desconectar_bot(bot, guild):
    """Desconecta o bot do canal de voz"""
    guild_id = guild.id
    
    if guild.voice_client:
        await guild.voice_client.disconnect()
    
    # Limpar sessão
    try:
        bot.supabase_client.table("music_session").delete().eq("server_guild_id", guild_id).execute()
        bot.supabase_client.table("music_queue").delete().eq("server_guild_id", guild_id).execute()
    except:
        pass
    
    # Notificar
    config = await get_music_config(bot, guild_id)
    if config and config.get('channel_text_id'):
        channel = guild.get_channel(int(config['channel_text_id']))
        if channel:
            await channel.send("👋 Todos saíram. Bot desconectado.")


# --- Função para buscar música com yt-dlp (múltiplas fontes) ---
import yt_dlp

async def buscar_musica(query: str) -> Optional[dict]:
    """Busca música de múltiplas fontes: YouTube, SoundCloud, Spotify, Bandcamp, etc."""
    try:
        # Verificar se é uma URL direta
        is_url = query.startswith('http://') or query.startswith('https://')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'extractor_retries': 3,
            'fragment_retries': 3,
            'skip_unavailable_fragments': False,
        }
        
        # Tenta usar cookies se existir
        import os
        cookies_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cookies.txt')
        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
        
        # Tenta múltiplas fontes
        sources_to_try = []
        
        if is_url:
            sources_to_try.append(query)
        else:
            # Busca em várias fontes
            sources_to_try = [
                f"ytsearch3:{query}",  # YouTube
                f"soundcloudsearch:{query}",  # SoundCloud
                f"bandcampsearch:{query}",  # Bandcamp
                f"youtubesearch:{query}",  # YouTube alternativo
            ]
        
        last_error = None
        for source in sources_to_try:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    if source.startswith("http"):
                        info = ydl.extract_info(source, download=False)
                    else:
                        info = ydl.extract_info(source, download=False)
                    
                    if info:
                        break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[MUSIC] Fonte falhou ({source}): {e}")
                continue
        
        if not info:
            
            if not info:
                return None
            
            # Se for uma busca, pega o primeiro resultado
            if 'entries' in info:
                info = info['entries'][0]
            
            # Pega o URL de áudio diretamente
            audio_url = info.get('url')
            if not audio_url:
                # Tenta获取formats
                formats = info.get('formats', [])
                for f in formats:
                    if f.get('ext') in ['m4a', 'webm', 'mp4'] and f.get('url'):
                        audio_url = f['url']
                        break
            
            return {
                "title": info.get('title', 'Unknown'),
                "url": audio_url or info.get('webpage_url'),
                "duration": info.get('duration', 180),
                "thumbnail": info.get('thumbnail'),
                "source": info.get('extractor', 'unknown')
            }
    except Exception as e:
        logger.error(f"[MUSIC] Erro ao buscar música: {e}")
        return None


# --- comandos de música ---
class MusicCommands:
    """Comandos do sistema de música"""
    
    @app_commands.command(name="tocar", description="Toca uma música no canal de voz")
    @app_commands.describe(música="Nome ou URL da música para tocar")
    async def tocar(self, interaction: Interaction, música: str):
        """Comando /tocar - conecta e toca música"""
        await interaction.response.defer(ephemeral=True)
        
        # 1. Verificar canal autorizado
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        # 2. Verificar se usuário está em canal de voz
        if not await verificar_usuario_em_canal(interaction):
            return
        
        guild_id = interaction.guild.id
        user_channel = interaction.user.voice.channel
        
        # 3. Buscar música
        try:
            musica = await buscar_musica(música)
            if not musica:
                await interaction.followup.send("❌ Música não encontrada.", ephemeral=True)
                return
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao buscar música: {str(e)[:100]}", ephemeral=True)
            return
        
        # 4. Conectar ao canal se não estiver conectado
        voice_client = interaction.guild.voice_client
        if not voice_client:
            try:
                logger.info(f"[MUSIC] Tentando conectar ao canal: {user_channel.name} (ID: {user_channel.id})")
                voice_client = await asyncio.wait_for(
                    user_channel.connect(),
                    timeout=30.0
                )
                logger.info(f"[MUSIC] Conectado com sucesso ao canal: {user_channel.name}")
                voice_client = interaction.guild.voice_client
            except asyncio.TimeoutError:
                logger.error(f"[MUSIC] Timeout ao conectar ao canal de voz")
                await interaction.followup.send("❌ Timeout ao conectar no canal de voz. O ambiente pode estar bloqueando conexões UDP.", ephemeral=True)
                return
            except Exception as e:
                logger.error(f"[MUSIC] Erro ao conectar: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[MUSIC] Traceback: {traceback.format_exc()}")
                await interaction.followup.send(f"❌ Erro ao conectar no canal: {type(e).__name__}: {str(e)[:200]}", ephemeral=True)
                return
        
        # 5. Reproduzir música
        try:
            logger.info(f"[MUSIC] Tentando reproduzir: {musica.get('url')}")
            source = FFmpegPCMAudio(musica.get('url'))
            voice_client.play(source)
            logger.info(f"[MUSIC] Música iniciada: {musica.get('title')}")
        except Exception as e:
            logger.error(f"[MUSIC] Erro ao reproduzir: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[MUSIC] Traceback: {traceback.format_exc()}")
        
        # 6. Atualizar sessão no banco
        await update_music_session(self.bot, guild_id, {
            "channel_voice_id": user_channel.id,
            "current_controller_id": interaction.user.id,
            "current_controller_name": interaction.user.display_name,
            "is_playing": True,
            "current_song_title": musica.get('title'),
            "current_song_url": musica.get('url'),
            "current_song_duration": musica.get('duration'),
            "last_activity": datetime.now(timezone.utc).isoformat()
        })
        
        # 6. Enviar confirmação
        embed = discord.Embed(
            title="🎵 Música adicionada à fila",
            description=f"**{musica.get('title')}**",
            color=discord.Color.green()
        )
        
        if musica.get('duration'):
            minutos = musica['duration'] // 60
            segundos = musica['duration'] % 60
            embed.add_field(name="Duração", value=f"{minutos}:{segundos:02d}", inline=True)
        
        if musica.get('source'):
            embed.add_field(name="Fonte", value=musica['source'].title(), inline=True)
        
        embed.add_field(name="Canal", value=user_channel.mention, inline=True)
        embed.add_field(name="Controlado por", value=interaction.user.mention, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # 7. Notificar no canal de controle
        config = await get_music_config(self.bot, guild_id)
        if config and config.get('channel_text_id'):
            channel = interaction.guild.get_channel(int(config['channel_text_id']))
            if channel and channel.id != interaction.channel.id:
                await channel.send(
                    f"🎵 **Tocando:** {musica.get('title')}\n"
                    f"▶️ **Controlado por:** {interaction.user.mention}\n"
                    f"📍 **Canal:** {user_channel.mention}"
                )

    @app_commands.command(name="pausar", description="Pausa a música atual")
    async def pausar(self, interaction: Interaction):
        """Comando /pausar - pausa a reprodução"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        if not await verificar_usuario_em_canal(interaction):
            return
        
        if not await verificar_mesmo_canal(interaction, interaction.guild.id):
            return
        
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.followup.send("❌ Não há música tocando.", ephemeral=True)
            return
        
        voice_client.pause()
        
        await update_music_session(self.bot, interaction.guild.id, {
            "is_playing": False,
            "last_activity": datetime.now(timezone.utc).isoformat()
        })
        
        await interaction.followup.send("⏸️ Música pausada.", ephemeral=True)

    @app_commands.command(name="continuar", description="Continua a música pausada")
    async def continuar(self, interaction: Interaction):
        """Comando /continuar - continua a reprodução"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        if not await verificar_usuario_em_canal(interaction):
            return
        
        if not await verificar_mesmo_canal(interaction, interaction.guild.id):
            return
        
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_paused():
            await interaction.followup.send("❌ A música não está pausada.", ephemeral=True)
            return
        
        voice_client.resume()
        
        await update_music_session(self.bot, interaction.guild.id, {
            "is_playing": True,
            "last_activity": datetime.now(timezone.utc).isoformat()
        })
        
        await interaction.followup.send("▶️ Música continuada.", ephemeral=True)

    @app_commands.command(name="pular", description="Pula para a próxima música")
    async def pular(self, interaction: Interaction):
        """Comando /pular - pula para próxima música"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        if not await verificar_usuario_em_canal(interaction):
            return
        
        if not await verificar_mesmo_canal(interaction, interaction.guild.id):
            return
        
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.followup.send("❌ Bot não está conectado.", ephemeral=True)
            return
        
        # Aqui você implementaria a lógica de pular para próxima na fila
        # Por enquanto, apenas para a música atual
        if voice_client.is_playing():
            voice_client.stop()
        
        await interaction.followup.send("⏭️ Música pulada.", ephemeral=True)

    @app_commands.command(name="parar", description="Para a música e desconecta o bot")
    async def parar(self, interaction: Interaction):
        """Comando /parar - para e desconecta"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        if not await verificar_usuario_em_canal(interaction):
            return
        
        voice_client = interaction.guild.voice_client
        if voice_client:
            voice_client.stop()
            await desconectar_bot(self.bot, interaction.guild)
        
        await interaction.followup.send("⏹️ Música parada e bot desconectado.", ephemeral=True)

    @app_commands.command(name="fila", description="Mostra a fila de músicas")
    async def fila(self, interaction: Interaction):
        """Comando /fila - mostra a fila"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        # Buscar fila do banco
        try:
            response = self.bot.supabase_client.table("music_queue").select("*").eq("server_guild_id", interaction.guild.id).order("position").execute()
            queue = response.data if response.data else []
        except:
            queue = []
        
        if not queue:
            await interaction.followup.send("📋 A fila está vazia.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Fila de Músicas",
            color=discord.Color.blurple()
        )
        
        for i, song in enumerate(queue[:10], 1):
            embed.add_field(
                name=f"{i}. {song.get('title', 'Desconhecido')[:50]}",
                value=f"Adicionado por: {song.get('added_by_name', 'Desconhecido')}",
                inline=False
            )
        
        if len(queue) > 10:
            embed.set_footer(text=f"Total: {len(queue)} músicas na fila")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="volume", description="Ajusta o volume (0-100)")
    @app_commands.describe(volume="Volume de 0 a 100")
    async def volume(self, interaction: Interaction, volume: int):
        """Comando /volume - ajusta o volume"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        volume = max(0, min(100, volume))
        
        await update_music_session(self.bot, interaction.guild.id, {
            "volume": volume,
            "last_activity": datetime.now(timezone.utc).isoformat()
        })
        
        await interaction.followup.send(f"🔊 Volume ajustado para {volume}%.)", ephemeral=True)

    @app_commands.command(name="tocando", description="Mostra a música atual")
    async def tocando(self, interaction: Interaction):
        """Comando /tocando - mostra música atual"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        session = await get_or_create_session(self.bot, interaction.guild.id)
        
        if not session or not session.get('current_song_title'):
            await interaction.followup.send("❌ Nenhuma música tocando.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎵 Tocando Agora",
            description=f"**{session.get('current_song_title')}**",
            color=discord.Color.green()
        )
        
        if session.get('current_song_url'):
            embed.add_field(name="URL", value=session.get('current_song_url')[:50], inline=False)
        
        if session.get('current_controller_name'):
            embed.add_field(name="Controlado por", value=session.get('current_controller_name'), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="misturar", description="Mistura a fila de músicas")
    async def misturar(self, interaction: Interaction):
        """Comando /misturar - mistura a fila"""
        await interaction.response.defer(ephemeral=True)
        
        if not await verificar_canal_autorizado(self.bot, interaction):
            return
        
        if not await verificar_usuario_em_canal(interaction):
            return
        
        if not await verificar_mesmo_canal(interaction, interaction.guild.id):
            return
        
        # Buscar fila
        try:
            response = self.bot.supabase_client.table("music_queue").select("*").eq("server_guild_id", interaction.guild.id).execute()
            queue = response.data if response.data else []
        except:
            queue = []
        
        if len(queue) < 2:
            await interaction.followup.send("❌ precisa de pelo menos 2 músicas na fila para misturar.", ephemeral=True)
            return
        
        random.shuffle(queue)
        
        # Atualizar posições
        for i, song in enumerate(queue, 1):
            try:
                self.bot.supabase_client.table("music_queue").update({"position": i}).eq("id", song['id']).execute()
            except:
                pass
        
        await interaction.followup.send("🔀 Fila misturada!", ephemeral=True)


# --- COG Principal ---
class Musica(commands.Cog, MusicCommands):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sync_commands()
        logger.info("[✅] Cog 'musica' carregado.")
    
    def _sync_commands(self):
        """Sincroniza os comandos após a criação da classe"""
        pass

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("[✅] Sistema de música inicializado")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Detecta quando alguém sai do canal de voz"""
        if member.bot:
            return
        
        if before.channel and after.channel != before.channel:
            guild = member.guild
            if not guild.voice_client:
                return
            
            session = await get_or_create_session(self.bot, guild.id)
            if not session or session.get('current_controller_id') != member.id:
                return
            
            # O controlador saiu, transferir ou desconectar
            voice_channel = guild.voice_client.channel
            outros_membros = [m for m in voice_channel.members if not m.bot and m.id != member.id]
            
            if outros_membros:
                await update_controller(self.bot, await self.bot.get_context(await self.bot.get_channel(after.channel.id).send("dummy")), outros_membros[0])
            else:
                await desconectar_bot(self.bot, guild)


class MusicConfigModal(ui.Modal, title="Config. Música"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        
        self.add_item(ui.TextInput(
            label="Canal de texto (ID)",
            placeholder="ID do canal onde comandos funcionam",
            default=str(self.config.get("channel_text_id", "")),
            required=False
        ))
        
        self.add_item(ui.TextInput(
            label="Cargo autorizado (ID)",
            placeholder="ID do cargo que pode usar comandos",
            default=str(self.config.get("role_id", "")),
            required=False
        ))
        
        self.add_item(ui.TextInput(
            label="Volume padrão (0-100)",
            placeholder="Volume padrão ao iniciar",
            default=str(self.config.get("volume_default", 50)),
            required=False
        ))
        
        self.add_item(ui.TextInput(
            label="Auto-desconectar (minutos)",
            placeholder="Minutos de inatividade para desconectar",
            default=str(self.config.get("auto_disconnect_minutes", 30)),
            required=False
        ))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            channel_text_id = int(self.children[0].value.strip()) if self.children[0].value.strip().isdigit() else None
            role_id = int(self.children[1].value.strip()) if self.children[1].value.strip().isdigit() else None
            volume_default = int(self.children[2].value.strip()) if self.children[2].value.strip().isdigit() else 50
            auto_disconnect = int(self.children[3].value.strip()) if self.children[3].value.strip().isdigit() else 30
            
            volume_default = max(0, min(100, volume_default))
            auto_disconnect = max(1, min(120, auto_disconnect))
            
            try:
                self.bot.supabase_client.table("music_config").upsert({
                    "server_guild_id": interaction.guild.id,
                    "channel_text_id": channel_text_id,
                    "role_id": role_id,
                    "volume_default": volume_default,
                    "auto_disconnect_minutes": auto_disconnect,
                    "enabled": True
                }, on_conflict="server_guild_id").execute()
                
                await interaction.followup.send("✅ Configurações de música salvas com sucesso!", ephemeral=True)
            except Exception as e:
                logger.error(f"Erro ao salvar config de música: {e}")
                await interaction.followup.send(f"❌ Erro ao salvar: {e}", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao processar config de música: {e}")
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Musica(bot))
    logger.info("[✅] Cog 'musica' configurado com sucesso.")
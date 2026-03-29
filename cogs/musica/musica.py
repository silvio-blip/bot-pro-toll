import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import logging

logger = logging.getLogger("MusicaCog")

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'source_address': '0.0.0.0',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

PLATFORMS = [
    ('scsearch', 'SoundCloud'),
]


async def get_music_config(bot, guild_id: int) -> dict:
    try:
        if not hasattr(bot, 'supabase_client'):
            return {}
        response = bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
        if response.data:
            all_settings = response.data[0].get('settings', {})
            return all_settings.get('music', {})
    except Exception as e:
        logger.error(f"Erro ao buscar config de música para {guild_id}: {e}")
    return {}


def is_dj(member, guild, bot):
    if not guild:
        return False
    
    async def get_config():
        return await get_music_config(bot, guild.id)
    
    config = asyncio.run(get_config()) if asyncio.iscoroutinefunction(get_config) is False else None
    
    loop = asyncio.get_event_loop()
    config = loop.run_until_complete(get_music_config(bot, guild.id))
    
    dj_role_id = config.get('dj_role_id')
    
    if dj_role_id:
        role = guild.get_role(dj_role_id)
        if role and role in member.roles:
            return True
    
    current_dj_id = bot.current_dj.get(guild.id)
    if current_dj_id and member.id == current_dj_id:
        return True
    return False


def is_url(text):
    return text.startswith('http://') or text.startswith('https://')


def format_duration(seconds):
    if not seconds:
        return "?"
    secs = int(seconds)
    mins = secs // 60
    secs = secs % 60
    return f"{mins}:{secs:02d}"


async def search_all_platforms(busca, ydl):
    for prefix, name in PLATFORMS:
        try:
            logger.info(f"🔍 Buscando em {name}...")
            query = f"{prefix}10:{busca}"
            info = ydl.extract_info(query, download=False)
            if info and 'entries' in info and info['entries']:
                for entry in info['entries']:
                    duration = entry.get('duration', 0)
                    if duration and duration >= 50:
                        return {
                            'url': entry['url'],
                            'title': entry.get('title', 'Música'),
                            'extractor': entry.get('extractor_key', name),
                            'thumbnail': entry.get('thumbnail', ''),
                            'duration': duration,
                        }
        except Exception as e:
            logger.error(f"❌ Erro em {name}: {str(e)[:50]}")
            continue
    return None


class MusicaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("[✅] Cog 'musica' carregado.")

    def get_queue(self, guild_id):
        if guild_id not in self.bot.queues:
            self.bot.queues[guild_id] = []
        return self.bot.queues[guild_id]

    async def play_next(self, guild: discord.Guild):
        queue = self.get_queue(guild.id)
        
        if not queue:
            if self.bot.funk_mode.get(guild.id):
                try:
                    await self.play_random_funk(guild)
                except Exception as e:
                    logger.error(f"Erro ao tocar funk automático: {e}")
                    self.bot.funk_mode.pop(guild.id, None)
                    self.bot.current.pop(guild.id, None)
            else:
                self.bot.current.pop(guild.id, None)
            return

        info = queue.pop(0)
        vc = guild.voice_client

        if not vc:
            return

        try:
            source = discord.FFmpegOpusAudio(info['url'], **FFMPEG_OPTIONS)
            self.bot.current[guild.id] = info

            def after_playing(error):
                if error:
                    logger.error(f'Erro no player: {error}')
                asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)

            vc.play(source, after=after_playing)
        except Exception as e:
            logger.error(f"Erro ao tocar: {e}")
            await self.play_next(guild)

    async def play_random_funk(self, guild: discord.Guild):
        import random
        
        funk_searches = [
            "The Box Medley MC Ryan SP",
            "Cala a Boca e Me Chupa DJ Paulo Magrão",
            "MC Pipokinha",
            "MC Poze do Rodo",
            "MC Ryan SP funk 2025",
            "MC Dricka",
            "MC Lele JP",
            "MC Flavinho",
            "MC Menor ZL",
            "MC GH funk",
            "DJ Arana",
            "MC Lan",
            "MC Rick funk",
            "MC GW",
            "MC Magrinho",
            "MC Paulin da Capital",
            "MC Livinho",
            "MC Hariel",
            "MC Pierre funk",
            "MC Davi",
            "DJ Topo",
            "DJ GBR",
            "MC Daniel funk",
            "MC Neguinho do Kaxeta",
            "MTG funk",
            "DJ Win",
            "DJ Jhow Beats",
            "DJ Claudinho Buchecha",
            "MC Rebecca",
            "DJ Vovô funk",
            "MC Luan da BS",
            "Banda Eva funk",
            "DJ WS da Igrejinha",
            "Orochi funk",
            "MC Kevin funk",
            "WIU funk",
            "Ludmilla funk",
            "MC Saci",
            "DJ Kotim",
            "DJ Dubom",
            "MC L da Vinte",
            "DJ Swat",
            "Parado no Bailão",
            "DJ Clei",
            "Slowed funk brasil",
            "Phonk brasileiro",
            "Brazilian Phonk",
            "DJ LL funk",
            "DJ Japa NK",
            "funk slowed 2025",
            "funk automotiv",
            "MC IG",
            "MC Tati Zaqui",
            "MC Hariel funk",
            "funk paredão 2025",
            "funk gospel remix",
            "DJ 2D funk",
            "MC Koruth",
            "DJ RN",
            "MC Triz",
            "funk viral tiktok",
            "funk montagem",
            "funk grave arrastado",
            "funk pesado 2025",
            "funk brasil 2025",
            "MC funk 2025",
            "DJ alk",
            "DJ g lockdowns",
            "DJ Biel",
            "funk 150 bpm",
            "funk ostentação",
            "funk prohibited",
            "funk melody",
            "funk mix",
            "MC funk pesado",
            "batidao funk",
            "brazilian bass funk",
            "funk старо модерно",
            "funk brasileiro hit",
            "funk viral",
            "funk 2024 2025",
            "MC DJ",
            "funk deukai",
            "funk r7",
            "funk radio",
            "MC PH",
            "Ludmilla",
            "Anitta funk",
            "Luísa Sonza funk",
            "Pabllo Vittar funk",
        ]
        
        busca = random.choice(funk_searches)
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(f"scsearch20:{busca}", download=False)
            if not info or 'entries' not in info:
                return
            
            valid_entries = [e for e in info['entries'] if e.get('duration', 0) and e.get('duration', 0) >= 30]
            if not valid_entries:
                return
            
            entry = random.choice(valid_entries)
            info = ydl.extract_info(entry['url'], download=False)
            
            url = info['url']
            titulo = info.get('title', 'Funk')
            extrator = info.get('extractor_key', 'SoundCloud')
            duration = info.get('duration', 0)
            
            music_info = {
                'url': url,
                'title': titulo,
                'extractor': extrator,
                'thumbnail': '',
                'duration': duration,
                'requester': 'Auto-Funk'
            }
            
            vc = guild.voice_client
            if not vc:
                return
            
            self.bot.current[guild.id] = music_info
            
            try:
                source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
                
                def after_playing(error):
                    if error:
                        logger.error(f'Erro no player: {error}')
                    asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)
                
                vc.play(source, after=after_playing)
                
                channel = vc.channel
                if channel:
                    try:
                        await channel.send(f"🎶 Tocando Funk: **{titulo}** [{format_duration(duration)}]")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Erro ao tocar funk: {e}")
                await self.play_next(guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            return
        
        guild = member.guild
        vc = guild.voice_client
        
        if vc and vc.channel:
            current_dj_id = self.bot.current_dj.get(guild.id)
            
            if current_dj_id and member.id == current_dj_id:
                new_dj = None
                for m in vc.channel.members:
                    if m.id != self.bot.user.id:
                        new_dj = m
                        break
                
                if new_dj:
                    self.bot.current_dj[guild.id] = new_dj.id
                    try:
                        await vc.channel.send(f"🎧 **{new_dj.mention}** agora está no controle!")
                    except:
                        pass
                else:
                    self.bot.current_dj.pop(guild.id, None)
            
            if len(vc.channel.members) <= 1:
                self.bot.queues[guild.id] = []
                self.bot.current.pop(guild.id, None)
                self.bot.current_dj.pop(guild.id, None)
                self.bot.funk_mode.pop(guild.id, None)
                await vc.disconnect()
                logger.info(f"👋 Desconectado do canal {vc.channel.name} (sem usuários)")

    @app_commands.command(name="play", description="Toca música de vários lugares")
    async def play(self, interaction: discord.Interaction, busca: str):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("Entre num canal de voz primeiro!")

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        
        self.bot.current_dj[interaction.guild.id] = interaction.user.id

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                if is_url(busca):
                    info = ydl.extract_info(busca, download=False)
                    if 'entries' in info:
                        info = info['entries'][0]
                    url = info['url']
                    titulo = info.get('title', 'Música')
                    extrator = info.get('extractor_key', 'Link')
                    thumbnail = info.get('thumbnail', '')
                    duration = info.get('duration', 0)
                else:
                    await interaction.followup.send("🔍 Buscando em múltiplas plataformas...")
                    result = await search_all_platforms(busca, ydl)
                    if not result:
                        return await interaction.followup.send("❌ Nenhuma música encontrada em nenhuma plataforma.")
                    url = result['url']
                    titulo = result['title']
                    extrator = result['extractor']
                    thumbnail = result['thumbnail']
                    duration = result.get('duration', 0)

                music_info = {
                    'url': url,
                    'title': titulo,
                    'extractor': extrator,
                    'thumbnail': thumbnail,
                    'duration': duration,
                    'requester': interaction.user.name
                }

                queue = self.get_queue(interaction.guild.id)
                duracao_str = format_duration(duration)

                if vc.is_playing() or vc.is_paused():
                    queue.append(music_info)
                    await interaction.followup.send(
                        f"📝 Adicionado à fila: **{titulo}** [{duracao_str}] (posição {len(queue)})"
                    )
                else:
                    source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
                    self.bot.current[interaction.guild.id] = music_info

                    def after_playing(error):
                        if error:
                            logger.error(f'Erro no player: {error}')
                        asyncio.run_coroutine_threadsafe(
                            self.play_next(interaction.guild), self.bot.loop
                        )

                    vc.play(source, after=after_playing)
                    await interaction.followup.send(
                        f"🎶 Tocando: **{titulo}** [{duracao_str}] via **{extrator}**"
                    )

            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao processar: {str(e)[:100]}")

    @app_commands.command(name="queue", description="Mostra a fila de músicas")
    async def queue_cmd(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        vc = interaction.guild.voice_client
        if not vc or not vc.channel:
            return await interaction.response.send_message("❌ Não estou em nenhum canal de voz.")
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            return await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot.")
        
        dj_role_id = config.get('dj_role_id')
        if dj_role_id:
            role = interaction.guild.get_role(dj_role_id)
            if role and role in interaction.user.roles:
                pass
            else:
                current_dj_id = self.bot.current_dj.get(interaction.guild.id)
                if not current_dj_id or interaction.user.id != current_dj_id:
                    return await interaction.response.send_message("❌ Apenas o DJ ou pessoas com cargo privilegiado podem fazer isso.")
        
        queue = self.get_queue(interaction.guild.id)
        current = self.bot.current.get(interaction.guild.id)

        embed = discord.Embed(
            title="🎵 Fila de Música",
            color=discord.Color.blue()
        )

        if current:
            duracao = format_duration(current.get('duration', 0))
            embed.add_field(
                name="▶ Tocando agora",
                value=f"**{current['title']}** [{duracao}] (por {current['requester']})",
                inline=False
            )

        if queue:
            lista = "\n".join(
                f"{i+1}. **{m['title']}** [{format_duration(m.get('duration', 0))}] (por {m['requester']})"
                for i, m in enumerate(queue[:10])
            )
            if len(queue) > 10:
                lista += f"\n... e mais {len(queue) - 10} músicas"
            embed.add_field(name="📝 Próximas", value=lista, inline=False)
        else:
            embed.add_field(name="📝 Próximas", value="Fila vazia", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Pula para próxima música")
    async def skip(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        vc = interaction.guild.voice_client
        if not vc or not vc.channel:
            return await interaction.response.send_message("❌ Não estou em nenhum canal de voz.")
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            return await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot.")
        
        dj_role_id = config.get('dj_role_id')
        if dj_role_id:
            role = interaction.guild.get_role(dj_role_id)
            if role and role in interaction.user.roles:
                pass
            else:
                current_dj_id = self.bot.current_dj.get(interaction.guild.id)
                if not current_dj_id or interaction.user.id != current_dj_id:
                    return await interaction.response.send_message("❌ Apenas o DJ ou pessoas com cargo privilegiado podem fazer isso.")
        
        vc = interaction.guild.voice_client

        if not vc or not vc.is_playing():
            return await interaction.response.send_message("Nada tocando agora.")

        queue = self.get_queue(interaction.guild.id)

        if not queue:
            vc.stop()
            await interaction.response.send_message("⏭️ Musica pulada. Fila vazia, parando.")
        else:
            vc.stop()
            await interaction.response.send_message("⏭️ Pulando para próxima...")

    @app_commands.command(name="pause", description="Pausa a música atual")
    async def pause(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        vc = interaction.guild.voice_client
        if not vc or not vc.channel:
            return await interaction.response.send_message("❌ Não estou em nenhum canal de voz.")
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            return await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot.")
        
        dj_role_id = config.get('dj_role_id')
        if dj_role_id:
            role = interaction.guild.get_role(dj_role_id)
            if role and role in interaction.user.roles:
                pass
            else:
                current_dj_id = self.bot.current_dj.get(interaction.guild.id)
                if not current_dj_id or interaction.user.id != current_dj_id:
                    return await interaction.response.send_message("❌ Apenas o DJ ou pessoas com cargo privilegiado podem fazer isso.")
        
        vc = interaction.guild.voice_client

        if not vc or not vc.is_playing():
            return await interaction.response.send_message("Nada tocando agora.")

        vc.pause()
        await interaction.response.send_message("⏸️ Pausado")

    @app_commands.command(name="resume", description="Continua a música pausada")
    async def resume(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        vc = interaction.guild.voice_client
        if not vc or not vc.channel:
            return await interaction.response.send_message("❌ Não estou em nenhum canal de voz.")
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            return await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot.")
        
        dj_role_id = config.get('dj_role_id')
        if dj_role_id:
            role = interaction.guild.get_role(dj_role_id)
            if role and role in interaction.user.roles:
                pass
            else:
                current_dj_id = self.bot.current_dj.get(interaction.guild.id)
                if not current_dj_id or interaction.user.id != current_dj_id:
                    return await interaction.response.send_message("❌ Apenas o DJ ou pessoas com cargo privilegiado podem fazer isso.")
        
        vc = interaction.guild.voice_client

        if not vc or not vc.is_paused():
            return await interaction.response.send_message("Não está pausado.")

        vc.resume()
        await interaction.response.send_message("▶️ Continuando...")

    @app_commands.command(name="stop", description="Para tudo e sai")
    async def stop(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        vc = interaction.guild.voice_client
        if not vc or not vc.channel:
            return await interaction.response.send_message("❌ Não estou em nenhum canal de voz.")
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            return await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot.")
        
        dj_role_id = config.get('dj_role_id')
        if dj_role_id:
            role = interaction.guild.get_role(dj_role_id)
            if role and role in interaction.user.roles:
                pass
            else:
                current_dj_id = self.bot.current_dj.get(interaction.guild.id)
                if not current_dj_id or interaction.user.id != current_dj_id:
                    return await interaction.response.send_message("❌ Apenas o DJ ou pessoas com cargo privilegiado podem fazer isso.")
        
        if interaction.guild.voice_client:
            self.bot.queues[interaction.guild.id] = []
            self.bot.current.pop(interaction.guild.id, None)
            self.bot.funk_mode.pop(interaction.guild.id, None)
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Saindo... 👋")
        else:
            await interaction.response.send_message("Não estou em canal de voz.")

    @app_commands.command(name="clear", description="Limpa a fila de músicas")
    async def clear(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        vc = interaction.guild.voice_client
        if not vc or not vc.channel:
            return await interaction.response.send_message("❌ Não estou em nenhum canal de voz.")
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            return await interaction.response.send_message("❌ Você precisa estar no mesmo canal de voz que o bot.")
        
        dj_role_id = config.get('dj_role_id')
        if dj_role_id:
            role = interaction.guild.get_role(dj_role_id)
            if role and role in interaction.user.roles:
                pass
            else:
                current_dj_id = self.bot.current_dj.get(interaction.guild.id)
                if not current_dj_id or interaction.user.id != current_dj_id:
                    return await interaction.response.send_message("❌ Apenas o DJ ou pessoas com cargo privilegiado podem fazer isso.")
        
        queue = self.get_queue(interaction.guild.id)
        if queue:
            queue.clear()
            await interaction.response.send_message("🗑️ Fila limpa!")
        else:
            await interaction.response.send_message("Fila já está vazia.")

    @app_commands.command(name="funk", description="Toca funk aleatório")
    async def funk(self, interaction: discord.Interaction):
        config = await get_music_config(self.bot, interaction.guild.id)
        music_channel_id = config.get('music_channel_id')
        
        if music_channel_id and interaction.channel_id != music_channel_id:
            channel = self.bot.get_channel(music_channel_id)
            channel_mention = channel.mention if channel else f"<#{music_channel_id}>"
            return await interaction.response.send_message(
                f"❌ Este comando só pode ser usado no canal {channel_mention}.",
                ephemeral=True
            )
        
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("Entre num canal de voz primeiro!")

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        
        self.bot.current_dj[interaction.guild.id] = interaction.user.id

        funk_searches = [
            "The Box Medley MC Ryan SP",
            "Cala a Boca e Me Chupa DJ Paulo Magrão",
            "MC Pipokinha",
            "MC Poze do Rodo",
            "MC Ryan SP funk 2025",
            "MC Dricka",
            "MC Lele JP",
            "MC Flavinho",
            "MC Menor ZL",
            "MC GH funk",
            "DJ Arana",
            "MC Lan",
            "MC Rick funk",
            "MC GW",
            "MC Magrinho",
            "MC Paulin da Capital",
            "MC Livinho",
            "MC Hariel",
            "MC Pierre funk",
            "MC Davi",
            "DJ Topo",
            "DJ GBR",
            "MC Daniel funk",
            "MC Neguinho do Kaxeta",
            "MTG funk",
            "DJ Win",
            "DJ Jhow Beats",
            "DJ Claudinho Buchecha",
            "MC Rebecca",
            "DJ Vovô funk",
            "MC Luan da BS",
            "Banda Eva funk",
            "DJ WS da Igrejinha",
            "Orochi funk",
            "MC Kevin funk",
            "WIU funk",
            "Ludmilla funk",
            "MC Saci",
            "DJ Kotim",
            "DJ Dubom",
            "MC L da Vinte",
            "DJ Swat",
            "Parado no Bailão",
            "DJ Clei",
            "Slowed funk brasil",
            "Phonk brasileiro",
            "Brazilian Phonk",
            "DJ LL funk",
            "DJ Japa NK",
            "funk slowed 2025",
            "funk automotivo",
            "MC IG",
            "MC Tati Zaqui",
            "MC Hariel funk",
            "funk paredão 2025",
            "funk gospel remix",
            "DJ 2D funk",
            "funk viral tiktok",
            "funk montagem",
            "funk grave arrastado",
            "funk pesado 2025",
            "funk brasil 2025",
            "MC funk 2025",
            "funk 150 bpm",
            "funk ostentação",
            "funk prohibited",
            "funk melody",
            "funk mix",
            "MC funk pesado",
            "batidao funk",
            "brazilian bass funk",
            "funk старо модерно",
            "funk brasileiro hit",
            "funk viral",
            "funk 2024 2025",
            "Ludmilla",
            "Anitta funk",
            "Luísa Sonza funk",
        ]
        
        import random
        busca = random.choice(funk_searches)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                await interaction.followup.send(f"🔍 Procurando funk: {busca}...")
                
                info = ydl.extract_info(f"scsearch20:{busca}", download=False)
                if not info or 'entries' not in info:
                    return await interaction.followup.send("❌ Nenhum funk encontrado.")
                
                valid_entries = [e for e in info['entries'] if e.get('duration', 0) and e.get('duration', 0) >= 30]
                
                if not valid_entries:
                    return await interaction.followup.send("❌ Nenhum funk com duração mínima encontrado.")
                
                entry = random.choice(valid_entries)
                
                info = ydl.extract_info(entry['url'], download=False)
                url = info['url']
                titulo = info.get('title', 'Funk')
                extrator = info.get('extractor_key', 'SoundCloud')
                duration = info.get('duration', 0)

                music_info = {
                    'url': url,
                    'title': titulo,
                    'extractor': extrator,
                    'thumbnail': '',
                    'duration': duration,
                    'requester': interaction.user.name
                }

                queue = self.get_queue(interaction.guild.id)
                duracao_str = format_duration(duration)
                
                self.bot.funk_mode[interaction.guild.id] = True

                if vc.is_playing() or vc.is_paused():
                    queue.append(music_info)
                    await interaction.followup.send(
                        f"📝 Adicionado à fila: **{titulo}** [{duracao_str}] (posição {len(queue)})"
                    )
                else:
                    source = discord.FFmpegOpusAudio(url, **FFMPEG_OPTIONS)
                    self.bot.current[interaction.guild.id] = music_info

                    def after_playing(error):
                        if error:
                            logger.error(f'Erro no player: {error}')
                        asyncio.run_coroutine_threadsafe(
                            self.play_next(interaction.guild), self.bot.loop
                        )

                    vc.play(source, after=after_playing)
                    await interaction.followup.send(
                        f"🎶 Tocando Funk: **{titulo}** [{duracao_str}] via **{extrator}**"
                    )

            except Exception as e:
                await interaction.followup.send(f"❌ Erro ao processar: {str(e)[:100]}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicaCog(bot))

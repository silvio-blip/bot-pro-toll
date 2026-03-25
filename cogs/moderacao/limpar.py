# -*- coding: utf-8 -*-
# Sistema de Limpeza de Mensagens - Comando /limpar
# Versão completa com todas as funcionalidades

import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, ButtonStyle, SelectOption
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, List

# Remover logs HTTP detalhados
logging.getLogger('discord.http').setLevel(logging.ERROR)
logger = logging.getLogger("LimparCog")


# --- Função Auxiliar para buscar Configurações ---
async def get_limpar_config(bot, guild_id: int) -> dict:
    try:
        if not hasattr(bot, 'supabase_client'):
            return {}
        
        # Tentar buscar na tabela server_configs (onde está cleaner_role_id)
        try:
            response = bot.supabase_client.table("server_configs").select("cleaner_role_id", "limpar_max_messages", "limpar_enabled").eq("server_id", guild_id).execute()
            if response.data and response.data[0]:
                data = response.data[0]
                return {
                    "role_id": data.get("cleaner_role_id"),
                    "max_messages": data.get("limpar_max_messages", 100),
                    "enabled": data.get("limpar_enabled", False)
                }
        except:
            pass
        
        # Fallback para server_configurations
        response = bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
        if response.data:
            return response.data[0].get('settings', {}).get('limpar', {})
            
    except Exception as e:
        logger.error(f"Erro ao buscar config de limpar para o servidor {guild_id}: {e}", exc_info=True)
    return {}


# --- Sistema de Verificação de Permissão ---
async def verificar_permissao_limpar(bot, interaction: Interaction) -> bool:
    """Verifica se o usuário tem permissão para usar o comando /limpar"""
    guild_id = interaction.guild.id
    
    # Buscar configuração do servidor
    config = await get_limpar_config(bot, guild_id)
    
    # Primeiro verificar se é administrador (sempre pode)
    if interaction.user.guild_permissions.administrator:
        return True
    
    # Se a verificação por cargo estiver ativa e um cargo estiver configurado
    if config.get('enabled') and config.get('role_id'):
        role = interaction.guild.get_role(config['role_id'])
        if role and role in interaction.user.roles:
            return True
    
    # Se não tiver cargo configurado, verificar permissão native do Discord
    return interaction.user.guild_permissions.manage_messages


# --- Sistema de Busca de Mensagens ---
async def buscar_mensagens(
    canal: discord.TextChannel,
    quantidade: int,
    usuario: Optional[discord.Member] = None,
    periodo: Optional[str] = None,
    limite_max: int = 100
) -> List[discord.Message]:
    """Busca mensagens para deletar baseado nos filtros"""
    mensagens = []
    
    # Calcular cutoff de tempo baseado no período
    cutoff_time = None
    if periodo:
        now = datetime.now(timezone.utc)
        if periodo == '1m':
            cutoff_time = now - timedelta(minutes=1)
        elif periodo == '15m':
            cutoff_time = now - timedelta(minutes=15)
        elif periodo == '1h':
            cutoff_time = now - timedelta(hours=1)
        elif periodo == '24h':
            cutoff_time = now - timedelta(hours=24)
        elif periodo == 'today':
            cutoff_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # 'all' não tem cutoff_time (busca todas as mensagens)
    
    # Buscar mensagens
    quantidade_buscar = min(quantidade, limite_max)
    if periodo == 'all':
        quantidade_buscar = min(500, limite_max * 5)  # Buscar mais para 'all'
    
    try:
        async for message in canal.history(limit=quantidade_buscar + 50):
            # Verificar se a mensagem é muito antiga (mais de 14 dias - limite do Discord)
            if cutoff_time and message.created_at.replace(tzinfo=timezone.utc) < cutoff_time:
                continue
            
            # Verificar filtro de usuário
            if usuario and message.author.id != usuario.id:
                continue
            
            # Não incluir mensagens do próprio bot na contagem inicial
            if message.author.bot and not usuario:
                continue
            
            mensagens.append(message)
            
            if len(mensagens) >= quantidade:
                break
    except Exception as e:
        logger.error(f"Erro ao buscar mensagens: {e}")
    
    return mensagens[:quantidade]


# --- View de Confirmação ---
class ConfirmarLimpeza(ui.View):
    def __init__(self, bot, canal: discord.TextChannel, mensagens: List[discord.Message], quantidade: int, usuario: Optional[discord.Member], periodo: Optional[str]):
        super().__init__(timeout=30)
        self.bot = bot
        self.canal = canal
        self.mensagens = mensagens
        self.quantidade = quantidade
        self.usuario = usuario
        self.periodo = periodo

    @ui.button(label="🗑️ Confirmar Limpeza", style=ButtonStyle.danger, emoji="🧹", row=0)
    async def confirmar(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted_count = 0
            for msg in self.mensagens:
                try:
                    await msg.delete()
                    deleted_count += 1
                except:
                    pass
            
            embed = discord.Embed(
                title="🧹 Mensagens Limpas",
                description=f"Foram deletadas **{deleted_count}** mensagens do canal {self.canal.mention}",
                color=discord.Color.green()
            )
            
            if self.usuario:
                embed.add_field(name="Usuário", value=self.usuario.mention, inline=True)
            if self.periodo:
                embed.add_field(name="Período", value=f"`{self.periodo}`", inline=True)
                
            embed.set_footer(text=f"Executado por {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Mensagem pública
            await self.canal.send(f"🧹 {interaction.user.mention} limpou **{deleted_count}** mensagens.", delete_after=10)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao limpar mensagens: {e}", ephemeral=True)
        
        self.stop()

    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary, row=0)
    async def cancelar(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="❌ Operação cancelada.",
            embed=None,
            view=None
        )
        self.stop()


# --- Modal de Configuração (para o painel de controle) ---
class LimparConfigModal(ui.Modal, title="Config. Limpar Mensagens"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}
        
        self.add_item(ui.TextInput(
            label="ID do Cargo autorizado",
            placeholder="ID do cargo que pode usar o comando",
            default=str(self.config.get("role_id", "")),
            required=False
        ))
        
        self.add_item(ui.TextInput(
            label="Máximo de mensagens (1-100)",
            placeholder="Limite máximo por uso",
            default=str(self.config.get("max_messages", 100)),
            required=False
        ))
        
        self.add_item(ui.TextInput(
            label="Ativar verificação por cargo (sim/não)",
            placeholder="sim = só quem tem o cargo pode usar",
            default="não" if not self.config.get("enabled") else "sim",
            required=False
        ))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            role_id_str = self.children[0].value.strip()
            max_messages_str = self.children[1].value.strip()
            enabled_str = self.children[2].value.strip().lower()
            
            role_id = int(role_id_str) if role_id_str.isdigit() else None
            max_messages = int(max_messages_str) if max_messages_str.isdigit() else 100
            enabled = enabled_str in ["sim", "yes", "true", "1", "on", "ativado"]
            
            # Validar max_messages
            max_messages = max(1, min(100, max_messages))
            
            # Salvar na tabela server_configs
            try:
                self.bot.supabase_client.table("server_configs").upsert({
                    "server_id": interaction.guild.id,
                    "cleaner_role_id": role_id,
                    "limpar_max_messages": max_messages,
                    "limpar_enabled": enabled
                }, on_conflict="server_id").execute()
                
                await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
            except Exception as e:
                # Fallback: salvar em server_configurations
                def update_settings(settings):
                    settings['limpar'] = {
                        "role_id": role_id,
                        "max_messages": max_messages,
                        "enabled": enabled
                    }
                
                success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)
                
                if success:
                    await interaction.followup.send("✅ Configurações salvas com sucesso!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Erro ao salvar config de limpar: {e}")
            await interaction.followup.send(f"❌ Erro ao processar: {e}", ephemeral=True)


# --- Cog Principal ---
class LimparCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("[✅] Cog 'limpar' carregado.")

    @app_commands.command(
        name="limpar",
        description="[Moderação] Limpa mensagens do canal. Use /limparhelp para ver todas as opções."
    )
    @app_commands.describe(
        quantidade="Número de mensagens para limpar (1-100)",
        usuario="Filtrar por usuário específico (opcional)",
        canal="Canal para limpar mensagens (opcional, padrão: atual)",
        periodo="Período: 1m, 15m, 1h, 24h, today, all"
    )
    @app_commands.choices(
        periodo=[
            app_commands.Choice(name="Último minuto", value="1m"),
            app_commands.Choice(name="Últimos 15 minutos", value="15m"),
            app_commands.Choice(name="Última hora", value="1h"),
            app_commands.Choice(name="Últimas 24 horas", value="24h"),
            app_commands.Choice(name="Hoje", value="today"),
            app_commands.Choice(name="Todas as mensagens", value="all"),
        ]
    )
    async def limpar(
        self,
        interaction: Interaction,
        quantidade: int,
        usuario: Optional[discord.Member] = None,
        canal: Optional[discord.TextChannel] = None,
        periodo: Optional[str] = None
    ):
        """Comando para limpar mensagens do canal com todas as opções"""
        
        # Verificar permissão
        if not await verificar_permissao_limpar(self.bot, interaction):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando. "
                "Você precisa ter a permissão 'Gerenciar Mensagens' ou o cargo configurado no painel.",
                ephemeral=True
            )
            return
        
        # Validar quantidade
        config = await get_limpar_config(self.bot, interaction.guild.id)
        maximo = config.get('max_messages', 100)
        
        if quantidade < 1:
            await interaction.response.send_message("❌ A quantidade deve ser pelo menos 1.", ephemeral=True)
            return
        
        if quantidade > maximo:
            await interaction.response.send_message(
                f"❌ O limite máximo de mensagens é **{maximo}**. "
                f"Para limpar mais mensagens, use o comando novamente ou ajuste nas configurações.",
                ephemeral=True
            )
            return
        
        # Verificar se o bot tem permissão
        if not interaction.app_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Eu não tenho permissão para `Gerenciar Mensagens` neste canal.",
                ephemeral=True
            )
            return
        
        # Determinar o canal
        target_canal = canal or interaction.channel
        
        # Se período for 'all', aumentar a quantidade de busca
        quantidade_buscar = quantidade
        if periodo == 'all':
            quantidade_buscar = min(500, maximo * 5)
        
        # Buscar mensagens
        mensagens = await buscar_mensagens(
            target_canal,
            quantidade_buscar,
            usuario,
            periodo,
            maximo
        )
        
        if not mensagens:
            await interaction.response.send_message(
                f"❌ Nenhuma mensagem encontrada para limpar.",
                ephemeral=True
            )
            return
        
        # Limitar às mensagens encontradas
        mensagens = mensagens[:quantidade]
        quantidade_encontrada = len(mensagens)
        
        # Criar embed de preview
        embed = discord.Embed(
            title="🧹 Preview da Limpeza",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="Canal",
            value=target_canal.mention,
            inline=True
        )
        
        embed.add_field(
            name="Mensagens",
            value=f"**{quantidade_encontrada}**",
            inline=True
        )
        
        if usuario:
            embed.add_field(
                name="Usuário",
                value=usuario.mention,
                inline=True
            )
        
        if periodo:
            periodo_nomes = {
                "1m": "Último minuto",
                "15m": "15 minutos",
                "1h": "1 hora",
                "24h": "24 horas",
                "today": "Hoje",
                "all": "Todas"
            }
            embed.add_field(
                name="Período",
                value=periodo_nomes.get(periodo, periodo),
                inline=True
            )
        
        embed.set_footer(text=f"Solicitado por {interaction.user.name}")
        
        # Se quantidade > 10, pedir confirmação
        if quantidade_encontrada > 10:
            view = ConfirmarLimpeza(
                self.bot,
                target_canal,
                mensagens,
                quantidade_encontrada,
                usuario,
                periodo
            )
            await interaction.response.send_message(
                content=f"⚠️ **Confirmação necessária**\n\n"
                        f"Você está prestes a limpar **{quantidade_encontrada}** mensagens. "
                        f"Esta ação não pode ser desfeita.",
                embed=embed,
                view=view,
                ephemeral=True
            )
        else:
            # Limpar imediatamente para quantidades pequenas
            try:
                deleted_count = 0
                for msg in mensagens:
                    try:
                        await msg.delete()
                        deleted_count += 1
                    except:
                        pass
                
                embed_result = discord.Embed(
                    title="🧹 Mensagens Limpas",
                    description=f"Foram deletadas **{deleted_count}** mensagens do canal {target_canal.mention}",
                    color=discord.Color.green()
                )
                
                if usuario:
                    embed_result.add_field(name="Usuário", value=usuario.mention, inline=True)
                if periodo:
                    embed_result.add_field(name="Período", value=periodo, inline=True)
                    
                embed_result.set_footer(text=f"Executado por {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed_result, ephemeral=True)
                
                # Mensagem pública
                await target_canal.send(
                    f"🧹 {interaction.user.mention} limpou **{deleted_count}** mensagens.",
                    delete_after=10
                )
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Erro ao limpar mensagens: {e}",
                    ephemeral=True
                )

    # --- Comando de ajuda /limparhelp ---
    @app_commands.command(
        name="limparhelp",
        description="Mostra todas as opções do comando /limpar"
    )
    async def limpar_help(self, interaction: Interaction):
        """Mostra a ajuda do comando /limpar"""
        
        embed = discord.Embed(
            title="🧹 Ajuda - Comando /limpar",
            description="Comando para limpar mensagens do canal",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="📌 Como usar",
            value="""```
/limpar quantidade:10
/limpar quantidade:50 usuario:@fulano
/limpar quantidade:100 periodo:1h canal:#chat
/limpar quantidade:50 periodo:all usuario:@fulano canal:#geral
```""",
            inline=False
        )
        
        embed.add_field(
            name="📊 Parâmetros",
            value="""**quantidade** (obrigatório) - Número de mensagens para limpar (1-100)
**usuario** (opcional) - Filtrar por usuário específico
**canal** (opcional) - Canal para limpar (padrão: canal atual)
**periodo** (opcional) - Período de tempo para buscar""",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Opções de Período",
            value="""`1m` - Último minuto
`15m` - Últimos 15 minutos
`1h` - Última hora
`24h` - Últimas 24 horas
`today` - Apenas mensagens de hoje
`all` - Todas as mensagens do canal""",
            inline=False
        )
        
        embed.add_field(
            name="🔐 Permissão",
            value="Você precisa ter a permissão **Gerenciar Mensagens** ou o cargo configurado no painel de controle.",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Aviso",
            value="O Discord só permite deletar mensagens dos **últimos 14 dias**.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @limpar.error
    async def limpar_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.",
                ephemeral=True
            )
        else:
            logger.error(f"Erro no comando /limpar: {error}")
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar o comando.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(LimparCog(bot))
    logger.info("[✅] Cog 'limpar' configurado com sucesso.")
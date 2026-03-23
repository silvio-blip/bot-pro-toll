
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, SelectOption, Embed, Color

# --- DADOS DOS COMANDOS ---
# Estrutura de dados para armazenar as informações de cada categoria.
# Isso facilita a geração dos embeds dinamicamente.
COMMANDS_DATA = {
    "gerenciamento": {
        "label": "Gerenciamento",
        "emoji": "⚙️",
        "description": "Comandos essenciais para registrar e gerenciar o bot.",
        "commands": [
            ("</registrar:0>", "Inicia o registro do servidor e do administrador."),
            ("</verificar:0>", "Ativa sua conta com o código de verificação."),
            ("</painel:0>", "Abre o painel de controle para configurar tudo."),
            ("</recuperar-senha:0>", "Força a redefinição de senha de um admin."),
            ("</desregistrar-servidor:0>", "Remove todos os dados do seu servidor do bot."),
        ]
    },
    "moderacao": {
        "label": "Moderação",
        "emoji": "🛡️",
        "description": "Ferramentas para proteger seu servidor e gerenciar membros.",
        "commands": [
            ("</warn:0>", "Aplica uma advertência a um membro."),
            ("</configurar no painel>", "Anti-Raid, Captcha, Filtros e mais são configurados via `/painel`."),
        ]
    },
    "utilidades": {
        "label": "IA & Utilidades",
        "emoji": "🤖",
        "description": "Funcionalidades úteis e de inteligência artificial.",
        "commands": [
            ("</chat:0>", "Converse com uma IA diretamente no chat."),
            ("</previsão-tempo:0>", "Mostra a previsão do tempo para uma cidade."),
            ("</qr-code:0>", "Gera um QR Code a partir de um texto ou link."),
        ]
    },
    "notificacoes": {
        "label": "Notificações Sociais",
        "emoji": "🌐",
        "description": "Anuncie automaticamente posts de redes sociais.",
        "commands": [
            ("</configurar no painel>", "YouTube, Twitch, TikTok e mais são configurados via `/painel`."),
        ]
    }
}

# --- COMPONENTES DA UI ---

class HelpSelect(ui.Select):
    """
    O menu de seleção que permite ao usuário escolher uma categoria de ajuda.
    """
    def __init__(self):
        # Cria as opções do menu a partir do dicionário de dados
        options = [
            SelectOption(label="Início", description="Voltar para a visão geral.", emoji="🏠", value="inicio")
        ]
        for key, data in COMMANDS_DATA.items():
            options.append(SelectOption(label=data["label"], description=data["description"], emoji=data["emoji"], value=key))
        
        super().__init__(placeholder="Escolha uma categoria de comandos...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        # Esta função é chamada quando o usuário seleciona uma opção.
        # Ela edita a mensagem original para mostrar os comandos da categoria escolhida.
        choice = self.values[0]
        
        if choice == "inicio":
            # Se a escolha for "Início", mostra o embed inicial
            new_embed = create_initial_embed(interaction.client)
        else:
            # Caso contrário, cria um embed para a categoria selecionada
            category_data = COMMANDS_DATA[choice]
            new_embed = Embed(
                title=f"{category_data['emoji']} Comandos de {category_data['label']}",
                description=category_data['description'],
                color=Color.blue()
            )
            # Adiciona os comandos da categoria ao embed
            for name, description in category_data['commands']:
                new_embed.add_field(name=name, value=description, inline=False)
            
            if interaction.client.user.avatar:
                new_embed.set_thumbnail(url=interaction.client.user.avatar.url)
            new_embed.set_footer(text="Selecione outra categoria abaixo para ver mais comandos.")

        # Edita a mensagem original com o novo embed
        await interaction.response.edit_message(embed=new_embed)

class HelpView(ui.View):
    """
    A View que contém o menu de seleção.
    """
    def __init__(self):
        super().__init__(timeout=None)  # Timeout None para a view não expirar
        self.add_item(HelpSelect())

# --- FUNÇÃO HELPER PARA EMBED ---

def create_initial_embed(bot_client):
    """
    Cria o embed inicial que é mostrado quando o comando /ajuda é usado pela primeira vez.
    """
    embed = Embed(
        title="Painel de Ajuda Interativo",
        description="Bem-vindo(a) ao menu de ajuda!\n\n"
                    "Use o menu de seleção abaixo para navegar pelas categorias e "
                    "descobrir tudo que eu posso fazer. Cada categoria lista os comandos "
                    "e suas funções.",
        color=Color.dark_purple()
    )
    if bot_client.user.avatar:
        embed.set_thumbnail(url=bot_client.user.avatar.url)
    embed.set_footer(text=f"{bot_client.user.name} | Selecione uma categoria abaixo.")
    return embed

# --- COG PRINCIPAL ---

class Ajuda(commands.Cog):
    """
    O Cog que contém o comando de ajuda.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ajuda", description="Mostra um painel de ajuda interativo com todos os comandos.")
    async def ajuda(self, interaction: Interaction):
        # Cria o embed e a view iniciais e os envia ao usuário
        initial_embed = create_initial_embed(self.bot)
        view = HelpView()
        await interaction.response.send_message(embed=initial_embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Ajuda(bot))


import discord
from discord.ext import commands
from discord import app_commands, Interaction
from typing import Optional, List, Dict, Set

# --- A View da Enquete (Onde a mágica acontece) ---
class PollView(discord.ui.View):
    def __init__(self, question: str, options: List[str], author_name: str):
        super().__init__(timeout=None)  # A enquete não expira
        self.question = question
        self.options = options
        self.author_name = author_name
        
        # Estrutura para armazenar os votos: {option_index: {user_id, user_id, ...}}
        self.votes: Dict[int, Set[int]] = {i: set() for i in range(len(options))}

        # Adiciona os botões dinamicamente
        for i, option_text in enumerate(options):
            button = discord.ui.Button(
                label=f"{option_text} (0)", 
                style=discord.ButtonStyle.secondary,
                custom_id=f"poll_option_{i}"
            )
            button.callback = self.button_callback
            self.add_item(button)

    def create_embed(self) -> discord.Embed:
        """Cria ou atualiza o embed da enquete com a contagem de votos."""
        embed = discord.Embed(
            title=f"📊 Enquete: {self.question}",
            description="Clique em uma das opções abaixo para votar. Seu voto é único!",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Enquete criada por {self.author_name}")
        return embed

    async def button_callback(self, interaction: Interaction):
        """Processa o clique em um botão de voto."""
        user_id = interaction.user.id
        custom_id = interaction.data['custom_id']
        selected_index = int(custom_id.split('_')[-1])

        # Verifica se o usuário já votou em alguma opção e remove o voto antigo
        for index, voters in self.votes.items():
            if user_id in voters:
                # Se o usuário clicou na mesma opção, remove o voto (anula)
                if index == selected_index:
                    voters.remove(user_id)
                    break
                # Se clicou em outra, remove o voto antigo para mover para o novo
                voters.remove(user_id)

        # Adiciona o novo voto
        # Se o voto foi anulado no passo anterior, este 'else' não será executado.
        else:
            self.votes[selected_index].add(user_id)

        # Atualiza os labels dos botões com a nova contagem
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item_index = int(item.custom_id.split('_')[-1])
                item.label = f"{self.options[item_index]} ({len(self.votes[item_index])})"
        
        # Atualiza a mensagem com a nova view (que contém os botões atualizados)
        await interaction.response.edit_message(view=self)

# --- O Comando de Barra ---
class PollCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="enquete", description="Cria uma enquete com botões e votos em tempo real.")
    @app_commands.describe(
        pergunta="A pergunta da sua enquete.",
        opcao_1="Primeira opção de voto.",
        opcao_2="Segunda opção de voto.",
        opcao_3="Terceira opção de voto (opcional).",
        opcao_4="Quarta opção de voto (opcional).",
        opcao_5="Quinta opção de voto (opcional).",
        opcao_6="Sexta opção de voto (opcional).",
        opcao_7="Sétima opção de voto (opcional).",
        opcao_8="Oitava opção de voto (opcional).",
        opcao_9="Nona opção de voto (opcional).",
        opcao_10="Décima opção de voto (opcional)."
    )
    async def enquete(self, interaction: Interaction, 
                      pergunta: str, 
                      opcao_1: str, 
                      opcao_2: str, 
                      opcao_3: Optional[str] = None,
                      opcao_4: Optional[str] = None,
                      opcao_5: Optional[str] = None,
                      opcao_6: Optional[str] = None,
                      opcao_7: Optional[str] = None,
                      opcao_8: Optional[str] = None,
                      opcao_9: Optional[str] = None,
                      opcao_10: Optional[str] = None):
        
        await interaction.response.defer(ephemeral=False)
        
        options = [opt for opt in [opcao_1, opcao_2, opcao_3, opcao_4, opcao_5, opcao_6, opcao_7, opcao_8, opcao_9, opcao_10] if opt is not None]
        
        if len(options) > 10:
            await interaction.followup.send("Você só pode fornecer até 10 opções.", ephemeral=True)
            return
        if len(options) < 2:
            await interaction.followup.send("Você precisa fornecer pelo menos 2 opções.", ephemeral=True)
            return

        # Cria a view e o embed inicial
        view = PollView(question=pergunta, options=options, author_name=interaction.user.display_name)
        embed = view.create_embed()

        await interaction.followup.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(PollCommand(bot))

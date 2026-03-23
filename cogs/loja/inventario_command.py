import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, Embed, SelectOption, ButtonStyle
import logging
from collections import defaultdict
import json

# --- Função de Correção de URL Definitiva --- #
def get_image_url_from_data(item_data):
    """Extrai a URL da imagem de forma robusta, lidando com JSON aninhado e chaves malformadas."""
    data_to_process = None
    # 1. Se o dado for uma string que é um JSON, decodifica primeiro.
    if isinstance(item_data, str):
        try:
            data_to_process = json.loads(item_data)
        except json.JSONDecodeError:
            # Se não for JSON, trata como uma URL simples.
            if item_data.startswith('http'):
                return item_data
            data_to_process = item_data # Mantém como string se não for JSON nem http
    else:
        data_to_process = item_data

    # 2. Agora processa o resultado (que deve ser um dicionário ou string)
    if isinstance(data_to_process, dict):
        url = data_to_process.get('image_url') or data_to_process.get('url')
        if url: return url
        # Busca por valores que sejam URLs, para chaves malformadas
        for key, value in data_to_process.items():
            if isinstance(value, str) and (value.startswith('http') or value.startswith('//')):
                if value.startswith('//'):
                    # Adiciona 'https://' e retorna, tratando o caso `{"https": "//link..."}`
                    return 'https://' + value.lstrip('//') 
                return value

    # 3. Fallback final para strings
    if isinstance(data_to_process, str) and data_to_process.startswith('http'):
        return data_to_process
        
    return None

# --- Funções de DB ---
async def update_user_profile_background(bot, guild_id: int, user_id: int, image_url: str):
    try: bot.supabase_client.table("gamification_profiles").upsert({"guild_id": guild_id, "user_id": user_id, "profile_background_url": image_url}).execute()
    except Exception as e: logging.error(f"Erro ao ATUALIZAR o fundo de perfil para o user {user_id}: {e}")

async def update_user_profile_avatar(bot, guild_id: int, user_id: int, image_url: str):
    try: bot.supabase_client.table("gamification_profiles").upsert({"guild_id": guild_id, "user_id": user_id, "profile_avatar_url": image_url}).execute()
    except Exception as e: logging.error(f"Erro ao ATUALIZAR o avatar de perfil para o user {user_id}: {e}")

# --- Views do Inventário ---

class EquipItemSelect(ui.Select):
    def __init__(self, bot, items: list, item_type: str, target_user: discord.Member):
        self.bot = bot
        self.items_map = {str(item['id']): item for item in items}
        self.item_type = item_type
        self.target_user = target_user
        options = [SelectOption(label=item['item_name'], value=str(item['id']), description=f"Comprado em: {item['purchased_at'][:10]}", emoji="🖼️" if item_type == 'fundo_perfil' else '👤') for item in items]
        if not options: options.append(SelectOption(label="Nenhum item desta categoria.", value="disabled"))
        super().__init__(placeholder=f"Selecione um {self.get_item_type_name(True)} para equipar...", options=options, min_values=1, max_values=1)

    def get_item_type_name(self, singular=False):
        if self.item_type == 'fundo_perfil': return "fundo" if singular else "Fundos"
        return "avatar" if singular else "Avatares"

    async def callback(self, interaction: Interaction):
        item_id = self.values[0]
        if item_id == "disabled": return await interaction.response.send_message("Nenhum item selecionado.", ephemeral=True)
            
        selected_item = self.items_map[item_id]
        raw_item_data = selected_item.get('item_data')
        image_url = get_image_url_from_data(raw_item_data)

        await interaction.response.defer(ephemeral=True)

        try:
            if not image_url: raise ValueError("URL da imagem não pôde ser determinada para este item.")

            if self.item_type == 'fundo_perfil': await update_user_profile_background(self.bot, interaction.guild.id, self.target_user.id, image_url)
            elif self.item_type == 'avatar_perfil': await update_user_profile_avatar(self.bot, interaction.guild.id, self.target_user.id, image_url)
            
            embed = Embed(description=f"✅ Você equipou o {self.get_item_type_name(True)} **{selected_item['item_name']}**! Use `/perfil` para ver.", color=discord.Color.green())
            if self.item_type == 'fundo_perfil': embed.set_image(url=image_url)
            elif self.item_type == 'avatar_perfil': embed.set_thumbnail(url=image_url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logging.error(f"Erro ao equipar item: {e}")
            await interaction.followup.send("❌ Ocorreu um erro ao tentar equipar o item.", ephemeral=True)

class InventoryView(ui.View):
    def __init__(self, bot, inventory_items: dict, target_user: discord.Member):
        super().__init__(timeout=180)
        self.bot = bot
        self.inventory_items = inventory_items
        self.target_user = target_user
        self.create_category_buttons()

    def create_category_buttons(self):
        if self.inventory_items.get('fundo_perfil'): self.add_item(self.create_category_button("Fundos de Perfil", "fundo_perfil", "🖼️"))
        if self.inventory_items.get('avatar_perfil'): self.add_item(self.create_category_button("Avatares de Perfil", "avatar_perfil", "👤"))
        if self.inventory_items.get('licenca_comando'): self.add_item(self.create_category_button("Licenças de Comando", "licenca_comando", "🔑"))

    def create_category_button(self, label: str, custom_id: str, emoji: str):
        button = ui.Button(label=label, custom_id=custom_id, style=ButtonStyle.secondary, emoji=emoji)
        button.callback = self.on_category_button_click
        return button

    async def on_category_button_click(self, interaction: Interaction):
        custom_id = interaction.data['custom_id']
        items_in_category = self.inventory_items.get(custom_id)
        if not items_in_category: return await interaction.response.send_message("Você não possui itens nesta categoria.", ephemeral=True)

        if custom_id in ['fundo_perfil', 'avatar_perfil']:
            equip_view = ui.View(timeout=180)
            equip_view.add_item(EquipItemSelect(self.bot, items_in_category, custom_id, self.target_user))
            type_name = "Fundos" if custom_id == 'fundo_perfil' else "Avatares"
            embed = Embed(title=f"Equipar {type_name}", description=f"Selecione um item para equipar no perfil de **{self.target_user.display_name}**.", color=discord.Color.blue())
            await interaction.response.edit_message(embed=embed, view=equip_view)
        else:
            embed = Embed(title=f"Inventário - {interaction.data['custom_id']}", color=discord.Color.green())
            embed.description = "\n".join([f"- **{item['item_name']}**" for item in items_in_category])
            await interaction.response.edit_message(embed=embed, view=None)

class InventarioCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="inventario", description="Mostra seus itens comprados na loja.")
    @app_commands.describe(membro="[ADM] Veja o inventário de outro membro.")
    async def inventario(self, interaction: Interaction, membro: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        target_user = membro or interaction.user
        if not (target_user.id == interaction.user.id) and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("Você só pode ver o seu próprio inventário.", ephemeral=True)

        try:
            response = self.bot.supabase_client.table("user_inventories").select("*").eq("guild_id", interaction.guild.id).eq("user_id", target_user.id).order("purchased_at", desc=True).execute()
            items = response.data
        except Exception as e:
            logging.error(f"Erro ao buscar inventário: {e}")
            return await interaction.followup.send("❌ Erro ao buscar o inventário.", ephemeral=True)

        if not items:
            embed = Embed(title=f"Inventário de {target_user.display_name}", description="Seu inventário está vazio. Visite a `/loja` para comprar itens!", color=discord.Color.red())
            return await interaction.followup.send(embed=embed)

        inventory_items = defaultdict(list)
        for item in items:
            inventory_items[item['item_type']].append(item)

        embed = Embed(title=f"Inventário de {target_user.display_name}", description="Selecione uma categoria para ver e gerenciar seus itens.", color=discord.Color.purple())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        view = InventoryView(self.bot, inventory_items, target_user)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(InventarioCog(bot))

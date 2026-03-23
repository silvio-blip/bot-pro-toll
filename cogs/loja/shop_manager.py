import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, SelectOption, TextStyle, ButtonStyle
import logging

# --- Funções de Ajuda ---

def parse_simple_data(data_string: str) -> dict:
    if not data_string or ':' not in data_string:
        return {}
    key, value = data_string.split(':', 1)
    try:
        if '.' in value:
            return {key.strip(): float(value.strip())}
        return {key.strip(): int(value.strip())}
    except ValueError:
        return {key.strip(): value.strip()}

def format_simple_data(data_dict: dict) -> str:
    if not data_dict:
        return ""
    key, value = next(iter(data_dict.items()))
    return f"{key}: {value}"

# --- Modais de Edição e Criação ---

class ItemModal(ui.Modal):
    def __init__(self, bot: commands.Bot, item: dict = None):
        self.bot = bot
        self.item = item
        is_editing = item is not None
        super().__init__(title=f"Editando: {item['name'][:40]}" if is_editing else "Adicionar Novo Item")

        self.name = ui.TextInput(label="Nome do Item", default=item.get('name', '') if is_editing else "", placeholder="Ex: Cargo VIP Amarelo" if not is_editing else None)
        self.description = ui.TextInput(label="Descrição", style=TextStyle.long, default=item.get('description', '') if is_editing else "", placeholder="Ex: Muda a cor do seu nome para amarelo." if not is_editing else None)
        self.price = ui.TextInput(label="Preço em Pontos", default=str(item.get('price', 0)) if is_editing else "", placeholder="Ex: 1000" if not is_editing else None)
        self.item_type = ui.TextInput(label="Tipo do Item", default=item.get('item_type', '') if is_editing else "", placeholder="Ex: fundo_perfil, avatar_perfil, cargo_colorido" if not is_editing else None)
        self.item_data = ui.TextInput(label="Dado (URL da imagem ou ID do cargo)", default=format_simple_data(item.get('item_data', {})) if is_editing else "", placeholder="Ex: https://i.imgur.com/link.png ou role_id:12345" if not is_editing else None, required=False)

        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.price)
        self.add_item(self.item_type)
        self.add_item(self.item_data)

    async def on_submit(self, interaction: Interaction):
        try:
            price_int = int(self.price.value)
            # Correção: usar .value para obter o dado do campo de texto
            item_data_str = self.item_data.value
            if ':' in item_data_str:
                data_dict = parse_simple_data(item_data_str)
            else: # Se não for um par chave-valor, assume-se que é uma URL direta para os tipos de item comuns
                data_dict = {"url": item_data_str} if item_data_str else {}

            is_editing = self.item is not None

            payload = {
                "name": self.name.value,
                "description": self.description.value,
                "price": price_int,
                "item_type": self.item_type.value.lower().strip(),
                "item_data": data_dict
            }
            
            await interaction.response.defer(ephemeral=True)

            table = self.bot.supabase_client.table("loja_items")
            if is_editing:
                table.update(payload).eq("id", self.item['id']).execute()
                await interaction.followup.send("✅ Item atualizado com sucesso!", ephemeral=True)
            else:
                payload["guild_id"] = interaction.guild.id
                payload["is_active"] = True
                table.insert(payload).execute()
                await interaction.followup.send("✅ Item adicionado com sucesso!", ephemeral=True)

        except Exception as e:
            logging.error(f"Falha ao salvar item: {e}")
            await interaction.followup.send(f"❌ Erro ao salvar o item: {e}", ephemeral=True)

# --- Views e Selects de Gerenciamento ---

class ItemActionSelect(ui.Select):
    def __init__(self, items: list):
        self.items_map = {str(item['id']): item for item in items}
        options = [SelectOption(label=item['name'], value=str(item['id']), description=f"ID: {item['id']} | Tipo: {item['item_type']}") for item in items]
        if not options: options.append(SelectOption(label="Nenhum item encontrado", value="disabled"))
        
        super().__init__(placeholder="Selecione um item para uma ação...", options=options, disabled=not items)

    async def callback(self, interaction: Interaction):
        if self.values[0] == "disabled":
            await interaction.response.send_message("Nenhum item para selecionar.", ephemeral=True)
            return
        
        self.view.selected_item_id = int(self.values[0])
        selected_item = self.items_map[self.values[0]]
        self.view.enable_buttons()
        
        await interaction.response.edit_message(content=f"Você selecionou: **{selected_item['name']}**. Escolha uma ação.", view=self.view)

class ItemActionView(ui.View):
    def __init__(self, bot: commands.Bot, items: list):
        super().__init__(timeout=180)
        self.bot = bot
        self.items = {str(item['id']): item for item in items}
        self.selected_item_id = None

        self.select_menu = ItemActionSelect(items)
        self.add_item(self.select_menu)
        
        self.edit_button_item = ui.Button(label="Editar Item", style=ButtonStyle.primary, row=1, disabled=True)
        self.edit_button_item.callback = self.edit_button_callback
        self.add_item(self.edit_button_item)

        self.delete_button_item = ui.Button(label="Apagar Item", style=ButtonStyle.danger, row=1, disabled=True)
        self.delete_button_item.callback = self.delete_button_callback
        self.add_item(self.delete_button_item)

    def enable_buttons(self):
        self.edit_button_item.disabled = False
        self.delete_button_item.disabled = False

    async def edit_button_callback(self, interaction: Interaction):
        if self.selected_item_id is None:
            await interaction.response.send_message("Selecione um item primeiro.", ephemeral=True)
            return

        item_data = self.items.get(str(self.selected_item_id))
        modal = ItemModal(self.bot, item=item_data)
        await interaction.response.send_modal(modal)

    async def delete_button_callback(self, interaction: Interaction):
        if self.selected_item_id is None:
            await interaction.response.send_message("Selecione um item primeiro.", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
            self.bot.supabase_client.table("loja_items").delete().eq("id", self.selected_item_id).execute()
            await interaction.followup.send(f"🗑️ Item (ID: {self.selected_item_id}) foi apagado. A lista está desatualizada.", ephemeral=True)
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(view=self, content="Ação concluída.")
        except Exception as e:
            logging.error(f"Falha ao apagar item {self.selected_item_id}: {e}")
            await interaction.followup.send(f"❌ Erro ao apagar o item.", ephemeral=True)

# View para ser importada pelo painel de controle
class ShopManagerPanelView(ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None) # Removido timeout para persistência no painel
        self.bot = bot_instance
    
    @ui.button(label="Adicionar Novo Item", style=ButtonStyle.success, emoji="➕")
    async def add_item_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_modal(ItemModal(self.bot))

    @ui.button(label="Editar ou Apagar Item", style=ButtonStyle.secondary, emoji="📝")
    async def list_items_button(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            response = self.bot.supabase_client.table("loja_items").select("*").eq("guild_id", interaction.guild.id).order("name").execute()
            if not response.data:
                await interaction.followup.send("Nenhum item encontrado na loja.", ephemeral=True)
                return
            
            view = ItemActionView(self.bot, response.data)
            await interaction.followup.send("Selecione um item abaixo para escolher uma ação:", view=view, ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao listar itens da loja: {e}")
            await interaction.followup.send("Ocorreu um erro ao buscar os itens.", ephemeral=True)

class ShopManagerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gerenciar_loja", description="Adicionar, editar ou remover itens da loja do servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def gerenciar_loja(self, interaction: Interaction):
        await interaction.response.send_message("O que você gostaria de fazer?", view=ShopManagerPanelView(self.bot), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShopManagerCog(bot))

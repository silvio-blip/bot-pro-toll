
import discord
from discord.ext import commands
from discord import ui, Interaction, TextStyle
import logging
import datetime

# --- Modal de Configuração ---

class AutoRoleConfigModal(ui.Modal, title="Configurar Auto-Role"):
    def __init__(self, bot, config: dict = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config or {}

        enabled_value = "sim" if self.config.get("enabled") else "não"
        role_ids_str = ", ".join(map(str, self.config.get("role_ids", [])))
        
        self.add_item(ui.TextInput(label="Ativar sistema? (sim/não)", custom_id="enabled", default=enabled_value, max_length=3))
        self.add_item(ui.TextInput(label="IDs dos Cargos (separados por vírgula)", custom_id="role_ids", style=TextStyle.paragraph, default=role_ids_str, placeholder="Ex: 12345, 67890"))

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            role_ids_raw = self.children[1].value.strip()
            role_ids = []
            if role_ids_raw:
                role_ids = [int(r_id.strip()) for r_id in role_ids_raw.split(',') if r_id.strip().isdigit()]

            config_data = {
                "enabled": self.children[0].value.lower() == 'sim',
                "role_ids": role_ids
            }

            def update_settings(settings):
                settings['autorole'] = config_data

            success = await self.bot.get_and_update_server_settings(interaction.guild.id, update_settings)

            if success:
                await interaction.followup.send("✅ Configurações do Auto-Role salvas com sucesso!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Erro ao salvar as configurações.", ephemeral=True)

        except ValueError:
             await interaction.followup.send("❌ Erro ao salvar. Verifique se os IDs dos cargos são válidos e estão separados por vírgula.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro inesperado no on_submit do AutoRoleConfigModal: {e}")
            await interaction.followup.send("❌ Ocorreu um erro inesperado.", ephemeral=True)

# --- Cog Principal ---

class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_server_config(self, guild_id: int) -> dict:
        try:
            response = self.bot.supabase_client.table("server_configurations").select("settings").eq("server_guild_id", guild_id).execute()
            if response.data:
                return response.data[0].get('settings', {}).get('autorole', {})
        except Exception as e:
            logging.error(f"Erro ao buscar config de autorole para o servidor {guild_id}: {e}")
        return {}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot: return

        # --- FASE 1: Coleta de Dados para Gráfico de Crescimento ---
        try:
            self.bot.supabase_client.table("member_growth_stats").insert({
                "user_id": member.id,
                "guild_id": member.guild.id,
                "joined_at": datetime.datetime.utcnow().isoformat()
            }).execute()
            logging.info(f"[Crescimento] Membro {member.name} registrado no servidor {member.guild.name}.")
        except Exception as e:
            logging.error(f"[Crescimento] Falha ao registrar entrada do membro {member.name}: {e}")
        # ----------------------------------------------------------

        # Lógica original do Auto-Role
        config = await self.get_server_config(member.guild.id)
        if not config.get("enabled") or not config.get("role_ids"):
            return

        role_ids = config.get("role_ids", [])
        roles_to_add = []
        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role:
                if role < member.guild.me.top_role:
                    roles_to_add.append(role)
                else:
                    logging.warning(f"O cargo '{role.name}' (ID: {role_id}) está acima do cargo do bot no servidor {member.guild.id}. Não é possível adicioná-lo.")
            else:
                logging.warning(f"Cargo com ID {role_id} não encontrado no servidor {member.guild.id} para o Auto-Role.")
        
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Auto-Role automático na entrada.")
                logging.info(f"Cargos adicionados para {member.name} no servidor {member.guild.name}.")
            except discord.Forbidden:
                logging.error(f"Permissão negada para adicionar cargos (Auto-Role) no servidor {member.guild.id}.")
            except Exception as e:
                logging.error(f"Erro ao adicionar cargos via Auto-Role para {member.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))

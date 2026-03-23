
import discord
from discord import app_commands
from discord.ext import commands
import io
import aiohttp
from rembg import remove, new_session
from PIL import Image
import asyncio

class UtilidadesCog(commands.Cog, name="🔧 Utilidades"):
    def __init__(self, bot):
        self.bot = bot
        # Mantemos o melhor modelo para garantir a qualidade nos bastidores
        self.rembg_session = new_session("isnet-general-use") 

    @app_commands.command(
        name="remover_fundo",
        description="[🔧] Remove o fundo de uma imagem."
    )
    @app_commands.describe(
        imagem="Envie a imagem (PNG, JPG) para remover o fundo."
    )
    # Mantemos o cooldown, pois o processamento continua intenso
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def remover_fundo(self, interaction: discord.Interaction, imagem: discord.Attachment):
        
        if not imagem.content_type or not imagem.content_type.startswith('image/'):
            return await interaction.response.send_message(
                "❌ Por favor, envie um arquivo de imagem válido (PNG, JPG, JPEG).",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(imagem.url) as resp:
                    if resp.status != 200:
                        raise Exception("Falha ao baixar a imagem original.")
                    input_data = await resp.read()

            def process_image():
                # Configuração de máxima qualidade com pós-processamento para suavizar as bordas
                return remove(
                    input_data, 
                    session=self.rembg_session, 
                    post_process_mask=True, # Suaviza as bordas serrilhadas
                    alpha_matting=True, 
                    alpha_matting_foreground_threshold=270, # Refinamento do recorte
                    alpha_matting_background_threshold=20  # Refinamento do recorte
                )

            output_data = await asyncio.to_thread(process_image)

            output_image = io.BytesIO(output_data)
            output_image.seek(0)
            
            filename = f"removido_{interaction.user.id}_{int(interaction.created_at.timestamp())}.png"
            final_file = discord.File(fp=output_image, filename=filename)

            # Embed super simplificada, como solicitado
            embed = discord.Embed(
                title="✨ Fundo Removido!",
                description=f"**Imagem Original:** [Clique Aqui]({imagem.url})",
                color=0x2ecc71 # Verde Padrão
            )
            embed.set_image(url=f"attachment://{filename}")

            await interaction.followup.send(embed=embed, file=final_file)

        except Exception as e:
            self.bot.logger.error(f"Erro no comando remover_fundo: {e}")
            await interaction.followup.send(
                f"❌ Ocorreu um erro ao processar a imagem. Tente novamente mais tarde.",
                ephemeral=True
            )

    @remover_fundo.error
    async def remover_fundo_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ O processamento é intenso! Aguarde {error.retry_after:.1f} segundos.",
                ephemeral=True
            )

# Função obrigatória para carregar o Cog
async def setup(bot):
    await bot.add_cog(UtilidadesCog(bot))

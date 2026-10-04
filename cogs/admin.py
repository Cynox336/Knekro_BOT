import discord
from discord import app_commands
from discord.ext import commands

import database as db
import gachapon.gacha_logic as gacha

# -- Cog de Administración & Testeo --
class AdminCog(commands.Cog, name="Administración & Testeo"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -- Comando /reset --
    @app_commands.command(name="reset", description="[TESTING] Resetea tu perfil, inventario, pity y restablece tus MiniPeruanos")
    @app_commands.describe(gemas_iniciales="Cantidad de MiniPeruanos con los que empezar (por defecto 1600)")
    async def reset_cmd(self, interaction: discord.Interaction, gemas_iniciales: int = 1600):
        user_id = interaction.user.id
        await db.reset_user(user_id)
        if gemas_iniciales != 1600:
            await db.set_user_protogemas(user_id, max(0, gemas_iniciales))

        embed = discord.Embed(
            title="🔄 Perfil Reseteado con Éxito",
            description=(
                f"Se han restablecido todos los datos de **{interaction.user.display_name}** para testeo:\n\n"
                f"• 🇵🇪 **MiniPeruanos:** {gemas_iniciales:,}\n"
                f"• 🎯 **Pity 5★:** 0 / {gacha.MAX_PITY_5STAR}\n"
                f"• 🎲 **50/50:** Reiniciado a estado inicial\n"
                f"• 🎒 **Inventario:** Vaciado por completo\n"
                f"• 💳 **Tarjetazo:** Enfriamiento reiniciado (puedes usar `/tarjetazo` de nuevo)\n"
                f"• 🪙 **Mendigar:** Enfriamiento de 12h reiniciado"
            ),
            color=0xE74C3C
        )
        embed.set_footer(text="¡Listo para empezar a testear desde cero!")
        await interaction.response.send_message(embed=embed)

    # -- Comando /darperuanos --
    @app_commands.command(name="darperuanos", description="[TESTING] Añade MiniPeruanos a tu cuenta para probar tiradas masivas o apuestas")
    @app_commands.describe(cantidad="Número de MiniPeruanos a añadir (ej: 16000)")
    async def darperuanos_cmd(self, interaction: discord.Interaction, cantidad: int):
        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser mayor que 0.", ephemeral=True)
            return

        user_id = interaction.user.id
        await db.update_balance(user_id, cantidad)
        user_data = await db.get_or_create_user(user_id)

        embed = discord.Embed(
            title="🇵🇪 MiniPeruanos Añadidos (Modo Test)",
            description=f"Has recibido **+{cantidad:,} MiniPeruanos** 🇵🇪.\nNuevo saldo: **{user_data['protogemas']:,}** MiniPeruanos.",
            color=0x2ECC71
        )
        embed.set_footer(text="Usa /gachapon o /apuesta para ponerlos a prueba.")
        await interaction.response.send_message(embed=embed)

    # -- Comando /setpity --
    @app_commands.command(name="setpity", description="[TESTING] Ajusta tu contador de Pity para probar el 50/50 o el Hard Pity")
    @app_commands.describe(
        pity="Número de tiradas acumuladas (0 a 80)",
        asegurado="¿Tener el 50/50 asegurado para el promocional?"
    )
    @app_commands.choices(asegurado=[
        app_commands.Choice(name="Sí (Garantizado el 5★ promocional)", value=1),
        app_commands.Choice(name="No (50% de probabilidad de ganar/perder)", value=0)
    ])
    async def setpity_cmd(self, interaction: discord.Interaction, pity: int, asegurado: app_commands.Choice[int]):
        if pity < 0 or pity > gacha.MAX_PITY_5STAR:
            await interaction.response.send_message(
                f"❌ El pity debe estar entre 0 y {gacha.MAX_PITY_5STAR}.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        await db.set_user_pity(user_id, pity, asegurado.value)

        estado_garantizado = "✨ Garantizado" if asegurado.value == 1 else "🎲 50/50 en juego"
        embed = discord.Embed(
            title="🎯 Pity Ajustado (Modo Test)",
            description=(
                f"Pity 5★ establecido en: **{pity} / {gacha.MAX_PITY_5STAR}**\n"
                f"Estado del 50/50: **{estado_garantizado}**"
            ),
            color=0x9B59B6
        )
        embed.set_footer(text="Haz una tirada con /gachapon para comprobar el resultado inmediato.")
        await interaction.response.send_message(embed=embed)

    # -- Comando /dar_ticket --
    @app_commands.command(name="dar_ticket", description="[TESTING] Te otorga el objeto 'Añadir premio 5 estrellas' para probar /añadir_premio")
    async def dar_ticket_cmd(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        current = await db.get_item_count(user_id, gacha.TICKET_5STAR_NAME)
        if current >= 3:
            await interaction.response.send_message(
                f"❌ Ya tienes el máximo permitido (**{current}/3**) de tickets. Debes gastar uno con `/añadir_premio` antes de recibir más.",
                ephemeral=True
            )
            return

        await db.add_pull_to_inventory(user_id, gacha.TICKET_5STAR_NAME, rarity=5)
        nuevo_total = current + 1
        embed = discord.Embed(
            title="🎫 Ticket 5★ Concedido (Modo Test)",
            description=(
                f"Se te ha otorgado el objeto **{gacha.TICKET_5STAR_NAME}**.\n"
                f"Total en tu inventario: **{nuevo_total}/3**.\n\n"
                f"👉 Ahora puedes usar `/añadir_premio` para crear un nuevo premio 5★."
            ),
            color=0xF39C12
        )
        embed.set_footer(text="Usa /añadir_premio para canjearlo.")
        await interaction.response.send_message(embed=embed)

# -- Setup --
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))

import random
import discord
from discord import app_commands
from discord.ext import commands

import database as db
import gachapon.gacha_logic as gacha

# -- Cog de Economía --
class EconomyCog(commands.Cog, name="Economía"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -- Comando /perfil --
    @app_commands.command(name="perfil", description="Consulta tus MiniPeruanos, tu pity acumulado y tu 50/50")
    async def perfil_cmd(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_data = await db.get_or_create_user(user_id)
        tickets = await db.get_item_count(user_id, gacha.TICKET_5STAR_NAME)

        pity_5 = user_data["pity_5star"]
        guaranteed = user_data["guaranteed_5star"]
        balance = user_data["protogemas"]
        total = user_data["total_pulls"]
        lost_5050 = user_data.get("lost_5050_count", 0)

        guaranteed_status = "✨ **ASEGURADO** (El próximo 5★ será el promocional)" if guaranteed else "🎲 **50/50 ACTIVO** (50% de ganar o perder)"

        embed = discord.Embed(
            title=f"📊 Perfil de Ludópata: {interaction.user.display_name}",
            color=0x3498DB
        )
        embed.add_field(name="🇵🇪 MiniPeruanos", value=f"**{balance:,}**", inline=True)
        embed.add_field(name="🎯 Pity 5★ Actual", value=f"**{pity_5}** / {gacha.MAX_PITY_5STAR}", inline=True)
        embed.add_field(name="🎫 Tickets Premio 5★", value=f"**{tickets}** / 3", inline=True)
        embed.add_field(name="📜 Tiradas Totales", value=f"**{total}**", inline=True)
        embed.add_field(name="💀 50/50 Perdidos", value=f"**{lost_5050}**", inline=True)
        embed.add_field(name="⚖️ Estado del 50/50", value=guaranteed_status, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="¿Sin fondos? Usa /tarjetazo o /mendigar si estás arruinado.")

        await interaction.response.send_message(embed=embed)

    # -- Comando /tarjetazo --
    @app_commands.command(name="tarjetazo", description="Pasa la tarjeta de crédito y reclama tus 1600 MiniPeruanos (cada 12h)")
    async def tarjetazo_cmd(self, interaction: discord.Interaction):
        success, message = await db.claim_daily(interaction.user.id, cooldown_hours=12)
        if success:
            embed = discord.Embed(title="💳 ¡Tarjetazo Bancario Aprobado!", description=message, color=0x2ECC71)
            embed.set_footer(text="KNekro dice: '¡Métele 50 pavos más, no pasa nada!'")
        else:
            embed = discord.Embed(title="⏳ Tarjeta Rechazada (Enfriamiento)", description=message, color=0xE67E22)
        await interaction.response.send_message(embed=embed)

    # -- Comando /mendigar --
    @app_commands.command(name="mendigar", description="Pídele limosna a KNekro si te has quedado sin MiniPeruanos (cada 1h 30m)")
    async def mendigar_cmd(self, interaction: discord.Interaction):
        success, status, message = await db.claim_mendigar(interaction.user.id, amount=160, cooldown_minutes=90)

        if status == "NOT_POOR":
            await interaction.response.send_message(message, ephemeral=True)
            return

        if status == "COOLDOWN":
            embed = discord.Embed(
                title="⏳ ¡A Trabajar, Flojo!",
                description=message,
                color=0xE67E22
            )
            embed.set_footer(text="KNekro dice: 'No soy una ONG, vuelve más tarde.'")
            await interaction.response.send_message(embed=embed)
            return

        frases_mendigo = [
            "Venga, toma 160 MiniPeruanos... pero no te los gastes en porquerías, chaval.",
            "Te veo muy mal. Toma una tiradita de compasión. ¡Que no se diga que soy mala gente!",
            "La casa de apuestas te da un empujoncito. 160 MiniPeruanos directos a tu cuenta.",
            "Te doy esto para que tires, pero como te salga un garrote del debate me voy a reír en tu cara."
        ]
        embed = discord.Embed(
            title="🪙 Limosna de Emergencia",
            description=f"*{random.choice(frases_mendigo)}*\n\n{message}",
            color=0xF39C12
        )
        embed.set_footer(text="Solo puedes mendigar una vez cada 1 hora y 30 minutos.")
        await interaction.response.send_message(embed=embed)

    # -- Comando /apuesta --
    @app_commands.command(name="apuesta", description="Apuesta tus MiniPeruanos en la ruleta ficticia para duplicarlos o perderlo todo")
    @app_commands.describe(
        cantidad="Número de MiniPeruanos a apostar",
        opcion="Elige a qué apostar: Rojo, Negro, Verde (x14) o Cara/Cruz"
    )
    @app_commands.choices(opcion=[
        app_commands.Choice(name="🔴 Rojo (x2)", value="rojo"),
        app_commands.Choice(name="⚫ Negro (x2)", value="negro"),
        app_commands.Choice(name="🟢 Verde / 0 (x14 - ¡Riesgo extremo!)", value="verde"),
        app_commands.Choice(name="🪙 Cara (x1.5)", value="cara"),
        app_commands.Choice(name="🪙 Cruz (x1.5)", value="cruz")
    ])
    async def apuesta_cmd(self, interaction: discord.Interaction, cantidad: int, opcion: app_commands.Choice[str]):
        if cantidad <= 0:
            await interaction.response.send_message("❌ Debes apostar al menos 1 MiniPeruano.", ephemeral=True)
            return

        user_data = await db.get_or_create_user(interaction.user.id)
        if user_data["protogemas"] < cantidad:
            await interaction.response.send_message(
                f"❌ No tienes suficientes MiniPeruanos. Tienes **{user_data['protogemas']}**.",
                ephemeral=True
            )
            return

        eleccion = opcion.value

        if eleccion in ["cara", "cruz"]:
            won = (random.random() < 0.38)
            multiplier = 1.5
            if won:
                outcome = eleccion
                roll_desc = f"La moneda cayó en **{outcome.upper()}** 🪙"
            else:
                if random.random() < 0.08:
                    roll_desc = "¡La moneda cayó de canto y rodó hacia la alcantarilla! 🪙"
                    outcome = "canto"
                else:
                    outcome = "cruz" if eleccion == "cara" else "cara"
                    roll_desc = f"La moneda cayó en **{outcome.upper()}** 🪙"
        elif eleccion == "verde":
            won = (random.random() < (1 / 35))
            multiplier = 14
            if won:
                wheel_num = 0
                outcome = "verde"
            else:
                wheel_num = random.randint(1, 36)
                outcome = "rojo" if wheel_num % 2 == 0 else "negro"
            roll_desc = f"La bola de la ruleta cayó en el **{wheel_num} ({outcome.upper()})** 🎡"
        else:
            won = (random.random() < 0.20)
            multiplier = 2
            if won:
                outcome = eleccion
                numeros_validos = [n for n in range(1, 37) if (n % 2 == 0 if outcome == "rojo" else n % 2 != 0)]
                wheel_num = random.choice(numeros_validos)
            else:
                if random.random() < 0.12:
                    wheel_num = 0
                    outcome = "verde"
                else:
                    outcome = "negro" if eleccion == "rojo" else "rojo"
                    numeros_validos = [n for n in range(1, 37) if (n % 2 == 0 if outcome == "rojo" else n % 2 != 0)]
                    wheel_num = random.choice(numeros_validos)
            roll_desc = f"La bola de la ruleta cayó en el **{wheel_num} ({outcome.upper()})** 🎡"

        if won:
            ganancia_neta = max(1, int(round(cantidad * (multiplier - 1))))
            await db.update_balance(interaction.user.id, ganancia_neta)
            nuevo_saldo = user_data["protogemas"] + ganancia_neta
            total_recibido = cantidad + ganancia_neta
            embed = discord.Embed(
                title="🤑 ¡¡HAS GANADO LA APUESTA!!",
                description=(
                    f"{roll_desc}\n\n"
                    f"Apostaste a: **{eleccion.upper()}** ({multiplier}x)\n"
                    f"Ganancia: **+{total_recibido:,} MiniPeruanos** 🎉\n"
                    f"Nuevo saldo: **{nuevo_saldo:,}** MiniPeruanos"
                ),
                color=0x2ECC71
            )
            embed.set_footer(text="¡KNekro dice: '¡Así se hace, chavales, el casino paga!'")
        else:
            await db.update_balance(interaction.user.id, -cantidad)
            nuevo_saldo = user_data["protogemas"] - cantidad
            embed = discord.Embed(
                title="💀 HAS PERDIDO LA APUESTA...",
                description=(
                    f"{roll_desc}\n\n"
                    f"Apostaste a: **{eleccion.upper()}**\n"
                    f"Perdiste: **-{cantidad} MiniPeruanos** 💸\n"
                    f"Nuevo saldo: **{nuevo_saldo:,}** MiniPeruanos"
                ),
                color=0xE74C3C
            )
            embed.set_footer(text="¡KNekro dice: 'La casa siempre gana... a dormir con el rabo entre las piernas.'")

        await interaction.response.send_message(embed=embed)

# -- Setup --
async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))

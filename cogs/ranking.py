import random
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from gachapon.quotes import KNEKRO_QUOTES_LOST_5050

# -- Cog de Rankings --
class RankingCog(commands.Cog, name="Rankings"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -- Comando /top --
    @app_commands.command(name="top", description="Ranking de los usuarios más ricos y adictos al gacha")
    async def top_cmd(self, interaction: discord.Interaction):
        leaders = await db.get_leaderboard(limit=10)
        if not leaders:
            await interaction.response.send_message("Aún no hay datos suficientes para el ranking.", ephemeral=True)
            return

        lines = []
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, user in enumerate(leaders):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            member = interaction.guild.get_member(user["user_id"]) if interaction.guild else None
            name = f"**{member.display_name}**" if member else f"<@{user['user_id']}>"
            lines.append(f"{medal} {name} — 🇵🇪 {user['protogemas']:,} MiniPeruanos | 🎯 {user['total_pulls']} tiradas")

        embed = discord.Embed(
            title="🏆 Salón de la Fama de la Ludopatía",
            description="\n".join(lines),
            color=0xF39C12
        )
        await interaction.response.send_message(embed=embed)

    # -- Comando /ranking --
    @app_commands.command(name="ranking", description="Rankings del servidor: más tiradas, más 50/50 perdidos y más 5 estrellas")
    @app_commands.describe(categoria="Elige la categoría del ranking a consultar")
    @app_commands.choices(categoria=[
        app_commands.Choice(name="🌟 Resumen General (Top 3 de cada categoría)", value="general"),
        app_commands.Choice(name="🎰 Más Tiradas Realizadas (Top 10)", value="tiradas"),
        app_commands.Choice(name="💀 Más 50/50 Perdidos / Maldición Qiqi (Top 10)", value="perdidos_5050"),
        app_commands.Choice(name="⭐ Más 5 Estrellas Obtenidos (Top 10)", value="cinco_estrellas"),
    ])
    async def ranking_cmd(self, interaction: discord.Interaction, categoria: app_commands.Choice[str] = None):
        cat = categoria.value if categoria else "general"
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        if cat == "general":
            top_pulls = await db.get_ranking_pulls(limit=3)
            top_lost = await db.get_ranking_lost_5050(limit=3)
            top_5stars = await db.get_ranking_five_stars(limit=3)

            embed = discord.Embed(
                title="🏆 RANKINGS DEL SERVIDOR: Cuadro de Honor y Desgracias",
                description="Aquí tienes a los mayores ludópatas, a los más desgraciados y a los más suertudos de la comunidad:\n",
                color=0xF1C40F
            )

            if top_pulls:
                lines_pulls = [
                    f"{medals[i]} <@{u['user_id']}> — **{u['total_pulls']}** tiradas"
                    for i, u in enumerate(top_pulls)
                ]
                embed.add_field(name="🎰 Más Tiradas Realizadas", value="\n".join(lines_pulls), inline=False)
            else:
                embed.add_field(name="🎰 Más Tiradas Realizadas", value="*Nadie ha tirado aún al gachapón.*", inline=False)

            if top_lost:
                lines_lost = [
                    f"{medals[i]} <@{u['user_id']}> — **{u['lost_5050_count']}** veces perdidas 💀"
                    for i, u in enumerate(top_lost)
                ]
                embed.add_field(name="💀 Más 50/50 Perdidos (Maldición de Qiqi)", value="\n".join(lines_lost), inline=False)
            else:
                embed.add_field(name="💀 Más 50/50 Perdidos (Maldición de Qiqi)", value="*Nadie ha perdido un 50/50 todavía.*", inline=False)

            if top_5stars:
                lines_5stars = [
                    f"{medals[i]} <@{u['user_id']}> — **{u['total_5stars']}** objetos 5★ ⭐"
                    for i, u in enumerate(top_5stars)
                ]
                embed.add_field(name="⭐ Más 5 Estrellas en Inventario", value="\n".join(lines_5stars), inline=False)
            else:
                embed.add_field(name="⭐ Más 5 Estrellas en Inventario", value="*Nadie posee objetos 5 estrellas todavía.*", inline=False)

            embed.set_footer(text="💡 Usa /ranking categoria:[opción] para ver el Top 10 completo de una categoría.")
            await interaction.response.send_message(embed=embed)
            return

        elif cat == "tiradas":
            top = await db.get_ranking_pulls(limit=10)
            if not top:
                await interaction.response.send_message("📊 Aún no hay tiradas registradas.", ephemeral=True)
                return

            lines = [
                f"{medals[i] if i < len(medals) else f'{i+1}.'} <@{u['user_id']}> — **{u['total_pulls']}** tiradas"
                for i, u in enumerate(top)
            ]
            embed = discord.Embed(
                title="🎰 Ranking: Más Tiradas al Gachapón (Top 10)",
                description="\n".join(lines),
                color=0x3498DB
            )
            embed.set_footer(text="El vicio no tiene límites.")
            await interaction.response.send_message(embed=embed)
            return

        elif cat == "perdidos_5050":
            top = await db.get_ranking_lost_5050(limit=10)
            if not top:
                await interaction.response.send_message("💀 ¡Increíble! Nadie en el servidor ha perdido un 50/50 todavía.", ephemeral=True)
                return

            lines = [
                f"{medals[i] if i < len(medals) else f'{i+1}.'} <@{u['user_id']}> — **{u['lost_5050_count']}** derrotas del 50/50 🧟"
                for i, u in enumerate(top)
            ]
            embed = discord.Embed(
                title="💀 Ranking: Los Más Desgraciados en el 50/50 (Top 10)",
                description=f"*{random.choice(KNEKRO_QUOTES_LOST_5050)}*\n\n" + "\n".join(lines),
                color=0xE74C3C
            )
            embed.set_footer(text="Un minuto de silencio por estos soldados caídos.")
            await interaction.response.send_message(embed=embed)
            return

        elif cat == "cinco_estrellas":
            top = await db.get_ranking_five_stars(limit=10)
            if not top:
                await interaction.response.send_message("⭐ Nadie posee objetos 5 estrellas todavía en su inventario.", ephemeral=True)
                return

            lines = [
                f"{medals[i] if i < len(medals) else f'{i+1}.'} <@{u['user_id']}> — **{u['total_5stars']}** objetos 5★ ✨"
                for i, u in enumerate(top)
            ]
            embed = discord.Embed(
                title="⭐ Ranking: Más 5 Estrellas en Inventario (Top 10)",
                description="\n".join(lines),
                color=0xFFD700
            )
            embed.set_footer(text="¡Los bendecidos por KNekro y el algoritmo!")
            await interaction.response.send_message(embed=embed)
            return

# -- Setup --
async def setup(bot: commands.Bot):
    await bot.add_cog(RankingCog(bot))

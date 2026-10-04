import random
import discord
from discord import app_commands
from discord.ext import commands

import database as db
import gachapon.gacha_logic as gacha
import gachapon.gacha_pool as gacha_pool
from gachapon.gacha_pool import PROMOTIONAL_5STAR
from gachapon.quotes import (
    KNEKRO_QUOTES_5STAR,
    KNEKRO_QUOTES_LOST_5050,
    KNEKRO_QUOTES_TRASH
)

# -- Selector de Inventario --
class InventorySelect(discord.ui.Select):
    def __init__(self, items: list, custom_prizes: list):
        options = []
        for it in items[:25]:
            detail = gacha_pool.find_item_details(it["item_name"], custom_prizes)
            desc_text = detail.get("description", "") if detail else ""
            if len(desc_text) > 90:
                desc_text = desc_text[:87] + "..."
            options.append(discord.SelectOption(
                label=it["item_name"][:100],
                description=desc_text if desc_text else f"Rareza: {it['rarity']}★ | x{it['count']}",
                value=it["item_name"][:100]
            ))
        super().__init__(
            placeholder="🔍 Selecciona un objeto para leer su lore y descripción...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.custom_prizes = custom_prizes

    async def callback(self, interaction: discord.Interaction):
        chosen_name = self.values[0]
        item = gacha_pool.find_item_details(chosen_name, self.custom_prizes)
        if not item:
            await interaction.response.send_message("❌ No se encontró información para este objeto.", ephemeral=True)
            return

        count = await db.get_item_count(interaction.user.id, chosen_name)
        rarity_stars = "⭐" * item["rarity"]
        color = 0xFFD700 if item["rarity"] == 5 else (0x9B59B6 if item["rarity"] == 4 else 0x3498DB)

        card = discord.Embed(
            title=f"{rarity_stars} {item['name']}",
            description=f"*{item.get('description', 'Sin descripción.')}*",
            color=color
        )
        card.add_field(name="🎒 Cantidad en tu Inventario", value=f"**x{count}** {'👑 (C6 MÁX)' if count >= 6 else ''}", inline=True)
        if "creator_id" in item and item["creator_id"]:
            card.add_field(name="🛠️ Creado por", value=f"<@{item['creator_id']}>", inline=True)

        await interaction.response.send_message(embed=card, ephemeral=True)

# -- Vista de Inventario --
class InventoryView(discord.ui.View):
    def __init__(self, items: list, custom_prizes: list):
        super().__init__(timeout=180)
        self.add_item(InventorySelect(items, custom_prizes))

# -- Cog de Gachapón --
class GachaCog(commands.Cog, name="Gachapón"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -- Comando /banner --
    @app_commands.command(name="banner", description="Muestra el banner promocional activo y los detalles del gacha")
    async def banner_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎰 BANNER PROMOCIONAL: El Despertar del Titán",
            description=(
                f"**Personaje 5★ Destacado:** {PROMOTIONAL_5STAR['name']}\n"
                f"*{PROMOTIONAL_5STAR['description']}*\n\n"
                "**Mecánicas y Probabilidades:**\n"
                "• Coste: **160 MiniPeruanos** por tirada.\n"
                "• **5★ Base:** 0.6% | **Soft Pity:** a partir de la tirada 60.\n"
                "• **Hard Pity:** Tirada 80 garantizada al 100%.\n"
                "• **Sistema 50/50:** Si sacas un 5★ y no tienes asegurado, hay 50% de probabilidad de ganar al Titán o 50% de perderlo con Qiqi u otros memes.\n"
                "• **🎫 Objeto Especial 5★:** Puedes conseguir *'Añadir premio 5 estrellas'* (máx 3 acumulables) para usar `/añadir_premio` y crear un nuevo premio para el servidor.\n"
                "• **4★ Garantizado:** Mínimo un 4★ cada 10 tiradas."
            ),
            color=0xFFD700
        )
        embed.set_footer(text="Usa /gachapon para tirar o /perfil para ver tu pity.")
        await interaction.response.send_message(embed=embed)

    # -- Comando /gachapon --
    @app_commands.command(name="gachapon", description="Tira al gachapón (1 tirada = 160 MiniPeruanos | 10 tiradas = 1600 MiniPeruanos)")
    @app_commands.describe(cantidad="Selecciona si quieres tirar 1 o 10 tiradas")
    @app_commands.choices(cantidad=[
        app_commands.Choice(name="1 Tirada (160 MiniPeruanos)", value=1),
        app_commands.Choice(name="10 Tiradas - Multi (1600 MiniPeruanos)", value=10),
    ])
    async def gachapon_cmd(self, interaction: discord.Interaction, cantidad: app_commands.Choice[int]):
        num_pulls = cantidad.value
        cost = num_pulls * gacha.WISH_COST
        user_id = interaction.user.id

        user_data = await db.get_or_create_user(user_id)
        if user_data["protogemas"] < cost:
            await interaction.response.send_message(
                f"❌ **No tienes suficientes MiniPeruanos.**\nNecesitas **{cost}** y tienes **{user_data['protogemas']}**.\n"
                f"👉 Usa `/tarjetazo` para recargar o `/apuesta` para jugártela.",
                ephemeral=True
            )
            return

        user_tickets = await db.get_item_count(user_id, gacha.TICKET_5STAR_NAME)
        custom_5stars = await db.get_all_custom_prizes()

        results, new_pity_5, new_pity_4, new_guaranteed, final_tickets = gacha.simulate_pulls(
            count=num_pulls,
            initial_pity_5=user_data["pity_5star"],
            initial_pity_4=user_data["pity_4star"],
            initial_guaranteed=user_data["guaranteed_5star"],
            current_tickets=user_tickets,
            custom_5stars=custom_5stars
        )

        lost_5050_events = sum(1 for res in results if res.get("event_type") == "5STAR_LOST_5050")

        await db.update_user_gacha_state(
            user_id=user_id,
            pity_5star=new_pity_5,
            pity_4star=new_pity_4,
            guaranteed_5star=new_guaranteed,
            pulls_done=num_pulls,
            protogemas_spent=cost,
            lost_5050_inc=lost_5050_events
        )

        total_refund = 0
        for res in results:
            item = res["item"]
            refund = await db.add_pull_to_inventory(user_id, item["name"], item["rarity"])
            res["refund"] = refund
            total_refund += refund

        max_rarity = max(res["item"]["rarity"] for res in results)
        five_star_events = [res["event_type"] for res in results if res["item"]["rarity"] == 5]

        quote = ""
        if max_rarity == 5:
            color = 0xFFD700
            if any("LOST_5050" in ev for ev in five_star_events):
                quote = f"🤬 **KNekro grita:** *\"{random.choice(KNEKRO_QUOTES_LOST_5050)}\"*"
            else:
                quote = f"🌟 **KNekro celebra:** *\"{random.choice(KNEKRO_QUOTES_5STAR)}\"*"
        elif max_rarity == 4:
            color = 0x9B59B6
            quote = "💜 ¡Al menos cayó un 4 estrellas!"
        else:
            color = 0x3498DB
            quote = f"💧 **KNekro suspira:** *\"{random.choice(KNEKRO_QUOTES_TRASH)}\"*"

        lines = []
        ticket_drawn = False
        for res in results:
            it = res["item"]
            ref = res.get("refund", 0)
            ref_text = f" ♻️ *(C6: +{ref} MiniPeruanos)*" if ref > 0 else ""
            desc = it.get("description", "")
            desc_line = f"\n↳ *{desc}*" if desc else ""

            if it["name"] == gacha.TICKET_5STAR_NAME:
                ticket_drawn = True
                lines.append(f"🎫 **[5★ ESPECIAL]** **{it['name']}** 🌟{desc_line}")
            elif it["rarity"] == 5:
                lines.append(f"⭐ **[5★]** **{it['name']}**{ref_text} 🎉{desc_line}")
            elif it["rarity"] == 4:
                lines.append(f"⭐ **[4★]** **{it['name']}**{ref_text}{desc_line}")
            else:
                lines.append(f"▫️ [3★] {it['name']}{desc_line}")

        result_text = "\n".join(lines)

        embed = discord.Embed(
            title=f"💫 ¡Tirada de Gachapón ({num_pulls}) de {interaction.user.display_name}!",
            description=f"{quote}\n\n{result_text}",
            color=color
        )
        embed.add_field(name="🎯 Pity 5★ actual", value=f"{new_pity_5} / {gacha.MAX_PITY_5STAR}", inline=True)
        embed.add_field(
            name="⚖️ 50/50",
            value="✨ Garantizado" if new_guaranteed else "🎲 En juego",
            inline=True
        )
        final_balance = user_data['protogemas'] - cost + total_refund
        embed.add_field(name="🇵🇪 Saldo restante", value=f"{final_balance:,} MiniPeruanos", inline=True)

        if total_refund > 0:
            embed.add_field(
                name="♻️ Reembolso por C6 Máximo",
                value=f"Has recibido **+{total_refund} MiniPeruanos** de vuelta por copias de personajes/objetos que ya tienes al nivel máximo (6 copias).",
                inline=False
            )

        if ticket_drawn:
            embed.add_field(
                name="🎫 ¡HAS OBTENIDO: AÑADIR PREMIO 5 ESTRELLAS!",
                value=(
                    f"¡Felicidades! Tienes **{final_tickets}/3** tickets acumulados.\n"
                    f"👉 Puedes usar `/añadir_premio` para crear un nuevo premio 5★ e incluirlo en el Gachapón del servidor."
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # -- Comando /inventario --
    @app_commands.command(name="inventario", description="Revisa tu colección de personajes y objetos conseguidos")
    async def inventario_cmd(self, interaction: discord.Interaction):
        items = await db.get_user_inventory(interaction.user.id)
        if not items:
            await interaction.response.send_message(
                "🎒 Tu inventario está totalmente vacío. ¡Usa `/gachapon` para empezar a coleccionar!",
                ephemeral=True
            )
            return

        fives = [it for it in items if it["rarity"] == 5]
        fours = [it for it in items if it["rarity"] == 4]
        threes = [it for it in items if it["rarity"] == 3]

        embed = discord.Embed(
            title=f"🎒 Inventario de {interaction.user.display_name}",
            color=0xF1C40F
        )

        if fives:
            formatted_fives = []
            for it in fives:
                c_text = "x6 👑 *(C6 MÁX)*" if it["count"] >= 6 else f"x{it['count']}"
                formatted_fives.append(f"• **{it['item_name']}** {c_text}")
            embed.add_field(name="🌟 5 Estrellas (Legendarios)", value="\n".join(formatted_fives), inline=False)
        else:
            embed.add_field(name="🌟 5 Estrellas (Legendarios)", value="*Ninguno todavía... la suerte te esquiva.*", inline=False)

        if fours:
            formatted_fours = []
            for it in fours[:8]:
                c_text = "x6 👑 *(C6 MÁX)*" if it["count"] >= 6 else f"x{it['count']}"
                formatted_fours.append(f"• **{it['item_name']}** {c_text}")
            text_4 = "\n".join(formatted_fours)
            if len(fours) > 8:
                text_4 += f"\n*...y {len(fours) - 8} más*"
            embed.add_field(name="💜 4 Estrellas (Épicos)", value=text_4, inline=False)

        total_items = sum(it["count"] for it in items)
        embed.set_footer(text=f"Total de objetos: {total_items} | Usa el menú de abajo o /objeto para leer descripciones.")

        custom_prizes = await db.get_all_custom_prizes()
        view = InventoryView(items, custom_prizes)
        await interaction.response.send_message(embed=embed, view=view)

    # -- Comando /objeto --
    @app_commands.command(name="objeto", description="Consulta los detalles, historia y descripción de cualquier objeto")
    @app_commands.describe(nombre="Escribe o selecciona el nombre del objeto a consultar")
    async def objeto_cmd(self, interaction: discord.Interaction, nombre: str):
        custom_prizes = await db.get_all_custom_prizes()
        item = gacha_pool.find_item_details(nombre, custom_prizes)
        if not item:
            await interaction.response.send_message(
                f"❌ No se encontró ningún objeto llamado **{nombre}**.\n"
                f"💡 Empieza a escribir el nombre del objeto en el comando para ver las sugerencias de autocompletado.",
                ephemeral=True
            )
            return

        user_count = await db.get_item_count(interaction.user.id, item["name"])
        rarity_stars = "⭐" * item["rarity"]
        color = 0xFFD700 if item["rarity"] == 5 else (0x9B59B6 if item["rarity"] == 4 else 0x3498DB)

        embed = discord.Embed(
            title=f"{rarity_stars} {item['name']}",
            description=f"*{item.get('description', 'Sin descripción.')}*",
            color=color
        )
        embed.add_field(name="⭐ Rareza", value=f"{item['rarity']} Estrellas ({rarity_stars})", inline=True)

        status_text = f"**x{user_count}** en tu inventario {'👑 (C6 Máximo)' if user_count >= 6 else ''}" if user_count > 0 else "❌ No lo tienes aún"
        embed.add_field(name="🎒 En tu Colección", value=status_text, inline=True)

        if "creator_id" in item and item["creator_id"]:
            embed.add_field(name="🛠️ Creador de la Comunidad", value=f"<@{item['creator_id']}>", inline=False)

        embed.set_footer(text="¡Tira en /gachapon para conseguirlo o sumar más copias!")
        await interaction.response.send_message(embed=embed)

    @objeto_cmd.autocomplete("nombre")
    async def objeto_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        custom_prizes = await db.get_all_custom_prizes()
        catalog = gacha_pool.get_all_items_catalog(custom_prizes)
        choices = []
        current_lower = current.strip().lower()

        for it in catalog:
            if not current_lower or current_lower in it["name"].lower():
                choices.append(app_commands.Choice(name=it["name"][:100], value=it["name"][:100]))
                if len(choices) >= 25:
                    break
        return choices

    # -- Comando /añadir_premio --
    @app_commands.command(name="añadir_premio", description="Crea un objeto 5★ e inclúyelo en el Gachapón (Requiere tener el ticket 5★)")
    @app_commands.describe(
        nombre="Nombre del personaje u objeto 5★ personalizado",
        descripcion="Descripción graciosa o épica del objeto"
    )
    async def anadir_premio_cmd(self, interaction: discord.Interaction, nombre: str, descripcion: str):
        user_id = interaction.user.id
        tickets = await db.get_item_count(user_id, gacha.TICKET_5STAR_NAME)

        if tickets <= 0:
            await interaction.response.send_message(
                "❌ **No tienes el objeto 'Añadir premio 5 estrellas'.**\n"
                "👉 Este objeto legendario solo se consigue teniendo suerte en `/gachapon`.\n"
                "¡Tira al gachapón hasta que te toque como 5★ para desbloquear esta opción!",
                ephemeral=True
            )
            return

        consumed = await db.consume_item(user_id, gacha.TICKET_5STAR_NAME, amount=1)
        if not consumed:
            await interaction.response.send_message("❌ Error al procesar tu ticket. Inténtalo de nuevo.", ephemeral=True)
            return

        remaining = tickets - 1
        clean_nombre = nombre.strip()
        clean_desc = descripcion.strip()
        await db.add_custom_prize(user_id, clean_nombre, clean_desc)

        embed = discord.Embed(
            title="🌟 ¡NUEVO PREMIO 5★ AÑADIDO AL GACHAPÓN!",
            description=(
                f"**{interaction.user.display_name}** ha usado su **Ticket 5 Estrellas** y ha añadido un nuevo objeto al pool del bot:\n\n"
                f"✨ **[5★] {clean_nombre}**\n"
                f"*{clean_desc}*\n\n"
                f"🎉 **¡A partir de ahora, cualquier persona del servidor puede sacarlo al tirar en `/gachapon`!**"
            ),
            color=0xFFD700
        )
        embed.set_footer(text=f"Te quedan {remaining}/3 tickets de premio disponibles.")
        await interaction.response.send_message(embed=embed)

    # -- Comando /premios_comunidad --
    @app_commands.command(name="premios_comunidad", description="Ver todos los objetos 5★ creados por los usuarios en el Gachapón")
    async def premios_comunidad_cmd(self, interaction: discord.Interaction):
        prizes = await db.get_all_custom_prizes()
        if not prizes:
            await interaction.response.send_message(
                "📜 Aún no hay premios 5★ creados por la comunidad.\n¡Sé el primero consiguiendo un ticket en `/gachapon`!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🏆 Premios 5★ Creados por la Comunidad",
            description=f"Actualmente hay **{len(prizes)}** objeto(s) 5★ creados por usuarios en el pool de `/gachapon`:\n",
            color=0xF1C40F
        )

        for p in prizes[:10]:
            embed.add_field(
                name=f"⭐ {p['name']}",
                value=f"{p['description']}\n*Creado por:* <@{p['creator_id']}>",
                inline=False
            )

        if len(prizes) > 10:
            embed.set_footer(text=f"...y {len(prizes) - 10} premios más en el pool.")

        await interaction.response.send_message(embed=embed)

    # -- Comando /help_gacha --
    @app_commands.command(name="help_gacha", description="Muestra la lista de todos los comandos disponibles y cómo utilizarlos")
    async def help_gacha_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎰 Guía de Comandos — KNekro BOT",
            description=(
                "¡Bienvenido al simulador oficial de ludopatía y copium con KNekro!\n"
                "Aquí tienes todos los comandos disponibles organizados por categoría:"
            ),
            color=0xF1C40F
        )

        embed.add_field(
            name="🎰 Gachapón & Colección",
            value=(
                "• **`/gachapon [1 o 10]`** — Tira al gacha (160 / 1.600 MiniPeruanos) con descripciones cómicas.\n"
                "• **`/banner`** — Consulta el 5★ promocional activo, probabilidades y estado del banner.\n"
                "• **`/inventario`** — Revisa tu colección con selector interactivo para leer el lore de tus objetos.\n"
                "• **`/objeto [nombre]`** — Ficha completa de cualquier objeto (historia, rareza y copias que posees).\n"
                "• **`/añadir_premio`** — Canjea un Ticket 5★ para crear un nuevo premio legendario en el servidor.\n"
                "• **`/premios_comunidad`** — Lista de premios 5★ creados por los miembros de la comunidad."
            ),
            inline=False
        )

        embed.add_field(
            name="💳 Economía & Apuestas",
            value=(
                "• **`/tarjetazo`** — Reclama 1.600 MiniPeruanos diarios (1 multi gratis al día).\n"
                "• **`/perfil`** — Consulta tu balance, pity acumulado (5★/4★), estado del 50/50 y derrotas ante Qiqi.\n"
                "• **`/apuesta [cantidad] [opción]`** — Apuesta en la Ruleta (Rojo, Negro, Verde x14) o a Cara/Cruz.\n"
                "• **`/mendigar`** — Pide limosna de emergencia a KNekro si estás en la quiebra (<160 MiniPeruanos, cada 12h)."
            ),
            inline=False
        )

        embed.add_field(
            name="🏆 Salón de la Fama y Desgracias",
            value=(
                "• **`/top`** — Podio de los mayores millonarios en MiniPeruanos del servidor.\n"
                "• **`/ranking [categoría]`** — Ránking de más tiradas, más 50/50 perdidos (Qiqi) o más 5 estrellas."
            ),
            inline=False
        )

        embed.set_footer(text="💡 Consejo: Pasa tu /tarjetazo cada día para conseguir 1600 MiniPeruanos gratis.")
        await interaction.response.send_message(embed=embed)

# -- Setup --
async def setup(bot: commands.Bot):
    await bot.add_cog(GachaCog(bot))

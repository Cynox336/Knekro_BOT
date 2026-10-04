import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import database as db

# -- Configuración & Variables --
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

# -- Inicialización del Bot --
class KnekroGachaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db.init_db()

        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        if os.path.exists(cogs_dir):
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    extension_name = f"cogs.{filename[:-3]}"
                    try:
                        await self.load_extension(extension_name)
                        print(f"📦 Extensión cargada con éxito: {extension_name}")
                    except Exception as e:
                        print(f"❌ Error al cargar extensión {extension_name}: {e}")

        try:
            synced = await self.tree.sync()
            print(f"✅ Sincronizados {len(synced)} comandos slash globalmente.")
        except Exception as e:
            print(f"❌ Error al sincronizar comandos slash: {e}")

bot = KnekroGachaBot()

# -- Eventos del Bot --
@bot.event
async def on_ready():
    print(f"🎉 Bot iniciado con éxito como: {bot.user} (ID: {bot.user.id})")
    
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"⚡ Sincronizados al instante {len(synced)} comandos para el servidor: {guild.name}")
        except Exception as e:
            print(f"⚠️ Error al sincronizar con el servidor {guild.name}: {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="/gachapon | Tirando al 50/50 con KNekro"
        )
    )

# -- Comandos de Texto --
@bot.command(name="sync")
async def manual_sync(ctx):
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ ¡Sincronizados al instante {len(synced)} comandos para **{ctx.guild.name}**! Ya deberías ver `/gachapon`, `/tarjetazo`, etc.")

# -- Arranque --
if __name__ == "__main__":
    if not TOKEN or TOKEN == "PEGA_AQUI_TU_TOKEN_DE_DISCORD":
        print("\n" + "="*70)
        print("❌ ERROR: No se ha configurado el DISCORD_TOKEN en el archivo .env")
        print("Abre el archivo .env en este directorio y coloca tu token del Developer Portal.")
        print("Ejemplo: DISCORD_TOKEN=MTE5OT...")
        print("="*70 + "\n")
    else:
        bot.run(TOKEN)

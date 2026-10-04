# 🎰 KNekro BOT — Simulador Oficial de Ludopatía y Copium

Un bot de Discord diseñado científicamente para saciar tu adicción a **gamblear** sin que te embarguen la casa (aquí solo perderás **MiniPeruanos** y tu dignidad).

Inspirado en los míticos streams de **KNekro** y las mecánicas despiadadas del gachapón estilo *Genshin Impact*: tira al banner del Titán Dorado, sufre perdiendo el 50/50 contra Qiqi, pasa la tarjeta de crédito a fin de mes, mendiga limosnas si te quedas en la ruina o juégatelo todo al verde en la ruleta.

---

## ⚡ Inicio Rápido

1. **Configurar Token:** Crea tu bot en [Discord Developer Portal](https://discord.com/developers/applications), activa los *Privileged Gateway Intents* y añade tu token en [`.env`](.env):
   ```env
   DISCORD_TOKEN=tu_token_aqui
   ```
2. **Invitar al Servidor:** En **OAuth2 -> URL Generator**, marca scopes `bot` + `applications.commands` (con permisos de mensajes y slash commands) y abre el enlace para invitarlo.
3. **Ejecutar:** Doble clic en [`run.bat`](run.bat) (o ejecuta `.\venv\Scripts\python.exe main.py`). *Usa `!sync` en cualquier canal si quieres forzar la sincronización instantánea de comandos.*

---

## 🎮 Comandos (Slash Commands)

### 🎰 Gachapón & Colección
| Comando | Descripción |
| :--- | :--- |
| `/help_gacha` | Guía interactiva con la lista de todos los comandos y su funcionamiento. |
| `/gachapon [1 o 10]` | Tira al gacha (160 o 1.600 MiniPeruanos) con descripciones cómicas en cada tirada. |
| `/inventario` | Revisa tu colección con menú desplegable interactivo para leer el lore de tus objetos. |
| `/objeto [nombre]` | Ficha completa de cualquier objeto con historia, rareza y copias que posees (autocompletado). |
| `/añadir_premio` | 🎫 Crea un 5★ personalizado para incluirlo en el Gachapón del servidor (requiere Ticket 5★). |
| `/premios_comunidad` | Lista de todos los premios 5★ creados por los miembros de la comunidad. |

### 💳 Economía & Vicio
| Comando | Descripción |
| :--- | :--- |
| `/tarjetazo` | Pasa la tarjeta bancaria y reclama tus 1.600 MiniPeruanos (cada 12h). |
| `/perfil` | Consulta tu balance, pity acumulado, estado del 50/50 y derrotas frente a Qiqi. |
| `/apuesta [cant] [opc]` | Apuesta en la Ruleta (Rojo/Negro x2, Verde x14) o Cara/Cruz (x1.5). |
| `/mendigar` | Pídele limosna de emergencia a KNekro si estás en la quiebra absoluta (<160 MiniPeruanos, cada 1h 30m). |

### 🏆 Salón de la Fama y Desgracias
| Comando | Descripción |
| :--- | :--- |
| `/ranking [cat]` | Podio de más tiradas, más 50/50 perdidos (maldición de Qiqi) y más 5 estrellas. |
| `/top` | Ranking de los mayores millonarios en MiniPeruanos del servidor. |
---

## 🎲 Reglas del Gacha
- **Coste:** 160 MiniPeruanos por tirada (1 multi = 1.600).
- **Ratios 5★:** 0.6% base. *Soft Pity* a partir de la tirada 60 y *Hard Pity* garantizado al 100% en la tirada 80.
- **Sistema 50/50:** 50% de ganar el Titán promocional o 50% de perderlo ante memes permanentes. Si pierdes, ¡el siguiente 5★ es asegurado!
- **Límite C6 & Reembolso:** Máximo 6 copias por personaje/objeto (4★ y 5★). Las copias repetidas a partir de la 6ª devuelven **+60** (5★) o **+30** (4★) MiniPeruanos.
- **Persistencia:** Base de datos SQLite local (`gacha.db`). No se pierde ningún progreso al apagar el bot.

---

## 📁 Arquitectura Modular (Cogs)
- [`main.py`](main.py): Arranque del cliente, ciclo de vida y cargador automático de módulos.
- [`database.py`](database.py): Base de datos asíncrona (`aiosqlite`).
- `cogs/`: `gacha.py` (gachapón e inventario), `economy.py` (finanzas y apuestas), `ranking.py` (podios).
- `gachapon/`: `gacha_logic.py` (simulador), `gacha_pool.py` (catálogo con iconos), `quotes.py` (frases de KNekro).

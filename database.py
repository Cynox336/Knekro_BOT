import aiosqlite
from datetime import datetime, timezone

DB_NAME = "gacha.db"
MAX_COPIES = 6
REFUND_5STAR = 60
REFUND_4STAR = 30

# -- Inicialización Base de Datos --
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                protogemas INTEGER DEFAULT 1600,
                pity_5star INTEGER DEFAULT 0,
                pity_4star INTEGER DEFAULT 0,
                guaranteed_5star INTEGER DEFAULT 0,
                total_pulls INTEGER DEFAULT 0,
                last_daily TEXT DEFAULT NULL,
                last_beg TEXT DEFAULT NULL,
                lost_5050_count INTEGER DEFAULT 0
            )
        """)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_beg TEXT DEFAULT NULL")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN lost_5050_count INTEGER DEFAULT 0")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER,
                item_name TEXT,
                rarity INTEGER,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, item_name)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

# -- Usuarios & Saldo --
async def get_or_create_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                return dict(user)

        await db.execute(
            "INSERT INTO users (user_id, protogemas, pity_5star, pity_4star, guaranteed_5star, total_pulls, lost_5050_count) "
            "VALUES (?, 1600, 0, 0, 0, 0, 0)",
            (user_id,)
        )
        await db.commit()
        return {
            "user_id": user_id,
            "protogemas": 1600,
            "pity_5star": 0,
            "pity_4star": 0,
            "guaranteed_5star": 0,
            "total_pulls": 0,
            "last_daily": None,
            "last_beg": None,
            "lost_5050_count": 0
        }

async def update_balance(user_id: int, amount: int):
    await get_or_create_user(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET protogemas = protogemas + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()

# -- Recompensas Diarias --
async def claim_daily(user_id: int, amount: int = 1600):
    user = await get_or_create_user(user_id)
    now = datetime.now(timezone.utc)
    last_daily_str = user.get("last_daily")

    if last_daily_str:
        try:
            last_daily = datetime.fromisoformat(last_daily_str)
            elapsed = (now - last_daily).total_seconds()
            wait_seconds = 20 * 3600
            if elapsed < wait_seconds:
                remaining = wait_seconds - elapsed
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                return False, f"¡Tranquilo ludópata! Aún debes esperar **{hours}h {minutes}m** para tu próximo tarjetazo."
        except Exception:
            pass

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET protogemas = protogemas + ?, last_daily = ? WHERE user_id = ?",
            (amount, now.isoformat(), user_id)
        )
        await db.commit()
    return True, f"¡Has pasado la tarjeta de crédito! Recibes **+{amount} MiniPeruanos** 💳 (Suficiente para una multi de 10 tiradas)."

# -- Sistema de Mendigar --
async def claim_mendigar(user_id: int, amount: int = 160, cooldown_hours: int = 12):
    user = await get_or_create_user(user_id)
    if user["protogemas"] >= 160:
        return False, "NOT_POOR", f"❌ ¿Pero qué me estás contando? Tienes **{user['protogemas']} MiniPeruanos**. ¡Tú no eres pobre, ve a gastártelos a /gachapon!"

    now = datetime.now(timezone.utc)
    last_beg_str = user.get("last_beg")

    if last_beg_str:
        try:
            last_beg = datetime.fromisoformat(last_beg_str)
            elapsed = (now - last_beg).total_seconds()
            wait_seconds = cooldown_hours * 3600
            if elapsed < wait_seconds:
                remaining = wait_seconds - elapsed
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                return False, "COOLDOWN", f"¡No abuses, sinvergüenza! Ya te dimos limosna hace poco. Debes esperar **{hours}h {minutes}m** para volver a mendigar."
        except Exception:
            pass

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET protogemas = protogemas + ?, last_beg = ? WHERE user_id = ?",
            (amount, now.isoformat(), user_id)
        )
        await db.commit()

    return True, "SUCCESS", f"Recibes **+{amount} MiniPeruanos** 🇵🇪. ¡Suficiente para una tirada de emergencia!"

# -- Inventario & Límite C6 --
async def add_pull_to_inventory(user_id: int, item_name: str, rarity: int) -> int:
    refund = 0
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT count FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        ) as cursor:
            row = await cursor.fetchone()
            current_count = row[0] if row else 0

        if rarity in (4, 5) and not item_name.startswith("🎫") and current_count >= MAX_COPIES:
            refund = REFUND_5STAR if rarity == 5 else REFUND_4STAR
            await db.execute(
                "UPDATE users SET protogemas = protogemas + ? WHERE user_id = ?",
                (refund, user_id)
            )
        else:
            await db.execute("""
                INSERT INTO inventory (user_id, item_name, rarity, count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, item_name) DO UPDATE SET count = count + 1
            """, (user_id, item_name, rarity))

        await db.commit()
    return refund

# -- Estado del Gacha --
async def update_user_gacha_state(user_id: int, pity_5star: int, pity_4star: int, guaranteed_5star: int, pulls_done: int, protogemas_spent: int, lost_5050_inc: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users
            SET pity_5star = ?,
                pity_4star = ?,
                guaranteed_5star = ?,
                total_pulls = total_pulls + ?,
                lost_5050_count = lost_5050_count + ?,
                protogemas = protogemas - ?
            WHERE user_id = ?
        """, (pity_5star, pity_4star, guaranteed_5star, pulls_done, lost_5050_inc, protogemas_spent, user_id))
        await db.commit()

# -- Consultas de Inventario --
async def get_user_inventory(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT item_name, rarity, count
            FROM inventory
            WHERE user_id = ?
            ORDER BY rarity DESC, count DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# -- Clasificación General --
async def get_leaderboard(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, protogemas, total_pulls
            FROM users
            ORDER BY protogemas DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# -- Comandos de Testing y Reseteo --
async def reset_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
        await db.execute("""
            INSERT INTO users (user_id, protogemas, pity_5star, pity_4star, guaranteed_5star, total_pulls, last_daily, last_beg, lost_5050_count)
            VALUES (?, 1600, 0, 0, 0, 0, NULL, NULL, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                protogemas = 1600,
                pity_5star = 0,
                pity_4star = 0,
                guaranteed_5star = 0,
                total_pulls = 0,
                last_daily = NULL,
                last_beg = NULL,
                lost_5050_count = 0
        """, (user_id,))
        await db.commit()

async def set_user_protogemas(user_id: int, amount: int):
    await get_or_create_user(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET protogemas = ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()

async def set_user_pity(user_id: int, pity_5star: int, guaranteed: int = 0):
    await get_or_create_user(user_id)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET pity_5star = ?, guaranteed_5star = ? WHERE user_id = ?",
            (pity_5star, guaranteed, user_id)
        )
        await db.commit()

# -- Gestión de Objetos --
async def get_item_count(user_id: int, item_name: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT count FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def consume_item(user_id: int, item_name: str, amount: int = 1) -> bool:
    current = await get_item_count(user_id, item_name)
    if current < amount:
        return False
    async with aiosqlite.connect(DB_NAME) as db:
        if current == amount:
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
                (user_id, item_name)
            )
        else:
            await db.execute(
                "UPDATE inventory SET count = count - ? WHERE user_id = ? AND item_name = ?",
                (amount, user_id, item_name)
            )
        await db.commit()
    return True

# -- Premios Personalizados --
async def add_custom_prize(creator_id: int, name: str, description: str):
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO custom_prizes (creator_id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (creator_id, name, description, now)
        )
        await db.commit()

async def get_all_custom_prizes():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM custom_prizes ORDER BY id DESC") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# -- Rankings del Servidor --
async def get_ranking_pulls(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, total_pulls
            FROM users
            WHERE total_pulls > 0
            ORDER BY total_pulls DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_ranking_lost_5050(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, lost_5050_count
            FROM users
            WHERE lost_5050_count > 0
            ORDER BY lost_5050_count DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_ranking_five_stars(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT user_id, SUM(count) as total_5stars
            FROM inventory
            WHERE rarity = 5
            GROUP BY user_id
            HAVING total_5stars > 0
            ORDER BY total_5stars DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

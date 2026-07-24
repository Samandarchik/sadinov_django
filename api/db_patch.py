"""managed=False jadvallarga yetishmayotgan jadval/ustunlarni qo'shadi.

Modellar `managed = False` bo'lgani uchun Django migratsiyalari bu jadvallarning
schema'sini o'zgartirmaydi, deploy esa `migrate` chaqirmaydi. Shuning uchun yangi
jadval va ustunlar startup'da tekshiriladi va bo'lmasa qo'shiladi (idempotent)."""

import logging

from django.db import connection

logger = logging.getLogger(__name__)

# (jadval, CREATE TABLE IF NOT EXISTS SQL) — hali mavjud bo'lmagan jadvallar.
TABLES = [
    (
        "promo_codes",
        """
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            discount_type TEXT NOT NULL DEFAULT 'percent',
            discount_value INTEGER NOT NULL DEFAULT 0,
            min_order INTEGER NOT NULL DEFAULT 0,
            max_discount INTEGER,
            usage_limit INTEGER,
            used_count INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT,
            created_at TEXT NOT NULL
        )
        """,
    ),
]

# (jadval, ustun, SQL tipi)
COLUMNS = [
    ("products", "old_price", "INTEGER"),
    ("banners", "product_id", "INTEGER"),
    ("banners", "is_sale", "INTEGER NOT NULL DEFAULT 1"),
    ("orders", "promo_code", "TEXT"),
    ("orders", "discount", "INTEGER NOT NULL DEFAULT 0"),
]


def ensure_columns() -> None:
    with connection.cursor() as cur:
        for _table, create_sql in TABLES:
            cur.execute(create_sql)

        for table, column, sql_type in COLUMNS:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = %s",
                [table],
            )
            if not cur.fetchone():
                continue  # jadval hali yaratilmagan
            cur.execute(f"PRAGMA table_info({table})")
            if column in {row[1] for row in cur.fetchall()}:
                continue
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
            logger.info("DB patch: %s.%s ustuni qo'shildi", table, column)

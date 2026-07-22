"""managed=False jadvallarga yetishmayotgan ustunlarni qo'shadi.

Modellar `managed = False` bo'lgani uchun Django migratsiyalari bu jadvallarning
schema'sini o'zgartirmaydi, deploy esa `migrate` chaqirmaydi. Shuning uchun yangi
ustunlar startup'da tekshiriladi va bo'lmasa qo'shiladi (idempotent)."""

import logging

from django.db import connection

logger = logging.getLogger(__name__)

# (jadval, ustun, SQL tipi)
COLUMNS = [
    ("products", "old_price", "INTEGER"),
    ("banners", "product_id", "INTEGER"),
]


def ensure_columns() -> None:
    with connection.cursor() as cur:
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

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        # managed=False jadvallarga yangi ustunlarni qo'shadi (aksiya, banner linki).
        # ready() ichida so'rov yuborilmaydi — birinchi DB ulanishida bajariladi.
        from django.db.backends.signals import connection_created

        connection_created.connect(_patch_schema, weak=False)


def _patch_schema(sender, connection, **kwargs):
    if getattr(connection, "_sadinov_schema_patched", False):
        return
    connection._sadinov_schema_patched = True
    from .db_patch import ensure_columns

    try:
        ensure_columns()
    except Exception as e:  # build/collectstatic paytida baza bo'lmasligi mumkin
        logger.warning("DB patch bajarilmadi: %s", e)

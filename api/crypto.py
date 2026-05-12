"""Fernet shifrlash va hash helperlar."""

import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _build_fernet() -> Fernet:
    env_key = (settings.FERNET_KEY or "").strip()
    if env_key:
        try:
            return Fernet(env_key.encode())
        except Exception:
            pass
    raw = hashlib.sha256(b"sadinov-store-fernet-dev-key").digest()
    return Fernet(base64.urlsafe_b64encode(raw))


_fernet = _build_fernet()


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()


def decrypt_safe(value: str) -> str:
    """Eski plain qiymatlarni ham qo'llab-quvvatlaydi (migratsiya uchun)."""
    if not value:
        return value
    try:
        return decrypt(value)
    except (InvalidToken, ValueError):
        return value


def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

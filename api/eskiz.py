"""Eskiz.uz SMS provider integratsiyasi."""

import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

ESKIZ_LOGIN_URL = "https://notify.eskiz.uz/api/auth/login"
ESKIZ_SMS_URL = "https://notify.eskiz.uz/api/message/sms/send"


def _get_token() -> str | None:
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        return None
    try:
        r = httpx.post(
            ESKIZ_LOGIN_URL,
            data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("data", {}).get("token")
        logger.error("Eskiz login failed: %s %s", r.status_code, r.text)
    except Exception:
        logger.exception("Eskiz login error")
    return None


def send_sms(phone: str, code: str) -> bool:
    """SMS yuborishga urinish. Dev mode'da konsolga log qiladi.
    Tasdiqlangan shablon: 'Sadinov store mobil ilovasidan ro'yxatdan o'tish...'"""
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        print(f"\n[DEV SMS] {phone} → kod: {code}\n", flush=True)
        return True
    token = _get_token()
    if not token:
        print(f"\n[DEV SMS FALLBACK — eskiz auth] {phone} → kod: {code}\n", flush=True)
        return True
    msg = (
        f"Kodni hech kimga bermang! Sadinov store mobil ilovasidan "
        f"ro'yxatdan o'tish uchun tasdiqlash kodi: {code}"
    )
    try:
        r = httpx.post(
            ESKIZ_SMS_URL,
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mobile_phone": phone.lstrip("+"),
                "message": msg,
                "from": settings.ESKIZ_FROM,
            },
            timeout=15,
        )
        print(f"\n[ESKIZ] {phone} → status={r.status_code} body={r.text}\n",
              flush=True)
        if r.status_code == 200:
            return True
    except Exception:
        logger.exception("Eskiz SMS error")
    print(f"\n[DEV SMS FALLBACK] {phone} → kod: {code}\n", flush=True)
    return True

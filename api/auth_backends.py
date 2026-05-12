"""Bearer token auth — DRF uchun."""

from django.core.cache import cache
from rest_framework import authentication, exceptions
from .models import User
from .crypto import hash_token

# Admin tokenlari Django cache'da saqlanadi — gunicorn ko'p worker bilan
# ishlaganda barcha workerlar bir xil tokenlarni ko'rishi uchun.
_ADMIN_PREFIX = "admin_tok:"


def issue_admin_token(token: str) -> None:
    cache.set(_ADMIN_PREFIX + token, 1, timeout=None)


def revoke_admin_token(token: str) -> None:
    cache.delete(_ADMIN_PREFIX + token)


def is_admin_token(token: str) -> bool:
    return cache.get(_ADMIN_PREFIX + token) is not None


class BearerAuthentication(authentication.BaseAuthentication):
    """Bearer token user auth (user.auth_token = SHA-256 hash).
    Admin tokenlarini ham hisobga oladi (alohida set)."""

    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.lower().startswith("bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return None
        # Admin token bo'lsa user emas — view alohida tekshiradi
        if is_admin_token(token):
            request.admin_token = token  # noqa
            return (None, token)
        try:
            user = User.objects.get(auth_token=hash_token(token))
        except User.DoesNotExist:
            return None
        return (user, token)


def require_user(request):
    """View ichida foydalanish uchun helper — auth bo'lmasa 401."""
    if not isinstance(getattr(request, "user", None), User):
        raise exceptions.NotAuthenticated("Token kerak")
    return request.user


def require_admin(request):
    token = getattr(request, "admin_token", None) or (
        request.META.get("HTTP_AUTHORIZATION", "").split(" ", 1)[-1].strip()
        if request.META.get("HTTP_AUTHORIZATION", "").lower().startswith("bearer ")
        else None
    )
    if not token or not is_admin_token(token):
        raise exceptions.AuthenticationFailed("Admin token kerak")
    return token

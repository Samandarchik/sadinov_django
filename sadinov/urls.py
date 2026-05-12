"""Sadinov Store URL'lari — FastAPI bilan aynan bir xil yo'llar."""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import path, re_path
from django.views.generic import RedirectView
from api import views as v

PANEL_DIR: Path = settings.BASE_DIR / "panel"
MEDIA_DIR: Path = Path(settings.MEDIA_ROOT)


def serve_panel(request, path: str = "index.html"):
    """Flutter web admin panelini xizmat qiladi (DEBUG'siz ham ishlaydi)."""
    file_path = (PANEL_DIR / path).resolve()
    if not str(file_path).startswith(str(PANEL_DIR.resolve())):
        raise Http404("Yo'l noto'g'ri")
    if file_path.is_dir():
        file_path = file_path / "index.html"
    if not file_path.is_file():
        # SPA fallback — ichki marshrut bo'lsa, index.html qaytariladi
        file_path = PANEL_DIR / "index.html"
        if not file_path.is_file():
            raise Http404("Admin panel build qilinmagan")
    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        open(file_path, "rb"),
        content_type=content_type or "application/octet-stream",
    )


def serve_media(request, path: str):
    """Foydalanuvchi yuklagan rasmlarni xizmat qiladi (DEBUG'siz ham)."""
    file_path = (MEDIA_DIR / path).resolve()
    if not str(file_path).startswith(str(MEDIA_DIR.resolve())):
        raise Http404("Yo'l noto'g'ri")
    if not file_path.is_file():
        raise Http404("Fayl topilmadi")
    content_type, _ = mimetypes.guess_type(str(file_path))
    resp = FileResponse(
        open(file_path, "rb"),
        content_type=content_type or "application/octet-stream",
    )
    resp["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


urlpatterns = [
    path("", v.root),

    # Admin web panel (Flutter web build)
    path(
        "panel/",
        RedirectView.as_view(url="/panel/index.html", permanent=False),
    ),
    re_path(r"^panel/(?P<path>.+)$", serve_panel),

    # Auth (trailing slash bilan)
    path("auth/send-sms/", v.auth_send_sms),
    path("auth/verify-code/", v.auth_verify_code),
    path("auth/register/", v.auth_register),
    path("auth/me/", v.auth_me),
    path("auth/logout/", v.auth_logout),

    # Banners
    path("banners/", v.banners_list),
    path("banners/<int:pk>", v.banner_detail),
    path("banners/<int:pk>/", v.banner_detail),

    # Categories
    path("categories/", v.categories_list),
    path("categories/<int:pk>", v.category_detail),
    path("categories/<int:pk>/", v.category_detail),

    # Products
    path("products/", v.products_list),
    path("products/search/", v.products_search),
    path("products/names/all", v.products_names_all),
    path("products/names/all/", v.products_names_all),
    path("products/<int:pk>", v.product_detail),
    path("products/<int:pk>/", v.product_detail),

    # Services
    path("services/", v.services_list),
    path("services/<int:pk>", v.service_detail),
    path("services/<int:pk>/", v.service_detail),

    # Orders
    path("orders/", v.orders_list),
    path("orders/my/", v.orders_my),
    re_path(r"^orders/(?P<pk>[\w\-]+)/?$", v.order_detail),

    # Favorites
    path("favorites/", v.favorites_list),
    path("favorites/ids/", v.favorites_ids),
    path("favorites/<int:product_id>/", v.favorite_action),

    # Users
    path("users/", v.users_list),
    path("users/<int:pk>", v.user_detail),
    path("users/<int:pk>/", v.user_detail),

    # Admin
    path("admin/login/", v.admin_login),
    path("admin/logout/", v.admin_logout),
    path("admin/me/", v.admin_me),
    path("admin/stats/", v.admin_stats),
    path("admin/orders/", v.admin_orders),
    re_path(r"^admin/orders/(?P<pk>[\w\-]+)/status/?$", v.admin_order_status),
    re_path(r"^admin/orders/(?P<pk>[\w\-]+)/?$", v.admin_delete_order),
    path("admin/users/", v.admin_users),
    path("admin/users/<int:pk>/", v.admin_delete_user),

    # Uploads — admin-only
    path("uploads/image/", v.upload_image),

    # Media — yuklangan rasmlarni serve qilish
    re_path(r"^media/(?P<path>.+)$", serve_media),
]

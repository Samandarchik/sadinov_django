"""DRF API views — FastAPI endpointlari bilan aynan bir xil URL va JSON shape."""

import json
import re
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .auth_backends import (
    issue_admin_token,
    require_admin,
    require_user,
    revoke_admin_token,
)
from .crypto import decrypt, decrypt_safe, encrypt, hash_phone, hash_token
from .eskiz import send_sms as eskiz_send_sms
from .models import (
    Banner,
    Category,
    Favorite,
    Order,
    PhoneVerification,
    Product,
    PromoCode,
    Service,
    User,
)
from .serializers import (
    banner_to_dict,
    category_to_dict,
    order_to_dict,
    product_summary_to_dict,
    product_to_dict,
    promo_code_to_dict,
    service_to_dict,
    user_to_dict,
)


# --- Banners ---


def _positive_int_or_none(raw):
    """Bo'sh / 0 / noto'g'ri qiymatni None ga aylantiradi."""
    if raw in (None, "", 0, "0"):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _to_bool(raw, default=True):
    """`false` / `0` / `""` — o'chirilgan, qolgani yoqilgan deb qaraladi."""
    if raw is None:
        return default
    if isinstance(raw, str):
        return raw.strip().lower() not in ("", "0", "false", "no")
    return bool(raw)


@api_view(["GET", "POST"])
def banners_list(request):
    if request.method == "GET":
        return Response([banner_to_dict(b) for b in Banner.objects.all()])
    data = request.data
    b = Banner.objects.create(
        image_uz=data.get("image_uz", ""),
        image_ru=data.get("image_ru", ""),
        position=data.get("position", 0),
        product_id=_positive_int_or_none(data.get("product_id")),
        is_sale=int(_to_bool(data.get("is_sale"))),
    )
    return Response(banner_to_dict(b), status=201)


@api_view(["GET", "PUT", "DELETE"])
def banner_detail(request, pk: int):
    try:
        b = Banner.objects.get(pk=pk)
    except Banner.DoesNotExist:
        raise NotFound("Banner topilmadi")
    if request.method == "GET":
        return Response(banner_to_dict(b))
    if request.method == "DELETE":
        b.delete()
        return Response({"message": "Banner o'chirildi"})
    for f in ("image_uz", "image_ru", "position"):
        if f in request.data:
            setattr(b, f, request.data[f])
    if "product_id" in request.data:
        b.product_id = _positive_int_or_none(request.data["product_id"])
    if "is_sale" in request.data:
        b.is_sale = int(_to_bool(request.data["is_sale"]))
    b.save()
    return Response(banner_to_dict(b))


# --- Categories ---


@api_view(["GET", "POST"])
def categories_list(request):
    if request.method == "GET":
        return Response([category_to_dict(c) for c in Category.objects.all()])
    data = request.data
    c = Category.objects.create(
        name_uz=data.get("name_uz", ""),
        name_ru=data.get("name_ru", ""),
        image=data.get("image", ""),
        position=data.get("position", 0),
    )
    return Response(category_to_dict(c), status=201)


@api_view(["GET", "PUT", "DELETE"])
def category_detail(request, pk: int):
    try:
        c = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        raise NotFound("Kategoriya topilmadi")
    if request.method == "GET":
        return Response(category_to_dict(c))
    if request.method == "DELETE":
        c.delete()
        return Response({"message": "Kategoriya o'chirildi"})
    for f in ("name_uz", "name_ru", "image", "position"):
        if f in request.data:
            setattr(c, f, request.data[f])
    c.save()
    return Response(category_to_dict(c))


# --- Products ---


def _apply_product_fields(p, data):
    for f in [
        "name", "name_uz", "name_ru",
        "description", "description_uz", "description_ru",
        "price", "currency", "category_id", "category_name",
        "position", "quantity",
    ]:
        if f in data:
            setattr(p, f, data[f])
    if "old_price" in data:
        # Aksiya: eski narx faqat hozirgi narxdan katta bo'lsa saqlanadi.
        old = _positive_int_or_none(data["old_price"])
        p.old_price = old if old and old > (p.price or 0) else None
    if "in_stock" in data:
        p.in_stock = 1 if data["in_stock"] else 0
    if "images" in data:
        p.images = json.dumps(data["images"])
    if "sizes" in data:
        p.sizes = json.dumps(data["sizes"])


@api_view(["GET", "POST"])
def products_list(request):
    if request.method == "GET":
        qs = Product.objects.all()
        cat = request.query_params.get("category_id")
        in_stock = request.query_params.get("in_stock")
        if cat is not None:
            qs = qs.filter(category_id=int(cat))
        if in_stock is not None:
            qs = qs.filter(in_stock=1 if in_stock.lower() == "true" else 0)
        # shuffle=true: har so'rovda tasodifiy tartib (bosh sahifadagi
        # "Ommabop mahsulotlar" har safar har xil chiqishi uchun).
        if (request.query_params.get("shuffle") or "").lower() == "true":
            qs = qs.order_by("?")
        return Response([product_to_dict(p) for p in qs])
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    p = Product(
        name=request.data.get("name", ""),
        price=request.data.get("price", 0),
        category_id=request.data.get("category_id", 0),
        category_name=request.data.get("category_name", ""),
        created_at=now,
        updated_at=now,
    )
    _apply_product_fields(p, request.data)
    p.save()
    return Response(product_to_dict(p), status=201)


@api_view(["GET"])
def products_search(request):
    """Qidiruv — 30 tadan sahifalab qaytaradi.

    `limit`/`offset` bilan cheksiz skroll qilinadi. Javob shakli:
    `{"results": [...], "total": n, "limit": .., "offset": .., "has_more": bool}`.
    """
    q = (request.query_params.get("q") or "").strip().lower()
    cat = request.query_params.get("category_id")

    try:
        limit = int(request.query_params.get("limit") or 30)
    except ValueError:
        limit = 30
    try:
        offset = int(request.query_params.get("offset") or 0)
    except ValueError:
        offset = 0
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    qs = Product.objects.all()
    if cat:
        qs = qs.filter(category_id=int(cat))
    if q:
        # name, name_uz, name_ru — uchalasi bo'yicha ham qidiramiz.
        like = f"%{q}%"
        qs = qs.extra(
            where=[
                "(LOWER(name) LIKE %s"
                " OR LOWER(COALESCE(name_uz, '')) LIKE %s"
                " OR LOWER(COALESCE(name_ru, '')) LIKE %s)"
            ],
            params=[like, like, like],
        )
    qs = qs.order_by("position", "id")

    total = qs.count()
    page = qs[offset:offset + limit]
    return Response({
        "results": [product_to_dict(p) for p in page],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    })


@api_view(["GET"])
def products_names_all(request):
    qs = Product.objects.all().order_by("name")
    return Response([product_summary_to_dict(p) for p in qs])


@api_view(["GET"])
def products_names(request):
    """Autocomplete uchun yengil ro'yxat — faqat id va nomlar.

    `?q=` berilsa server tomonda ham filtrlanadi, aks holda hammasi
    qaytadi (mijoz yozayotganda lokal filtrlash uchun).
    """
    qs = Product.objects.all()
    cat = request.query_params.get("category_id")
    if cat:
        qs = qs.filter(category_id=int(cat))
    q = (request.query_params.get("q") or "").strip().lower()
    if q:
        like = f"%{q}%"
        qs = qs.extra(
            where=[
                "(LOWER(name) LIKE %s"
                " OR LOWER(COALESCE(name_uz, '')) LIKE %s"
                " OR LOWER(COALESCE(name_ru, '')) LIKE %s)"
            ],
            params=[like, like, like],
        )
    rows = qs.order_by("name").values(
        "id", "name", "name_uz", "name_ru", "category_id", "category_name"
    )
    return Response(list(rows))


@api_view(["GET", "PUT", "DELETE"])
def product_detail(request, pk: int):
    try:
        p = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        raise NotFound("Mahsulot topilmadi")
    if request.method == "GET":
        return Response(product_to_dict(p))
    if request.method == "DELETE":
        p.delete()
        return Response({"message": "Mahsulot o'chirildi"})
    _apply_product_fields(p, request.data)
    p.updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    p.save()
    return Response(product_to_dict(p))


# --- Services ---


def _apply_service_fields(s, data):
    for f in [
        "name", "name_uz", "name_ru",
        "description", "description_uz", "description_ru",
        "image", "price", "time", "time_uz", "time_ru",
    ]:
        if f in data:
            setattr(s, f, data[f])
    for f in ("possibilities", "possibilities_uz", "possibilities_ru"):
        if f in data:
            setattr(s, f, json.dumps(data[f]))


@api_view(["GET", "POST"])
def services_list(request):
    if request.method == "GET":
        return Response([service_to_dict(s) for s in Service.objects.all()])
    s = Service(
        name=request.data.get("name", ""),
        price=request.data.get("price", 0),
    )
    _apply_service_fields(s, request.data)
    s.save()
    return Response(service_to_dict(s), status=201)


@api_view(["GET", "PUT", "DELETE"])
def service_detail(request, pk: int):
    try:
        s = Service.objects.get(pk=pk)
    except Service.DoesNotExist:
        raise NotFound("Xizmat topilmadi")
    if request.method == "GET":
        return Response(service_to_dict(s))
    if request.method == "DELETE":
        s.delete()
        return Response({"message": "Xizmat o'chirildi"})
    _apply_service_fields(s, request.data)
    s.save()
    return Response(service_to_dict(s))


# --- Auth ---

PHONE_RE = re.compile(r"^\+998\d{9}$")
CODE_TTL_MINUTES = 5

# App Store / Play Store reviewer demo account.
# Phone: 00 000 00 00, code: 000 000.
DEMO_PHONE = "+998000000000"
DEMO_CODE = "000000"
DEMO_NAME = "App Reviewer"


def _normalize_phone(raw: str) -> str:
    p = (raw or "").strip().replace(" ", "")
    if not p.startswith("+"):
        p = "+" + p
    if not PHONE_RE.match(p):
        raise ValidationError("Telefon raqami noto'g'ri formatda (+998XXXXXXXXX)")
    return p


@api_view(["POST"])
def auth_send_sms(request):
    phone = _normalize_phone(request.data.get("phone", ""))
    is_demo = phone == DEMO_PHONE
    code = DEMO_CODE if is_demo else f"{secrets.randbelow(900000) + 100000:06d}"
    phone_h = hash_phone(phone)
    with connection.cursor() as cur:
        cur.execute(
            """INSERT INTO phone_verifications (phone, code, created_at)
            VALUES (%s, %s, datetime('now'))
            ON CONFLICT(phone) DO UPDATE SET code = excluded.code,
                                              created_at = datetime('now')""",
            [phone_h, encrypt(code)],
        )
    if is_demo:
        return Response({"message": "SMS yuborildi"})
    if not eskiz_send_sms(phone, code):
        return Response({"detail": "SMS yuborilmadi"}, status=500)
    return Response({"message": "SMS yuborildi"})


@api_view(["POST"])
def auth_verify_code(request):
    phone = _normalize_phone(request.data.get("phone", ""))
    phone_h = hash_phone(phone)
    code = (request.data.get("code") or "").strip()
    try:
        pv = PhoneVerification.objects.get(phone=phone_h)
    except PhoneVerification.DoesNotExist:
        raise ValidationError("Avval SMS yuborilmagan")
    created = datetime.fromisoformat(pv.created_at)
    if datetime.utcnow() > created + timedelta(minutes=CODE_TTL_MINUTES):
        raise ValidationError("Kodning amal qilish muddati tugagan")
    try:
        stored = decrypt(pv.code)
    except Exception:
        raise ValidationError("Kod noto'g'ri saqlangan")
    if code != stored:
        raise ValidationError("Noto'g'ri kod kiritildi")

    user = User.objects.filter(phone_hash=phone_h).first()
    if not user and phone == DEMO_PHONE:
        # Reviewer demo account — auto-create so no name step is required.
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        user = User.objects.create(
            name=DEMO_NAME,
            phone=encrypt(phone),
            phone_hash=phone_h,
            created_at=now,
        )
    if user:
        raw = secrets.token_urlsafe(32)
        user.auth_token = hash_token(raw)
        user.save(update_fields=["auth_token"])
        pv.delete()
        return Response(
            {"is_new_user": False, "token": raw, "user": user_to_dict(user)}
        )
    return Response({"is_new_user": True, "phone": phone})


@api_view(["POST"])
def auth_register(request):
    phone = _normalize_phone(request.data.get("phone", ""))
    name = (request.data.get("name") or "").strip()
    if not name:
        raise ValidationError("Ism kiritilmadi")
    phone_h = hash_phone(phone)
    if User.objects.filter(phone_hash=phone_h).exists():
        raise ValidationError("Bu raqam allaqachon ro'yxatdan o'tgan")
    if not PhoneVerification.objects.filter(phone=phone_h).exists():
        raise ValidationError("Telefon raqami tasdiqlanmagan")
    raw = secrets.token_urlsafe(32)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    user = User.objects.create(
        name=name,
        phone=encrypt(phone),
        phone_hash=phone_h,
        auth_token=hash_token(raw),
        created_at=now,
    )
    PhoneVerification.objects.filter(phone=phone_h).delete()
    return Response({"token": raw, "user": user_to_dict(user)})


@api_view(["GET"])
def auth_me(request):
    user = require_user(request)
    return Response(user_to_dict(user))


@api_view(["POST"])
def auth_logout(request):
    user = require_user(request)
    user.auth_token = None
    user.save(update_fields=["auth_token"])
    return Response({"message": "Tizimdan chiqdingiz"})


# --- Promo codes ---

VALID_DISCOUNT_TYPES = {"percent", "fixed"}


def _normalize_code(raw: str) -> str:
    return (raw or "").strip().upper()


def _parse_expiry(raw):
    """`expires_at` matnini datetime'ga aylantiradi; faqat sana bo'lsa — kun oxiri."""
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        if len(s) == 10:  # YYYY-MM-DD — o'sha kun oxirigacha amal qiladi
            return datetime.fromisoformat(s) + timedelta(
                hours=23, minutes=59, seconds=59
            )
        return datetime.fromisoformat(s.replace("T", " "))
    except ValueError:
        return None


def _promo_discount(promo, subtotal: int) -> int:
    """Promo turi bo'yicha chegirma summasini (so'm) hisoblaydi."""
    if promo.discount_type == "fixed":
        discount = promo.discount_value or 0
    else:  # percent
        discount = (subtotal * (promo.discount_value or 0)) // 100
        if promo.max_discount:
            discount = min(discount, promo.max_discount)
    return max(0, min(discount, subtotal))


def _evaluate_promo(code_raw: str, subtotal: int):
    """Promo kodni tekshiradi. `(promo, discount, None)` yoki `(None, 0, xato)`."""
    code = _normalize_code(code_raw)
    if not code:
        return None, 0, "Promo kod kiritilmadi"
    promo = PromoCode.objects.filter(code=code).first()
    if not promo:
        return None, 0, "Promo kod topilmadi"
    if not promo.active:
        return None, 0, "Promo kod faol emas"
    expiry = _parse_expiry(promo.expires_at)
    if expiry and datetime.utcnow() > expiry:
        return None, 0, "Promo kod muddati tugagan"
    if promo.usage_limit is not None and (promo.used_count or 0) >= promo.usage_limit:
        return None, 0, "Promo kod ishlatish limiti tugagan"
    if subtotal < (promo.min_order or 0):
        need = f"{promo.min_order:,}".replace(",", " ")
        return None, 0, f"Buyurtma summasi kamida {need} so'm bo'lishi kerak"
    discount = _promo_discount(promo, subtotal)
    if discount <= 0:
        return None, 0, "Bu promo kod chegirma bermaydi"
    return promo, discount, None


@api_view(["POST"])
def promo_validate(request):
    """Mijoz promo kodni checkout oldidan tekshiradi (used_count o'zgarmaydi)."""
    subtotal = _positive_int_or_none(request.data.get("subtotal")) or 0
    promo, discount, err = _evaluate_promo(request.data.get("code", ""), subtotal)
    if err:
        return Response({"valid": False, "detail": err}, status=400)
    return Response({
        "valid": True,
        "code": promo.code,
        "discount_type": promo.discount_type,
        "discount_value": promo.discount_value,
        "discount": discount,
        "subtotal": subtotal,
        "final_price": max(0, subtotal - discount),
    })


def _apply_promo_fields(p, data):
    if "code" in data:
        p.code = _normalize_code(data["code"])
    if "discount_type" in data:
        dt = (data["discount_type"] or "").strip().lower()
        p.discount_type = dt if dt in VALID_DISCOUNT_TYPES else "percent"
    if "discount_value" in data:
        try:
            p.discount_value = max(0, int(data["discount_value"] or 0))
        except (TypeError, ValueError):
            p.discount_value = 0
    if "min_order" in data:
        p.min_order = _positive_int_or_none(data["min_order"]) or 0
    if "max_discount" in data:
        p.max_discount = _positive_int_or_none(data["max_discount"])
    if "usage_limit" in data:
        p.usage_limit = _positive_int_or_none(data["usage_limit"])
    if "active" in data:
        p.active = int(_to_bool(data["active"]))
    if "expires_at" in data:
        p.expires_at = (data.get("expires_at") or "").strip() or None


def _validate_promo_payload(p):
    if not p.code:
        raise ValidationError("Promo kod matni kiritilmadi")
    if (p.discount_value or 0) <= 0:
        raise ValidationError("Chegirma qiymati 0 dan katta bo'lishi kerak")
    if p.discount_type == "percent" and p.discount_value > 100:
        raise ValidationError("Foizli chegirma 100% dan oshmasligi kerak")


@api_view(["GET", "POST"])
def admin_promo_codes(request):
    require_admin(request)
    if request.method == "GET":
        return Response([promo_code_to_dict(p) for p in PromoCode.objects.all()])
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    p = PromoCode(discount_type="percent", used_count=0, active=1, created_at=now)
    _apply_promo_fields(p, request.data)
    _validate_promo_payload(p)
    if PromoCode.objects.filter(code=p.code).exists():
        raise ValidationError("Bu promo kod allaqachon mavjud")
    p.save()
    return Response(promo_code_to_dict(p), status=201)


@api_view(["GET", "PUT", "DELETE"])
def admin_promo_code_detail(request, pk: int):
    require_admin(request)
    try:
        p = PromoCode.objects.get(pk=pk)
    except PromoCode.DoesNotExist:
        raise NotFound("Promo kod topilmadi")
    if request.method == "GET":
        return Response(promo_code_to_dict(p))
    if request.method == "DELETE":
        p.delete()
        return Response({"message": "Promo kod o'chirildi"})
    _apply_promo_fields(p, request.data)
    _validate_promo_payload(p)
    if PromoCode.objects.filter(code=p.code).exclude(pk=p.pk).exists():
        raise ValidationError("Bu promo kod allaqachon mavjud")
    p.save()
    return Response(promo_code_to_dict(p))


# --- Orders ---


def _generate_order_id() -> str:
    today = datetime.utcnow().date()
    prefix = today.strftime("%y-%m-%d")
    cnt = Order.objects.filter(id__startswith=prefix).count()
    return f"{prefix}-{cnt + 1:02d}"


@api_view(["GET", "POST"])
def orders_list(request):
    if request.method == "GET":
        return Response([order_to_dict(o) for o in Order.objects.all()])
    user = require_user(request)
    items = request.data.get("items", []) or []
    service_ids = request.data.get("service_ids", []) or []
    if not items and not service_ids:
        raise ValidationError("Kamida bitta mahsulot yoki xizmat tanlash kerak")
    for it in items:
        if not Product.objects.filter(pk=it["product_id"]).exists():
            raise ValidationError(f"Mahsulot {it['product_id']} topilmadi")
    for sid in service_ids:
        if not Service.objects.filter(pk=sid).exists():
            raise ValidationError(f"Xizmat {sid} topilmadi")

    # Buyurtma summasi. Mahsulotlar bo'lsa serverda qayta hisoblanadi
    # (mijoz yuborgan narxga to'liq ishonmaslik uchun).
    subtotal = int(request.data.get("price") or 0)
    if items and not service_ids:
        item_total = sum(
            int(it.get("unit_price") or 0) * int(it.get("quantity") or 0)
            for it in items
        )
        if item_total > 0:
            subtotal = item_total

    # Promo kod (ixtiyoriy) — chegirma serverda hisoblanadi.
    promo = None
    discount = 0
    promo_code_raw = request.data.get("promo_code")
    if promo_code_raw:
        promo, discount, err = _evaluate_promo(promo_code_raw, subtotal)
        if err:
            return Response({"detail": err}, status=400)
    final_price = max(0, subtotal - discount)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    o = Order.objects.create(
        id=_generate_order_id(),
        user_id=user.id,
        items=json.dumps(items),
        service_ids=json.dumps(service_ids),
        longitude=request.data.get("longitude"),
        latitude=request.data.get("latitude"),
        address=request.data.get("address"),
        comment=request.data.get("comment"),
        price=final_price,
        promo_code=promo.code if promo else None,
        discount=discount,
        status="pending",
        created_at=now,
    )
    if promo:
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = %s",
                [promo.id],
            )
    return Response(order_to_dict(o), status=201)


@api_view(["GET"])
def orders_my(request):
    user = require_user(request)
    qs = Order.objects.filter(user_id=user.id)
    return Response([order_to_dict(o) for o in qs])


@api_view(["GET", "DELETE"])
def order_detail(request, pk: str):
    try:
        o = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        raise NotFound("Buyurtma topilmadi")
    if request.method == "DELETE":
        o.delete()
        return Response({"message": "Buyurtma o'chirildi"})
    return Response(order_to_dict(o))


# --- Favorites ---


@api_view(["GET"])
def favorites_list(request):
    user = require_user(request)
    pids = list(
        Favorite.objects.filter(user_id=user.id)
        .order_by("-created_at")
        .values_list("product_id", flat=True)
    )
    out = []
    for pid in pids:
        p = Product.objects.filter(pk=pid).first()
        if p:
            out.append(product_to_dict(p))
    return Response(out)


@api_view(["GET"])
def favorites_ids(request):
    user = require_user(request)
    ids = list(
        Favorite.objects.filter(user_id=user.id)
        .order_by("-created_at")
        .values_list("product_id", flat=True)
    )
    return Response(ids)


@api_view(["POST", "DELETE"])
def favorite_action(request, product_id: int):
    user = require_user(request)
    if request.method == "POST":
        if not Product.objects.filter(pk=product_id).exists():
            raise NotFound("Mahsulot topilmadi")
        with connection.cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO favorites (user_id, product_id) VALUES (%s, %s)",
                [user.id, product_id],
            )
        return Response({"product_id": product_id, "favorite": True}, status=201)
    Favorite.objects.filter(user_id=user.id, product_id=product_id).delete()
    return Response({"product_id": product_id, "favorite": False})


# --- Users (basic) ---


@api_view(["GET"])
def users_list(request):
    return Response(
        [user_to_dict(u) for u in User.objects.all().order_by("id")]
    )


@api_view(["GET"])
def user_detail(request, pk: int):
    try:
        u = User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise NotFound("Foydalanuvchi topilmadi")
    return Response(user_to_dict(u))


# --- Admin ---


@api_view(["POST"])
def admin_login(request):
    u = request.data.get("username", "")
    p = request.data.get("password", "")
    if u != settings.ADMIN_USERNAME or p != settings.ADMIN_PASSWORD:
        return Response({"detail": "Login yoki parol noto'g'ri"}, status=401)
    token = secrets.token_urlsafe(32)
    issue_admin_token(token)
    return Response({"token": token, "username": u})


@api_view(["POST"])
def admin_logout(request):
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        revoke_admin_token(token)
    return Response({"ok": True})


@api_view(["GET"])
def admin_me(request):
    require_admin(request)
    return Response({"username": settings.ADMIN_USERNAME, "is_admin": True})


@api_view(["GET"])
def admin_stats(request):
    require_admin(request)
    with connection.cursor() as cur:
        def c(t):
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            return cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(price), 0) FROM orders")
        revenue = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending = cur.fetchone()[0] or 0
        users_count = c("users")
        products_count = c("products")
        services_count = c("services")
        categories_count = c("categories")
        banners_count = c("banners")
        orders_count = c("orders")
        favorites_count = c("favorites")
        return Response({
            "total_users": users_count,
            "total_products": products_count,
            "total_services": services_count,
            "total_categories": categories_count,
            "total_banners": banners_count,
            "total_orders": orders_count,
            "pending_orders": pending,
            "total_favorites": favorites_count,
            "total_revenue": revenue,
            "users": users_count,
            "products": products_count,
            "services": services_count,
            "categories": categories_count,
            "banners": banners_count,
            "orders": orders_count,
            "orders_pending": pending,
            "favorites": favorites_count,
            "revenue": revenue,
        })


@api_view(["GET"])
def admin_orders(request):
    require_admin(request)
    with connection.cursor() as cur:
        cur.execute(
            """SELECT o.*, u.name AS user_name, u.phone AS user_phone
               FROM orders o LEFT JOIN users u ON u.id = o.user_id
               ORDER BY o.created_at DESC"""
        )
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    out = []
    for r in rows:
        r["items"] = json.loads(r["items"]) if r.get("items") else []
        r["service_ids"] = (
            json.loads(r["service_ids"]) if r.get("service_ids") else []
        )
        if r.get("user_phone"):
            r["user_phone"] = decrypt_safe(r["user_phone"])
        out.append(r)
    return Response(out)


@api_view(["PATCH"])
def admin_order_status(request, pk: str):
    require_admin(request)
    new_status = (request.data.get("status") or "").strip()
    if new_status not in {"pending", "confirmed", "in_progress", "delivered", "cancelled"}:
        raise ValidationError("Noto'g'ri status")
    try:
        o = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        raise NotFound("Buyurtma topilmadi")
    o.status = new_status
    o.save(update_fields=["status"])
    return Response({"id": pk, "status": new_status})


@api_view(["DELETE"])
def admin_delete_order(request, pk: str):
    require_admin(request)
    try:
        o = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        raise NotFound("Buyurtma topilmadi")
    o.delete()
    return Response({"ok": True})


@api_view(["GET"])
def admin_users(request):
    require_admin(request)
    with connection.cursor() as cur:
        cur.execute(
            """SELECT u.id, u.name, u.phone, u.created_at,
                      (SELECT COUNT(*) FROM orders WHERE user_id = u.id) AS orders_count,
                      (SELECT COALESCE(SUM(price), 0) FROM orders WHERE user_id = u.id) AS total_spent
               FROM users u ORDER BY u.id DESC"""
        )
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        r["phone"] = decrypt_safe(r["phone"])
    return Response(rows)


@api_view(["DELETE"])
def admin_delete_user(request, pk: int):
    require_admin(request)
    try:
        u = User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise NotFound("Foydalanuvchi topilmadi")
    u.delete()
    return Response({"ok": True})


@api_view(["GET"])
def root(request):
    return Response({"message": "Sadinov Store API (Django) ishlayapti!"})


# --- Uploads ---

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@api_view(["POST"])
def upload_image(request):
    """Rasm fayl yuklash. multipart/form-data orqali `file` field qabul qiladi."""
    import os
    import uuid
    from pathlib import Path

    require_admin(request)

    f = request.FILES.get("file")
    if not f:
        raise ValidationError("Fayl yuborilmadi (file maydoni)")

    name = (f.name or "").lower()
    ext = os.path.splitext(name)[1]
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValidationError(
            f"Faqat rasm formatlar: {', '.join(sorted(ALLOWED_IMAGE_EXT))}"
        )
    if f.size and f.size > MAX_IMAGE_BYTES:
        raise ValidationError("Fayl 10 MB dan katta")

    media_dir = Path(settings.MEDIA_ROOT) / "uploads"
    media_dir.mkdir(parents=True, exist_ok=True)

    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = media_dir / fname
    with open(fpath, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)

    rel_url = f"/media/uploads/{fname}"
    return Response(
        {
            "filename": fname,
            "url": rel_url,
            "size": f.size,
            "content_type": f.content_type,
        },
        status=201,
    )

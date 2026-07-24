"""JSON shape FastAPI bilan aynan bir xil bo'lishi uchun qo'lda yozilgan
serializerlar (dict qaytaradigan helperlar)."""

import json

from .crypto import decrypt_safe


def _loads(value, default=None):
    if not value:
        return default if default is not None else []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default if default is not None else []


def _discount_percent(price, old_price):
    """Aksiya foizi; aksiya bo'lmasa None."""
    if not old_price or not price or old_price <= price:
        return None
    return round((old_price - price) * 100 / old_price)


def banner_to_dict(b) -> dict:
    return {
        "id": b.id,
        "image_uz": b.image_uz,
        "image_ru": b.image_ru,
        "position": b.position,
        "product_id": b.product_id,
        "is_sale": bool(b.is_sale),
    }


def category_to_dict(c) -> dict:
    return {
        "id": c.id,
        "name_ru": c.name_ru,
        "name_uz": c.name_uz,
        "image": c.image,
        "position": c.position,
    }


def product_to_dict(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "name_uz": p.name_uz,
        "name_ru": p.name_ru,
        "description": p.description,
        "description_uz": p.description_uz,
        "description_ru": p.description_ru,
        "price": p.price,
        "old_price": p.old_price,
        "discount_percent": _discount_percent(p.price, p.old_price),
        "currency": p.currency,
        "images": _loads(p.images),
        "sizes": _loads(p.sizes),
        "category_id": p.category_id,
        "category_name": p.category_name,
        "position": p.position,
        "in_stock": bool(p.in_stock),
        "quantity": p.quantity,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def product_summary_to_dict(p) -> dict:
    """`/products/names/all/` uchun qisqartirilgan ko'rinish."""
    return {
        "id": p.id,
        "name": p.name,
        "name_uz": p.name_uz,
        "name_ru": p.name_ru,
        "category_id": p.category_id,
        "category_name": p.category_name,
        "price": p.price,
        "old_price": p.old_price,
        "discount_percent": _discount_percent(p.price, p.old_price),
        "currency": p.currency,
        "images": _loads(p.images),
        "in_stock": bool(p.in_stock),
    }


def service_to_dict(s) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "name_uz": s.name_uz,
        "name_ru": s.name_ru,
        "description": s.description,
        "description_uz": s.description_uz,
        "description_ru": s.description_ru,
        "image": s.image,
        "price": s.price,
        "time": s.time,
        "time_uz": s.time_uz,
        "time_ru": s.time_ru,
        "possibilities": _loads(s.possibilities),
        "possibilities_uz": _loads(s.possibilities_uz),
        "possibilities_ru": _loads(s.possibilities_ru),
    }


def user_to_dict(u) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "phone": decrypt_safe(u.phone),
    }


def promo_code_to_dict(p) -> dict:
    return {
        "id": p.id,
        "code": p.code,
        "discount_type": p.discount_type,
        "discount_value": p.discount_value,
        "min_order": p.min_order,
        "max_discount": p.max_discount,
        "usage_limit": p.usage_limit,
        "used_count": p.used_count or 0,
        "active": bool(p.active),
        "expires_at": p.expires_at,
        "created_at": p.created_at,
    }


def order_to_dict(o, user_name: str | None = None, user_phone: str | None = None) -> dict:
    d = {
        "id": o.id,
        "user_id": o.user_id,
        "items": _loads(o.items),
        "service_ids": _loads(o.service_ids),
        "longitude": o.longitude,
        "latitude": o.latitude,
        "address": o.address,
        "comment": o.comment,
        "price": o.price,
        "promo_code": getattr(o, "promo_code", None),
        "discount": getattr(o, "discount", 0) or 0,
        "status": o.status,
        "created_at": o.created_at,
    }
    if user_name is not None:
        d["user_name"] = user_name
    if user_phone is not None:
        d["user_phone"] = decrypt_safe(user_phone) if user_phone else None
    return d

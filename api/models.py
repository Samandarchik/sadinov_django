"""SQLite jadvallar bilan bir xil schema'dagi modellar.
Mavjud FastAPI bazasi bilan ishlash uchun managed=False."""

from django.db import models


class Banner(models.Model):
    image_uz = models.TextField()
    image_ru = models.TextField()
    position = models.IntegerField(default=0)

    class Meta:
        db_table = "banners"
        managed = False
        ordering = ["position"]


class Category(models.Model):
    name_ru = models.TextField()
    name_uz = models.TextField()
    image = models.TextField()
    position = models.IntegerField(default=0)

    class Meta:
        db_table = "categories"
        managed = False
        ordering = ["position"]


class Product(models.Model):
    name = models.TextField()
    name_uz = models.TextField(null=True, blank=True)
    name_ru = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    description_uz = models.TextField(null=True, blank=True)
    description_ru = models.TextField(null=True, blank=True)
    price = models.IntegerField()
    currency = models.TextField(default="UZS")
    images = models.TextField(default="[]")
    sizes = models.TextField(default="[]")
    category_id = models.IntegerField()
    category_name = models.TextField()
    position = models.IntegerField(default=0)
    in_stock = models.IntegerField(default=1)
    quantity = models.IntegerField(null=True, blank=True)
    created_at = models.TextField()
    updated_at = models.TextField()

    class Meta:
        db_table = "products"
        managed = False
        ordering = ["position"]


class Service(models.Model):
    name = models.TextField()
    name_uz = models.TextField(null=True, blank=True)
    name_ru = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    description_uz = models.TextField(null=True, blank=True)
    description_ru = models.TextField(null=True, blank=True)
    image = models.TextField(null=True, blank=True)
    price = models.IntegerField()
    time = models.TextField(null=True, blank=True)
    time_uz = models.TextField(null=True, blank=True)
    time_ru = models.TextField(null=True, blank=True)
    possibilities = models.TextField(default="[]")
    possibilities_uz = models.TextField(default="[]")
    possibilities_ru = models.TextField(default="[]")

    class Meta:
        db_table = "services"
        managed = False


class User(models.Model):
    name = models.TextField()
    phone = models.TextField()  # Fernet encrypted
    phone_hash = models.TextField(null=True, blank=True, unique=True)
    auth_token = models.TextField(null=True, blank=True, unique=True)
    created_at = models.TextField()

    class Meta:
        db_table = "users"
        managed = False


class PhoneVerification(models.Model):
    phone = models.TextField(primary_key=True)  # SHA-256 hash
    code = models.TextField()  # Fernet encrypted
    created_at = models.TextField()

    class Meta:
        db_table = "phone_verifications"
        managed = False


class Order(models.Model):
    id = models.TextField(primary_key=True)
    user_id = models.IntegerField()
    items = models.TextField(default="[]")
    service_ids = models.TextField(default="[]")
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    price = models.IntegerField()
    status = models.TextField(default="pending")
    created_at = models.TextField()

    class Meta:
        db_table = "orders"
        managed = False
        ordering = ["-created_at"]


class Favorite(models.Model):
    user_id = models.IntegerField()
    product_id = models.IntegerField()
    created_at = models.TextField()

    class Meta:
        db_table = "favorites"
        managed = False

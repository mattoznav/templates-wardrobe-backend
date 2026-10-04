"""Load the demo data from data/*.csv into the database.

Every CSV file is a table: one row per record, an `id` column as primary key
and `<table>_id` columns as foreign keys. Edit the files, then run
`python manage.py load_data` to rebuild the database from them.
"""

import csv
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Category, Collection, Colour, Product, ProductImage, Size, Variant
from apps.core.models import Editorial, Photo, Store
from apps.orders.models import Order, ShippingMethod
from apps.payments.models import Payment
from apps.returns.models import ReturnRequest


def read(name: str, data_dir: Path | None = None) -> list[dict]:
    path = Path(data_dir or settings.STORE_DATA_DIR) / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def split(value: str) -> list[str]:
    return [v for v in value.split("|") if v] if value else []


def optional_decimal(value: str) -> Decimal | None:
    return Decimal(value) if value else None


def optional_int(value: str) -> int | None:
    return int(value) if value else None


def flag(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes")


@transaction.atomic
def load_all(data_dir: Path | None = None) -> dict[str, int]:
    """Replace every table with the CSV contents. Users are kept."""

    def rows(name: str) -> list[dict]:
        return read(name, data_dir)

    # Children first, so foreign keys never point to a missing row
    ReturnRequest.objects.all().delete()
    Payment.objects.all().delete()
    Order.objects.all().delete()
    Collection.products.through.objects.all().delete()
    for model in (Collection, ProductImage, Variant, Product, Size, Colour, Category, ShippingMethod, Editorial, Photo, Store):
        model.objects.all().delete()

    Store.objects.bulk_create(
        [
            Store(
                **{k: v for k, v in r.items() if k not in ("free_shipping_over", "return_window_days")},
                free_shipping_over=optional_decimal(r["free_shipping_over"]),
                return_window_days=int(r["return_window_days"]),
            )
            for r in rows("store.csv")
        ]
    )
    Photo.objects.bulk_create([Photo(**r) for r in rows("photos.csv")])
    Editorial.objects.bulk_create(
        [Editorial(id=int(r["id"]), key=r["key"], title=r["title"], text=r["text"], photo_id=int(r["photo_id"]), alt=r["alt"]) for r in rows("editorial.csv")]
    )

    Category.objects.bulk_create([Category(id=int(r["id"]), slug=r["slug"], name=r["name"], position=int(r["position"])) for r in rows("categories.csv")])
    Colour.objects.bulk_create([Colour(id=int(r["id"]), slug=r["slug"], name=r["name"], hex=r["hex"]) for r in rows("colours.csv")])
    Size.objects.bulk_create(
        [Size(id=int(r["id"]), code=r["code"], label=r["label"], system=r["system"], position=int(r["position"])) for r in rows("sizes.csv")]
    )
    ShippingMethod.objects.bulk_create(
        [
            ShippingMethod(
                id=int(r["id"]),
                code=r["code"],
                name=r["name"],
                description=r["description"],
                price=Decimal(r["price"]),
                free_over_threshold=flag(r["free_over_threshold"]),
                days_min=int(r["days_min"]),
                days_max=int(r["days_max"]),
                position=int(r["position"]),
            )
            for r in rows("shipping_methods.csv")
        ]
    )

    product_rows = rows("products.csv")
    Product.objects.bulk_create(
        [
            Product(
                id=int(r["id"]),
                slug=r["slug"],
                name=r["name"],
                department=r["department"],
                category_id=int(r["category_id"]),
                status=r["status"],
                description=r["description"],
                details=split(r["details"]),
                composition=r["composition"],
                care=r["care"],
                price=Decimal(r["price"]),
                compare_at_price=optional_decimal(r["compare_at_price"]),
                is_new=flag(r["is_new"]),
                popularity=optional_int(r["popularity"]) or 0,
            )
            for r in product_rows
        ]
    )
    # Dates are stored as "days ago", so "new in" stays new whenever the demo is loaded
    now = timezone.now()
    for r in product_rows:
        Product.objects.filter(pk=int(r["id"])).update(created_at=now - timedelta(days=int(r["added_days_ago"] or 0)))

    ProductImage.objects.bulk_create(
        [
            ProductImage(
                id=int(r["id"]),
                product_id=int(r["product_id"]),
                photo_id=int(r["photo_id"]),
                colour_id=optional_int(r["colour_id"]),
                alt=r["alt"],
                position=int(r["position"]),
            )
            for r in rows("product_images.csv")
        ]
    )
    Variant.objects.bulk_create(
        [
            Variant(
                id=int(r["id"]),
                product_id=int(r["product_id"]),
                colour_id=int(r["colour_id"]),
                size_id=int(r["size_id"]),
                sku=r["sku"],
                stock=int(r["stock"]),
            )
            for r in rows("variants.csv")
        ]
    )
    Collection.objects.bulk_create(
        [
            Collection(
                id=int(r["id"]),
                slug=r["slug"],
                title=r["title"],
                subtitle=r["subtitle"],
                description=r["description"],
                photo_id=int(r["photo_id"]),
                alt=r["alt"],
                position=int(r["position"]),
            )
            for r in rows("collections.csv")
        ]
    )
    Collection.products.through.objects.bulk_create(
        [
            Collection.products.through(collection_id=int(r["collection_id"]), product_id=int(r["product_id"]))
            for r in rows("collection_products.csv")
        ]
    )

    return {
        "products": Product.objects.count(),
        "variants": Variant.objects.count(),
        "pieces in stock": sum(Variant.objects.values_list("stock", flat=True)),
        "collections": Collection.objects.count(),
        "photos": Photo.objects.count(),
    }

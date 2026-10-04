import secrets

from django.conf import settings
from django.db import models

from apps.catalog.models import Variant

# No 0/O or 1/I: references are read out over the phone
REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_reference():
    return "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))


class ShippingMethod(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    free_over_threshold = models.BooleanField(
        default=False, help_text="Free when the order reaches the store's free shipping amount."
    )
    days_min = models.PositiveSmallIntegerField(default=2)
    days_max = models.PositiveSmallIntegerField(default=4)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting payment"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    reference = models.CharField(max_length=12, unique=True, default=new_reference, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    email = models.EmailField()

    # Delivery address, copied on the order so later profile changes do not alter it
    full_name = models.CharField(max_length=120)
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2)
    phone = models.CharField(max_length=40, blank=True)

    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)

    expires_at = models.DateTimeField(help_text="Stock is released after this time unless the order is paid.")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference


class OrderLine(models.Model):
    """A variant in an order.

    Names, prices and the image are copied when the order is placed, so the
    order keeps reading the same after the catalogue changes. `reserved` is
    True while the quantity is taken out of stock for this line.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, related_name="order_lines")
    product_name = models.CharField(max_length=160)
    product_slug = models.SlugField()
    colour = models.CharField(max_length=60)
    size = models.CharField(max_length=20)
    sku = models.CharField(max_length=40)
    image_url = models.URLField(max_length=300, blank=True)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    reserved = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.order} {self.sku} x{self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

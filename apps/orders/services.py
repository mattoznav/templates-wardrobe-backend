"""Order rules: pricing a bag, reserving stock, confirming, cancelling and shipping.

Stock is taken out of `Variant.stock` the moment an order is placed, with a
conditional update (`stock >= quantity`), so two customers can never buy the
last piece twice. Unpaid orders give their stock back when they expire.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import Product, Variant
from apps.core.models import Store

from .models import Order, OrderLine, ShippingMethod

ZERO = Decimal("0.00")


class OrderError(Exception):
    """The request breaks an order rule. The message is safe to show to customers."""


class OutOfStock(OrderError):
    def __init__(self, items: list[dict]):
        self.items = items
        names = ", ".join(f"{i['name']} ({i['colour']}, {i['size']})" for i in items)
        super().__init__(f"Not enough stock for: {names}.")


@dataclass
class BagItem:
    variant: Variant
    quantity: int


@dataclass
class Quote:
    lines: list[dict] = field(default_factory=list)
    subtotal: Decimal = ZERO
    shipping: Decimal = ZERO
    total: Decimal = ZERO
    currency: str = "EUR"
    free_shipping_over: Decimal | None = None
    problems: list[str] = field(default_factory=list)


def store() -> Store | None:
    return Store.objects.first()


def shipping_cost(method: ShippingMethod, subtotal: Decimal) -> Decimal:
    shop = store()
    if method.free_over_threshold and shop and shop.free_shipping_over is not None and subtotal >= shop.free_shipping_over:
        return ZERO
    return method.price


def image_for(variant: Variant) -> str:
    """The photo of the variant's colour, or the product's first photo."""
    images = list(variant.product.images.all())
    match = next((i for i in images if i.colour_id == variant.colour_id), None) or (images[0] if images else None)
    return match.photo.url if match else ""


def quote(items: list[BagItem], method: ShippingMethod | None) -> Quote:
    """Price a bag with today's prices and stock. Problems are listed, not raised."""
    shop = store()
    result = Quote(currency=shop.currency if shop else "EUR", free_shipping_over=shop.free_shipping_over if shop else None)
    release_expired()
    for item in items:
        v = item.variant
        available = max(v.stock, 0)
        purchasable = v.product.status == Product.Status.ACTIVE
        line_total = v.product.price * item.quantity
        result.lines.append(
            {
                "variant": v.id,
                "sku": v.sku,
                "product": {"slug": v.product.slug, "name": v.product.name},
                "colour": v.colour.name,
                "size": v.size.label,
                "image": image_for(v),
                "unit_price": v.product.price,
                "compare_at_price": v.product.compare_at_price,
                "quantity": item.quantity,
                "available": available if purchasable else 0,
                "line_total": line_total,
            }
        )
        if not purchasable:
            result.problems.append(f"{v.product.name} is no longer available.")
        elif available < item.quantity:
            result.problems.append(
                f"Only {available} left of {v.product.name} ({v.colour.name}, {v.size.label})."
                if available
                else f"{v.product.name} ({v.colour.name}, {v.size.label}) is sold out."
            )
        result.subtotal += line_total
    result.shipping = shipping_cost(method, result.subtotal) if method and items else ZERO
    result.total = result.subtotal + result.shipping
    return result


def _take(variant_id: int, quantity: int) -> bool:
    return Variant.objects.filter(pk=variant_id, stock__gte=quantity).update(stock=F("stock") - quantity) == 1


def _give_back(lines) -> None:
    for line in lines:
        if line.reserved:
            Variant.objects.filter(pk=line.variant_id).update(stock=F("stock") + line.quantity)
            line.reserved = False
            line.save(update_fields=["reserved"])


def merge(items: list[BagItem]) -> list[BagItem]:
    """The same variant twice becomes one line."""
    merged: dict[int, BagItem] = {}
    for item in items:
        if item.variant.id in merged:
            merged[item.variant.id].quantity += item.quantity
        else:
            merged[item.variant.id] = BagItem(item.variant, item.quantity)
    return list(merged.values())


def place_order(user, items: list[BagItem], method: ShippingMethod, address: dict) -> Order:
    items = merge(items)
    if not items:
        raise OrderError("Your bag is empty.")
    if any(i.quantity < 1 for i in items):
        raise OrderError("Quantities must be at least 1.")
    if sum(i.quantity for i in items) > settings.ORDER_MAX_QUANTITY:
        raise OrderError(f"You can order up to {settings.ORDER_MAX_QUANTITY} pieces at a time.")

    priced = quote(items, method)
    unavailable = [i for i in items if i.variant.product.status != Product.Status.ACTIVE]
    if unavailable:
        raise OrderError(f"{unavailable[0].variant.product.name} is no longer available.")

    try:
        with transaction.atomic():
            # Placing a new order replaces the previous unpaid one, so stock is not held twice
            for previous in Order.objects.filter(user=user, status=Order.Status.PENDING):
                _close(previous, Order.Status.CANCELLED)

            order = Order.objects.create(
                user=user,
                email=address.get("email") or user.email,
                full_name=address["full_name"],
                address_line1=address["address_line1"],
                address_line2=address.get("address_line2", ""),
                city=address["city"],
                postal_code=address["postal_code"],
                country=address["country"].upper(),
                phone=address.get("phone", ""),
                shipping_method=method,
                subtotal=priced.subtotal,
                shipping=priced.shipping,
                total=priced.total,
                currency=priced.currency,
                expires_at=timezone.now() + timedelta(minutes=settings.ORDER_HOLD_MINUTES),
            )
            missing = []
            for item, line in zip(items, priced.lines, strict=True):
                v = item.variant
                if not _take(v.id, item.quantity):
                    missing.append({"variant": v.id, "name": v.product.name, "colour": v.colour.name, "size": v.size.label})
                    continue
                OrderLine.objects.create(
                    order=order,
                    variant=v,
                    product_name=v.product.name,
                    product_slug=v.product.slug,
                    colour=v.colour.name,
                    size=v.size.label,
                    sku=v.sku,
                    image_url=line["image"],
                    unit_price=v.product.price,
                    quantity=item.quantity,
                )
            if missing:
                raise OutOfStock(missing)  # rolls back every reservation above
    except IntegrityError:
        raise OrderError("Stock changed while you were checking out. Try again.") from None
    return order


def release_expired() -> int:
    """Expire unpaid orders past their deadline and put their stock back."""
    ids = list(
        Order.objects.filter(status=Order.Status.PENDING, expires_at__lte=timezone.now()).values_list("id", flat=True)
    )
    for order in Order.objects.filter(id__in=ids):
        with transaction.atomic():
            _close(order, Order.Status.EXPIRED, stamp=False)
    return len(ids)


@transaction.atomic
def confirm(order: Order) -> bool:
    """Mark a paid order as confirmed.

    Returns False when the order had expired and the stock went to someone else
    in the meantime: the caller must then refund the payment.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status in (Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED):
        return True
    if order.status not in (Order.Status.PENDING, Order.Status.EXPIRED):
        return False

    if order.status == Order.Status.EXPIRED:
        # Paid after the deadline: keep the order only if every piece is still in stock
        try:
            with transaction.atomic():
                for line in order.lines.all():
                    if not _take(line.variant_id, line.quantity):
                        raise OutOfStock([])
                order.lines.update(reserved=True)
        except OutOfStock:
            return False

    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])
    return True


def cancel(order: Order, *, by_staff: bool = False) -> Order:
    from apps.payments.services import refund_order

    if order.status in (Order.Status.CANCELLED, Order.Status.EXPIRED):
        raise OrderError("This order is no longer active.")
    if order.status in (Order.Status.SHIPPED, Order.Status.DELIVERED):
        raise OrderError("This order has already left the warehouse. Request a return instead.")
    if order.status == Order.Status.PAID:
        refund_order(order)
    with transaction.atomic():
        _close(order, Order.Status.CANCELLED)
    order.refresh_from_db()
    return order


def ship(order: Order, tracking_number: str = "") -> Order:
    if order.status != Order.Status.PAID:
        raise OrderError("Only paid orders can be shipped.")
    order.status = Order.Status.SHIPPED
    order.shipped_at = timezone.now()
    order.tracking_number = tracking_number.strip()
    order.save(update_fields=["status", "shipped_at", "tracking_number"])
    return order


def deliver(order: Order) -> Order:
    if order.status != Order.Status.SHIPPED:
        raise OrderError("Only shipped orders can be marked as delivered.")
    order.status = Order.Status.DELIVERED
    order.delivered_at = timezone.now()
    order.save(update_fields=["status", "delivered_at"])
    return order


def _close(order: Order, status: str, *, stamp: bool = True) -> None:
    _give_back(order.lines.all())
    order.status = status
    if stamp:
        order.cancelled_at = timezone.now()
    order.save(update_fields=["status", "cancelled_at"])

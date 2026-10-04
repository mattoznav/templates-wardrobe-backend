"""Returns: the customer asks, the parcel comes back, staff checks it and refunds.

The refund covers the pieces sent back, not the original shipping. Accepted
pieces go back into stock.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.catalog.models import Variant
from apps.orders.models import Order, OrderLine
from apps.orders.services import store

from .models import ReturnLine, ReturnRequest


class ReturnError(Exception):
    """The request breaks a return rule. The message is safe to show to customers."""


def returnable_quantity(line: OrderLine) -> int:
    """Pieces of a line that are not already in an open or accepted return."""
    asked = (
        ReturnLine.objects.filter(order_line=line)
        .exclude(request__status=ReturnRequest.Status.REJECTED)
        .aggregate(n=Sum("quantity"))["n"]
        or 0
    )
    return line.quantity - asked


def return_deadline(order: Order):
    received = order.delivered_at or order.shipped_at
    if received is None:
        return None
    shop = store()
    return received + timedelta(days=shop.return_window_days if shop else 30)


def can_return(order: Order) -> bool:
    deadline = return_deadline(order)
    return (
        order.status in (Order.Status.SHIPPED, Order.Status.DELIVERED)
        and deadline is not None
        and timezone.now() <= deadline
        and any(returnable_quantity(line) > 0 for line in order.lines.all())
    )


@transaction.atomic
def request_return(order: Order, picks: list[tuple[OrderLine, int]], reason: str, note: str = "") -> ReturnRequest:
    if order.status not in (Order.Status.SHIPPED, Order.Status.DELIVERED):
        raise ReturnError("Returns open once the order has shipped.")
    deadline = return_deadline(order)
    if deadline is None or timezone.now() > deadline:
        raise ReturnError("The return window for this order has closed.")
    picks = [(line, qty) for line, qty in picks if qty > 0]
    if not picks:
        raise ReturnError("Choose at least one piece to return.")
    for line, qty in picks:
        if line.order_id != order.id:
            raise ReturnError("Some pieces are not part of this order.")
        if qty > returnable_quantity(line):
            raise ReturnError(f"{line.product_name} ({line.size}) cannot be returned in that quantity.")

    request = ReturnRequest.objects.create(order=order, reason=reason, note=note)
    ReturnLine.objects.bulk_create([ReturnLine(request=request, order_line=line, quantity=qty) for line, qty in picks])
    return request


def refund_value(request: ReturnRequest) -> Decimal:
    return sum((rl.order_line.unit_price * rl.quantity for rl in request.lines.select_related("order_line")), Decimal("0"))


def receive(request: ReturnRequest, staff_note: str = "") -> ReturnRequest:
    """The parcel arrived and was checked: restock the pieces and refund them."""
    from apps.payments.services import refund_order

    with transaction.atomic():
        request = ReturnRequest.objects.select_for_update().get(pk=request.pk)
        if request.status != ReturnRequest.Status.REQUESTED:
            raise ReturnError("This return has already been handled.")
        for rl in request.lines.select_related("order_line"):
            Variant.objects.filter(pk=rl.order_line.variant_id).update(stock=F("stock") + rl.quantity)
        request.status = ReturnRequest.Status.REFUNDED
        request.closed_at = timezone.now()
        request.staff_note = staff_note
        request.save(update_fields=["status", "closed_at", "staff_note"])
    request.refund_amount = refund_order(request.order, refund_value(request))
    request.save(update_fields=["refund_amount"])
    return request


def reject(request: ReturnRequest, staff_note: str) -> ReturnRequest:
    if request.status != ReturnRequest.Status.REQUESTED:
        raise ReturnError("This return has already been handled.")
    if not staff_note.strip():
        raise ReturnError("Tell the customer why the return was rejected.")
    request.status = ReturnRequest.Status.REJECTED
    request.closed_at = timezone.now()
    request.staff_note = staff_note.strip()
    request.save(update_fields=["status", "closed_at", "staff_note"])
    return request

"""Payment flow, the same for every provider.

1. `start_checkout` creates a pending payment and returns the client secret.
2. The customer pays on the client.
3. The provider reports the outcome (webhook) and `handle_event` applies it.

`handle_event` is idempotent: providers may deliver the same event twice.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.orders import services as orders
from apps.orders.models import Order

from .models import Payment
from .providers import FAILED, SUCCEEDED, PaymentEvent, get_provider


class PaymentError(Exception):
    pass


def start_checkout(order: Order) -> tuple[Payment, str]:
    if order.status != Order.Status.PENDING or order.expires_at <= timezone.now():
        raise PaymentError("This order can no longer be paid. Your bag is still there: place the order again.")

    provider = get_provider()
    # A new attempt replaces any unfinished one
    order.payments.filter(status=Payment.Status.PENDING).update(status=Payment.Status.CANCELLED)
    payment = Payment.objects.create(order=order, provider=provider.name, amount=order.total, currency=order.currency)
    session = provider.create(payment)
    payment.provider_ref = session.provider_ref
    payment.save(update_fields=["provider_ref", "updated_at"])
    return payment, session.client_secret


def handle_event(provider_name: str, event: PaymentEvent) -> Payment | None:
    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("order")
            .filter(provider=provider_name, provider_ref=event.provider_ref)
            .first()
        )
        if payment is None or payment.status in (Payment.Status.SUCCEEDED, Payment.Status.REFUNDED):
            return payment

        if event.outcome == FAILED:
            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status", "updated_at"])
            return payment

        if event.outcome != SUCCEEDED:
            return payment

        # Money was taken, even if this attempt had been replaced: honour it
        payment.status = Payment.Status.SUCCEEDED
        payment.save(update_fields=["status", "updated_at"])
        order = payment.order
        already_paid = order.status in (Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED)

    if already_paid or not orders.confirm(order):
        # Paid twice, or paid too late for stock that is now gone
        refund(payment)
    return payment


def refund(payment: Payment, amount: Decimal | None = None) -> Decimal:
    """Refund all of a payment, or part of it. Returns the amount refunded."""
    if payment.status != Payment.Status.SUCCEEDED:
        return Decimal("0")
    amount = payment.refundable if amount is None else min(amount, payment.refundable)
    if amount <= 0:
        return Decimal("0")
    get_provider(payment.provider).refund(payment, amount)
    payment.refunded_amount += amount
    if payment.refunded_amount >= payment.amount:
        payment.status = Payment.Status.REFUNDED
    payment.save(update_fields=["refunded_amount", "status", "updated_at"])
    return amount


def refund_order(order: Order, amount: Decimal | None = None) -> Decimal:
    """Refund an order across its payments, all of it when no amount is given."""
    refunded = Decimal("0")
    for payment in order.payments.filter(status=Payment.Status.SUCCEEDED).order_by("created_at"):
        left = None if amount is None else amount - refunded
        if left is not None and left <= 0:
            break
        refunded += refund(payment, left)
    return refunded

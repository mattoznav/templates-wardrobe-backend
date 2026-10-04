import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import Variant
from apps.orders.models import Order, OrderLine, ShippingMethod
from apps.orders.services import image_for, shipping_cost, store
from apps.payments.models import Payment
from apps.returns.models import ReturnLine, ReturnRequest

# Fictional customers. Their accounts have no usable password.
CUSTOMERS = [
    ("Ada", "Marsh"), ("Bruno", "Kell"), ("Clara", "Voss"), ("Dario", "Fenn"), ("Elsa", "Wren"), ("Felix", "Hart"),
    ("Greta", "Lund"), ("Hugo", "Brandt"), ("Iris", "Calder"), ("Jonas", "Pike"), ("Kira", "Maddox"), ("Leo", "Strand"),
    ("Mila", "Quist"), ("Nils", "Ober"), ("Olga", "Reyes"), ("Pia", "Sato"), ("Quinn", "Ashby"), ("Rosa", "Teller"),
]
STREETS = ["Example Street", "Sample Road", "Demo Avenue", "Placeholder Lane", "Template Square"]


class Command(BaseCommand):
    help = "Create a month of fictional orders, payments and returns, so the back office has something to show."

    def add_arguments(self, parser):
        parser.add_argument("--orders", type=int, default=90)
        parser.add_argument("--seed", type=int, default=7)

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        User = get_user_model()
        shop = store()
        now = timezone.now()
        methods = list(ShippingMethod.objects.all())
        variants = list(Variant.objects.select_related("product", "colour", "size").prefetch_related("product__images__photo"))
        weights = [v.product.popularity for v in variants]

        customers = []
        for first, last in CUSTOMERS:
            user, _ = User.objects.get_or_create(
                email=f"{first}.{last}@example.com".lower(), defaults={"first_name": first, "last_name": last}
            )
            if user.has_usable_password():
                user.set_unusable_password()
                user.save()
            customers.append(user)

        created = returns = 0
        for i in range(options["orders"]):
            # More orders on recent days, a few every day
            placed = now - timedelta(days=min(29, int(rng.expovariate(1 / 9))), hours=rng.randint(0, 12), minutes=rng.randint(0, 59))
            user = rng.choice(customers)
            picks = {}
            for v in rng.choices(variants, weights=weights, k=rng.choice([1, 1, 1, 2, 2, 3])):
                picks[v.id] = (v, 1)
            lines = [(v, q) for v, q in picks.values() if Variant.objects.filter(pk=v.pk, stock__gte=q).update(stock=F("stock") - q)]
            if not lines:
                continue

            method = rng.choices(methods, weights=[8, 3, 2][: len(methods)])[0]
            subtotal = sum((v.product.price * q for v, q in lines), Decimal("0"))
            shipping = shipping_cost(method, subtotal)
            age = (now - placed).days
            status = (
                Order.Status.CANCELLED if rng.random() < 0.05
                else Order.Status.DELIVERED if age > 6
                else Order.Status.SHIPPED if age >= 1
                else Order.Status.PAID
            )
            order = Order.objects.create(
                user=user,
                status=status,
                email=user.email,
                full_name=user.get_full_name(),
                address_line1=f"{rng.randint(1, 120)} {rng.choice(STREETS)}",
                city="Sampletown",
                postal_code="00000",
                country=shop.country if shop else "IT",
                shipping_method=method,
                subtotal=subtotal,
                shipping=shipping,
                total=subtotal + shipping,
                currency=shop.currency if shop else "EUR",
                expires_at=placed + timedelta(minutes=15),
                paid_at=placed + timedelta(minutes=2),
                shipped_at=placed + timedelta(days=1) if status in (Order.Status.SHIPPED, Order.Status.DELIVERED) else None,
                delivered_at=placed + timedelta(days=rng.randint(2, 4)) if status == Order.Status.DELIVERED else None,
                cancelled_at=placed + timedelta(hours=3) if status == Order.Status.CANCELLED else None,
                tracking_number=f"TRK{rng.randint(10**8, 10**9 - 1)}" if status in (Order.Status.SHIPPED, Order.Status.DELIVERED) else "",
            )
            Order.objects.filter(pk=order.pk).update(created_at=placed)
            order_lines = [
                OrderLine.objects.create(
                    order=order, variant=v, product_name=v.product.name, product_slug=v.product.slug, colour=v.colour.name,
                    size=v.size.label, sku=v.sku, image_url=image_for(v), unit_price=v.product.price, quantity=q,
                    reserved=status != Order.Status.CANCELLED,
                )
                for v, q in lines
            ]
            payment = Payment.objects.create(
                order=order, provider="fake", provider_ref=f"fake_demo_{order.reference}", amount=order.total,
                currency=order.currency, status=Payment.Status.SUCCEEDED,
            )
            if status == Order.Status.CANCELLED:
                for v, q in lines:
                    Variant.objects.filter(pk=v.pk).update(stock=F("stock") + q)
                Payment.objects.filter(pk=payment.pk).update(status=Payment.Status.REFUNDED, refunded_amount=payment.amount)
            created += 1

            if status == Order.Status.DELIVERED and rng.random() < 0.18:
                line = rng.choice(order_lines)
                done = age > 12
                request = ReturnRequest.objects.create(
                    order=order,
                    reason=rng.choice([r for r, _ in ReturnRequest.Reason.choices]),
                    status=ReturnRequest.Status.REFUNDED if done else ReturnRequest.Status.REQUESTED,
                    refund_amount=line.unit_price if done else 0,
                    closed_at=order.delivered_at + timedelta(days=5) if done else None,
                )
                ReturnRequest.objects.filter(pk=request.pk).update(created_at=order.delivered_at + timedelta(days=1))
                ReturnLine.objects.create(request=request, order_line=line, quantity=1)
                if done:
                    Variant.objects.filter(pk=line.variant_id).update(stock=F("stock") + 1)
                    Payment.objects.filter(pk=payment.pk).update(refunded_amount=line.unit_price)
                returns += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} demo orders and {returns} returns"))

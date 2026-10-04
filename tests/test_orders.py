from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Variant
from apps.core.csvdata import load_all
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.providers import PaymentEvent
from apps.payments.services import handle_event

User = get_user_model()

ADDRESS = {
    "full_name": "Ada Marsh",
    "address_line1": "1 Example Street",
    "city": "Sampletown",
    "postal_code": "00000",
    "country": "it",
}


@override_settings(PAYMENT_PROVIDER="fake")
class OrderFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_all()
        cls.variant = Variant.objects.filter(stock__gte=5, product__price__gte=100).order_by("id").first()
        cls.other = Variant.objects.filter(stock__gte=5).exclude(pk=cls.variant.pk).order_by("id").first()
        cls.alice = User.objects.create_user("alice@example.com", "a-long-password")
        cls.bob = User.objects.create_user("bob@example.com", "a-long-password")
        cls.staff = User.objects.create_user("staff@example.com", "a-long-password", is_staff=True)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def stock(self, variant):
        return Variant.objects.get(pk=variant.pk).stock

    def place(self, user, items, method="standard"):
        return self.client_for(user).post(
            reverse("order-list"),
            {"items": [{"variant": v.id, "quantity": q} for v, q in items], "shipping_method": method, "address": ADDRESS},
            format="json",
        )

    def pay(self, user, order_id, outcome="succeeded"):
        client = self.client_for(user)
        checkout = client.post(reverse("order-checkout", args=[order_id]))
        self.assertEqual(checkout.status_code, 201, checkout.data)
        return client.post(
            reverse("payment-fake-complete"), {"payment_id": checkout.data["payment_id"], "outcome": outcome}, format="json"
        )

    def test_quote_prices_the_bag_and_lists_problems(self):
        Variant.objects.filter(pk=self.other.pk).update(stock=1)
        res = APIClient().post(
            reverse("bag-quote"),
            {"items": [{"variant": self.variant.id, "quantity": 2}, {"variant": self.other.id, "quantity": 3}], "shipping_method": "express"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        expected = self.variant.product.price * 2 + self.other.product.price * 3
        self.assertEqual(res.data["subtotal"], expected)
        self.assertEqual(res.data["total"], expected + 15)
        self.assertEqual(len(res.data["problems"]), 1)

    def test_standard_shipping_is_free_over_the_threshold(self):
        res = APIClient().post(
            reverse("bag-quote"), {"items": [{"variant": self.variant.id, "quantity": 2}], "shipping_method": "standard"}, format="json"
        )
        self.assertEqual(res.data["shipping"], 0)

    def test_placing_an_order_reserves_stock(self):
        before = self.stock(self.variant)
        res = self.place(self.alice, [(self.variant, 2)])
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["status"], "pending")
        self.assertEqual(res.data["country"], "IT")
        self.assertEqual(self.stock(self.variant), before - 2)

    def test_the_last_piece_cannot_be_sold_twice(self):
        Variant.objects.filter(pk=self.variant.pk).update(stock=1)
        self.assertEqual(self.place(self.alice, [(self.variant, 1)]).status_code, 201)
        res = self.place(self.bob, [(self.variant, 1)])
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["items"][0]["variant"], self.variant.id)
        self.assertEqual(self.stock(self.variant), 0)

    def test_a_failed_line_rolls_back_the_whole_order(self):
        Variant.objects.filter(pk=self.other.pk).update(stock=0)
        before = self.stock(self.variant)
        res = self.place(self.alice, [(self.variant, 1), (self.other, 1)])
        self.assertEqual(res.status_code, 409)
        self.assertEqual(self.stock(self.variant), before)
        self.assertFalse(Order.objects.filter(user=self.alice).exists())

    def test_expired_order_gives_the_stock_back(self):
        before = self.stock(self.variant)
        order_id = self.place(self.alice, [(self.variant, 2)]).data["id"]
        Order.objects.filter(pk=order_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        APIClient().get(reverse("product-detail", args=[self.variant.product.slug]))  # reads release expired holds
        self.assertEqual(Order.objects.get(pk=order_id).status, "expired")
        self.assertEqual(self.stock(self.variant), before)

    def test_new_order_replaces_the_unpaid_one(self):
        before = self.stock(self.variant)
        first = self.place(self.alice, [(self.variant, 1)]).data["id"]
        self.assertEqual(self.place(self.alice, [(self.variant, 1)]).status_code, 201)
        self.assertEqual(Order.objects.get(pk=first).status, "cancelled")
        self.assertEqual(self.stock(self.variant), before - 1)

    def test_successful_payment_marks_the_order_paid(self):
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        res = self.pay(self.alice, order_id)
        self.assertEqual(res.data, {"payment_status": "succeeded", "order_status": "paid"})

    def test_failed_payment_keeps_the_reservation_for_a_retry(self):
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        self.assertEqual(self.pay(self.alice, order_id, "failed").data["order_status"], "pending")
        self.assertEqual(self.pay(self.alice, order_id).data["order_status"], "paid")

    def test_duplicate_webhook_is_ignored(self):
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        self.pay(self.alice, order_id)
        payment = Payment.objects.get(order_id=order_id, status="succeeded")
        handle_event("fake", PaymentEvent(payment.provider_ref, "succeeded"))
        self.assertEqual(Payment.objects.get(pk=payment.pk).status, "succeeded")

    def test_late_payment_is_refunded_when_stock_is_gone(self):
        Variant.objects.filter(pk=self.variant.pk).update(stock=1)
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        checkout = self.client_for(self.alice).post(reverse("order-checkout", args=[order_id])).data
        Order.objects.filter(pk=order_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.place(self.bob, [(self.variant, 1)]).status_code, 201)

        payment = Payment.objects.get(pk=checkout["payment_id"])
        handle_event("fake", PaymentEvent(payment.provider_ref, "succeeded"))
        self.assertEqual(Payment.objects.get(pk=payment.pk).status, "refunded")
        self.assertEqual(Order.objects.get(pk=order_id).status, "expired")

    def test_late_payment_is_kept_when_stock_is_still_there(self):
        before = self.stock(self.variant)
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        checkout = self.client_for(self.alice).post(reverse("order-checkout", args=[order_id])).data
        Order.objects.filter(pk=order_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        APIClient().get(reverse("product-list"))  # triggers the release

        payment = Payment.objects.get(pk=checkout["payment_id"])
        handle_event("fake", PaymentEvent(payment.provider_ref, "succeeded"))
        self.assertEqual(Order.objects.get(pk=order_id).status, "paid")
        self.assertEqual(self.stock(self.variant), before - 1)

    def test_cancelling_a_paid_order_refunds_and_restocks(self):
        before = self.stock(self.variant)
        order_id = self.place(self.alice, [(self.variant, 2)]).data["id"]
        self.pay(self.alice, order_id)
        res = self.client_for(self.alice).post(reverse("order-cancel", args=[order_id]))
        self.assertEqual(res.data["status"], "cancelled")
        self.assertEqual(Payment.objects.get(order_id=order_id, status="refunded").refunded_amount, Decimal(res.data["total"]))
        self.assertEqual(self.stock(self.variant), before)

    def test_shipped_orders_cannot_be_cancelled(self):
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        self.pay(self.alice, order_id)
        staff = self.client_for(self.staff)
        self.assertEqual(staff.post(reverse("order-ship", args=[order_id]), {"tracking_number": "TRK1"}).status_code, 200)
        self.assertEqual(self.client_for(self.alice).post(reverse("order-cancel", args=[order_id])).status_code, 400)

    def test_only_staff_can_ship(self):
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        self.pay(self.alice, order_id)
        self.assertEqual(self.client_for(self.alice).post(reverse("order-ship", args=[order_id])).status_code, 403)

    def test_customers_only_see_their_own_orders(self):
        order_id = self.place(self.alice, [(self.variant, 1)]).data["id"]
        self.assertEqual(self.client_for(self.bob).get(reverse("order-detail", args=[order_id])).status_code, 404)
        staff_view = self.client_for(self.staff).get(reverse("order-detail", args=[order_id]))
        self.assertEqual(staff_view.data["customer"]["email"], "alice@example.com")

    def test_quantity_limit(self):
        res = self.place(self.alice, [(self.variant, 11)])
        self.assertEqual(res.status_code, 400)


@override_settings(PAYMENT_PROVIDER="stripe", STRIPE_SECRET_KEY="sk_test_dummy", STRIPE_WEBHOOK_SECRET="whsec_dummy")
class StripeWebhookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_all()
        cls.user = User.objects.create_user("carol@example.com", "a-long-password")

    def test_webhook_confirms_order(self):
        variant = Variant.objects.filter(stock__gte=1).first()
        client = APIClient()
        client.force_authenticate(self.user)
        order_id = client.post(
            reverse("order-list"),
            {"items": [{"variant": variant.id, "quantity": 1}], "shipping_method": "express", "address": ADDRESS},
            format="json",
        ).data["id"]

        intent = mock.Mock(id="pi_123", client_secret="pi_123_secret")
        with mock.patch("stripe.StripeClient") as stripe_client:
            stripe_client.return_value.v1.payment_intents.create.return_value = intent
            checkout = client.post(reverse("order-checkout", args=[order_id]))
        self.assertEqual(checkout.data["client_secret"], "pi_123_secret")

        event = mock.Mock(type="payment_intent.succeeded")
        event.data.object.id = "pi_123"
        with mock.patch("stripe.StripeClient") as stripe_client:
            stripe_client.return_value.construct_event.return_value = event
            res = APIClient().post(
                reverse("payment-stripe-webhook"), data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="t=1,v1=x"
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Order.objects.get(pk=order_id).status, "paid")

    def test_partial_refund_sends_the_amount(self):

        from apps.payments.services import refund

        variant = Variant.objects.filter(stock__gte=1).first()
        order = Order.objects.create(
            user=self.user, email="carol@example.com", full_name="Carol", address_line1="x", city="x", postal_code="0",
            country="IT", shipping_method_id=1, subtotal=100, shipping=0, total=100, currency="EUR", expires_at=timezone.now(),
        )
        payment = Payment.objects.create(order=order, provider="stripe", provider_ref="pi_9", amount=100, currency="EUR", status="succeeded")
        with mock.patch("stripe.StripeClient") as stripe_client:
            refund(payment, Decimal("40.00"))
            params = stripe_client.return_value.v1.refunds.create.call_args.kwargs["params"]
        self.assertEqual(params, {"payment_intent": "pi_9", "amount": 4000})
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.refunded_amount), ("succeeded", Decimal("40.00")))
        self.assertIsNotNone(variant)

    def test_invalid_signature_is_rejected(self):
        res = APIClient().post(
            reverse("payment-stripe-webhook"), data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="bad"
        )
        self.assertEqual(res.status_code, 400)

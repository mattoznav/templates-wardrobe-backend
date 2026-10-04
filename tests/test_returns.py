from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Variant
from apps.core.csvdata import load_all
from apps.orders.models import Order
from apps.payments.models import Payment

from .test_orders import ADDRESS

User = get_user_model()


@override_settings(PAYMENT_PROVIDER="fake")
class ReturnTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_all()
        cls.variant = Variant.objects.filter(stock__gte=5).order_by("id").first()
        cls.alice = User.objects.create_user("alice@example.com", "a-long-password")
        cls.bob = User.objects.create_user("bob@example.com", "a-long-password")
        cls.staff = User.objects.create_user("staff@example.com", "a-long-password", is_staff=True)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def delivered_order(self, quantity=2):
        client = self.client_for(self.alice)
        order = client.post(
            reverse("order-list"),
            {"items": [{"variant": self.variant.id, "quantity": quantity}], "shipping_method": "express", "address": ADDRESS},
            format="json",
        ).data
        payment_id = client.post(reverse("order-checkout", args=[order["id"]])).data["payment_id"]
        client.post(reverse("payment-fake-complete"), {"payment_id": payment_id}, format="json")
        staff = self.client_for(self.staff)
        staff.post(reverse("order-ship", args=[order["id"]]))
        return staff.post(reverse("order-deliver", args=[order["id"]])).data

    def ask(self, user, order, quantity=1, reason="too_small"):
        return self.client_for(user).post(
            reverse("return-list"),
            {"order": order["id"], "lines": [{"order_line": order["lines"][0]["id"], "quantity": quantity}], "reason": reason},
            format="json",
        )

    def test_receiving_a_return_restocks_and_refunds_the_pieces(self):
        order = self.delivered_order(quantity=2)
        stock_before = Variant.objects.get(pk=self.variant.pk).stock
        request = self.ask(self.alice, order, quantity=1)
        self.assertEqual(request.status_code, 201, request.data)

        res = self.client_for(self.staff).post(reverse("return-receive", args=[request.data["id"]]), {"staff_note": "Checked"})
        self.assertEqual(res.data["status"], "refunded")
        unit = Decimal(order["lines"][0]["unit_price"])
        self.assertEqual(Decimal(res.data["refund_amount"]), unit)
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock, stock_before + 1)
        payment = Payment.objects.get(order_id=order["id"])
        self.assertEqual((payment.status, payment.refunded_amount), ("succeeded", unit))

    def test_cannot_return_more_than_was_bought(self):
        order = self.delivered_order(quantity=1)
        self.assertEqual(self.ask(self.alice, order).status_code, 201)
        self.assertEqual(self.ask(self.alice, order).status_code, 400)

    def test_rejected_pieces_can_be_asked_again(self):
        order = self.delivered_order(quantity=1)
        request_id = self.ask(self.alice, order).data["id"]
        staff = self.client_for(self.staff)
        self.assertEqual(staff.post(reverse("return-reject", args=[request_id]), {"staff_note": ""}).status_code, 400)
        self.assertEqual(staff.post(reverse("return-reject", args=[request_id]), {"staff_note": "Worn"}).status_code, 200)
        self.assertEqual(self.ask(self.alice, order).status_code, 201)

    def test_return_window_closes(self):
        order = self.delivered_order()
        Order.objects.filter(pk=order["id"]).update(delivered_at=timezone.now() - timedelta(days=31))
        self.assertEqual(self.ask(self.alice, order).status_code, 400)

    def test_unshipped_orders_cannot_be_returned(self):
        client = self.client_for(self.alice)
        order = client.post(
            reverse("order-list"),
            {"items": [{"variant": self.variant.id, "quantity": 1}], "shipping_method": "standard", "address": ADDRESS},
            format="json",
        ).data
        self.assertEqual(self.ask(self.alice, order).status_code, 400)

    def test_customers_cannot_return_other_peoples_orders(self):
        order = self.delivered_order()
        self.assertEqual(self.ask(self.bob, order).status_code, 400)

    def test_only_staff_receive_returns(self):
        order = self.delivered_order()
        request_id = self.ask(self.alice, order).data["id"]
        self.assertEqual(self.client_for(self.alice).post(reverse("return-receive", args=[request_id])).status_code, 403)

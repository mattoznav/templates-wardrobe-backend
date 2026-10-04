from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Product, Variant
from apps.core.csvdata import load_all
from apps.orders.models import Order

User = get_user_model()


class CatalogueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_all()
        cls.staff = User.objects.create_user("staff@example.com", "a-long-password", is_staff=True)

    def staff_client(self):
        client = APIClient()
        client.force_authenticate(self.staff)
        return client

    def test_every_product_has_photos_with_credits_and_stock(self):
        for product in APIClient().get(reverse("product-list")).data:
            self.assertTrue(product["images"], product["slug"])
            for image in product["images"]:
                self.assertTrue(image["url"].startswith("https://images.unsplash.com/"))
                self.assertTrue(image["photographer"] and image["source_url"].startswith("https://unsplash.com/photos/"))
            self.assertTrue(product["variants"])

    def test_filters(self):
        client = APIClient()
        women = client.get(reverse("product-list"), {"department": "women"}).data
        self.assertTrue(women and all(p["department"] == "women" for p in women))
        sale = client.get(reverse("product-list"), {"on_sale": "1"}).data
        self.assertTrue(sale and all(p["compare_at_price"] for p in sale))
        cheap_first = client.get(reverse("product-list"), {"sort": "price_asc"}).data
        prices = [float(p["price"]) for p in cheap_first]
        self.assertEqual(prices, sorted(prices))
        knit = client.get(reverse("product-list"), {"collection": "the-quiet-season", "category": "knitwear"}).data
        self.assertTrue(knit and all(p["category"] == "knitwear" and "the-quiet-season" in p["collections"] for p in knit))

    def test_drafts_are_hidden_from_customers(self):
        Product.objects.filter(slug="satin-shirt").update(status=Product.Status.DRAFT)
        self.assertEqual(APIClient().get(reverse("product-detail", args=["satin-shirt"])).status_code, 404)
        self.assertEqual(self.staff_client().get(reverse("product-detail", args=["satin-shirt"])).status_code, 200)

    def test_staff_update_price_and_stock_in_one_request(self):
        client = self.staff_client()
        product = client.get(reverse("product-detail", args=["oxford-shirt"])).data
        variants = [{**v, "stock": 7} for v in product["variants"]]
        res = client.patch(
            reverse("product-detail", args=["oxford-shirt"]), {"price": "99.00", "variants": variants}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["price"], "99.00")
        self.assertTrue(all(v["stock"] == 7 for v in res.data["variants"]))

    def test_old_price_must_be_higher(self):
        res = self.staff_client().patch(reverse("product-detail", args=["oxford-shirt"]), {"compare_at_price": "10.00"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_customers_cannot_edit(self):
        customer = APIClient()
        customer.force_authenticate(User.objects.create_user("c@example.com", "a-long-password"))
        self.assertEqual(customer.patch(reverse("product-detail", args=["oxford-shirt"]), {"price": "1.00"}).status_code, 403)

    def test_stock_adjustments_cannot_go_negative(self):
        variant = Variant.objects.filter(stock=0).first() or Variant.objects.first()
        Variant.objects.filter(pk=variant.pk).update(stock=2)
        client = self.staff_client()
        self.assertEqual(client.post(reverse("inventory-adjust", args=[variant.pk]), {"delta": 5}).data["stock"], 7)
        self.assertEqual(client.post(reverse("inventory-adjust", args=[variant.pk]), {"delta": -8}).status_code, 400)

    def test_ordered_products_cannot_be_deleted(self):
        call_command("demo_orders", orders=20, stdout=open("/dev/null", "w"))
        slug = Order.objects.first().lines.first().product_slug
        self.assertEqual(self.staff_client().delete(reverse("product-detail", args=[slug])).status_code, 409)

    def test_dashboard(self):
        call_command("demo_orders", orders=30, stdout=open("/dev/null", "w"))
        res = self.staff_client().get(reverse("admin-summary"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["days"]), 14)
        self.assertTrue(res.data["has_sales"])
        self.assertEqual(APIClient().get(reverse("admin-summary")).status_code, 401)


class AccountTests(TestCase):
    def test_registering_twice_is_a_clear_error(self):
        data = {"email": "Dana@Example.com", "password": "a-long-password-1", "first_name": "Dana", "last_name": "Lee"}
        self.assertEqual(APIClient().post(reverse("register"), data).status_code, 201)
        res = APIClient().post(reverse("register"), {**data, "email": "dana@example.com"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("email", res.data)

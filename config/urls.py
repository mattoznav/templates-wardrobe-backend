from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import MeView, RegisterView
from apps.catalog.views import (
    CategoryViewSet,
    CollectionViewSet,
    ColourViewSet,
    InventoryViewSet,
    ProductViewSet,
    SizeViewSet,
)
from apps.core.dashboard import summary
from apps.core.views import editorial, health, store
from apps.orders.views import OrderViewSet, ShippingMethodViewSet, quote
from apps.payments import views as payments
from apps.returns.views import ReturnViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("colours", ColourViewSet, basename="colour")
router.register("sizes", SizeViewSet, basename="size")
router.register("collections", CollectionViewSet, basename="collection")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register("shipping-methods", ShippingMethodViewSet, basename="shipping-method")
router.register("orders", OrderViewSet, basename="order")
router.register("returns", ReturnViewSet, basename="return")

api = [
    path("", include(router.urls)),
    path("store/", store, name="store"),
    path("editorial/", editorial, name="editorial"),
    path("health/", health, name="health"),
    path("bag/quote/", quote, name="bag-quote"),
    path("admin/summary/", summary, name="admin-summary"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("payments/config/", payments.config, name="payment-config"),
    path("payments/fake/complete/", payments.fake_complete, name="payment-fake-complete"),
    path("payments/stripe/webhook/", payments.stripe_webhook, name="payment-stripe-webhook"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api)),
]

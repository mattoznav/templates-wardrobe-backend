"""Figures for the admin back office: sales by day, work waiting, stock running low."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.catalog.models import Product, Variant
from apps.catalog.views import stock_totals
from apps.orders.models import Order, OrderLine
from apps.orders.services import release_expired
from apps.returns.models import ReturnRequest

from .models import Store
from .permissions import IsStaff

SOLD = [Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED]


def day_start(day):
    return datetime.combine(day, time.min, timezone.get_current_timezone())


@api_view(["GET"])
@permission_classes([IsStaff])
def summary(request):
    """Sales of the last `days` (default 14, at most 90), today's figures and what needs attention."""
    try:
        days = max(1, min(int(request.query_params.get("days", 14)), 90))
    except ValueError:
        days = 14
    release_expired()
    today = timezone.localdate()
    first = today - timedelta(days=days - 1)

    paid = Order.objects.filter(status__in=SOLD, paid_at__gte=day_start(first))
    by_day = {d: {"orders": 0, "revenue": 0} for d in (first + timedelta(days=i) for i in range(days))}
    for paid_at, total in paid.values_list("paid_at", "total"):
        bucket = by_day.get(timezone.localtime(paid_at).date())
        if bucket is not None:
            bucket["orders"] += 1
            bucket["revenue"] += total
    series = [{"date": d, **v} for d, v in by_day.items()]

    todays = paid.filter(paid_at__gte=day_start(today))
    today_figures = todays.aggregate(orders=Count("id"), revenue=Coalesce(Sum("total"), Decimal("0")))
    today_figures["pieces"] = OrderLine.objects.filter(order__in=todays).aggregate(n=Coalesce(Sum("quantity"), 0))["n"]

    month_start = day_start(today - timedelta(days=29))
    top = (
        OrderLine.objects.filter(order__status__in=SOLD, order__paid_at__gte=month_start)
        .values("product_slug", "product_name")
        .annotate(
            units=Sum("quantity"),
            revenue=Sum(ExpressionWrapper(F("unit_price") * F("quantity"), output_field=DecimalField(max_digits=12, decimal_places=2))),
        )
        .order_by("-units")[:5]
    )
    images = {
        p.slug: (p.images.first().photo.url if p.images.exists() else "")
        for p in Product.objects.filter(slug__in=[t["product_slug"] for t in top]).prefetch_related("images__photo")
    }

    low = (
        Variant.objects.filter(product__status=Product.Status.ACTIVE, stock__lte=settings.LOW_STOCK_THRESHOLD)
        .select_related("product", "colour", "size")
        .order_by("stock", "product__name")[:8]
    )
    recent = Order.objects.exclude(status=Order.Status.PENDING).order_by("-created_at")[:6]
    store = Store.objects.first()

    return Response(
        {
            "currency": store.currency if store else "EUR",
            "days": series,
            "period": {
                "orders": sum(d["orders"] for d in series),
                "revenue": sum(d["revenue"] for d in series),
            },
            "today": today_figures,
            "to_ship": Order.objects.filter(status=Order.Status.PAID).count(),
            "in_transit": Order.objects.filter(status=Order.Status.SHIPPED).count(),
            "returns_open": ReturnRequest.objects.filter(status=ReturnRequest.Status.REQUESTED).count(),
            "stock": {**stock_totals(), "threshold": settings.LOW_STOCK_THRESHOLD},
            "low_stock": [
                {"id": v.id, "sku": v.sku, "product": v.product.name, "slug": v.product.slug, "colour": v.colour.name, "size": v.size.label, "stock": v.stock}
                for v in low
            ],
            "top_products": [{**t, "image": images.get(t["product_slug"], "")} for t in top],
            "recent_orders": [
                {"id": o.id, "reference": o.reference, "full_name": o.full_name, "status": o.status, "total": o.total, "created_at": o.created_at}
                for o in recent
            ],
            "orders_by_status": dict(Order.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")),
            "returns_by_reason": dict(
                ReturnRequest.objects.exclude(status=ReturnRequest.Status.REJECTED)
                .values_list("reason")
                .annotate(n=Count("id"))
                .values_list("reason", "n")
            ),
            "has_sales": Order.objects.filter(status__in=SOLD).exists(),
        }
    )

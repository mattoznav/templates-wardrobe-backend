from datetime import date, datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.catalog.models import Variant
from apps.core.permissions import IsStaff
from apps.payments.providers import get_provider
from apps.payments.services import PaymentError, start_checkout
from apps.returns.services import can_return, return_deadline, returnable_quantity

from . import services
from .models import Order, OrderLine, ShippingMethod


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = ["code", "name", "description", "price", "free_over_threshold", "days_min", "days_max"]


class OrderLineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    returnable = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = [
            "id", "variant", "product_name", "product_slug", "colour", "size", "sku", "image_url", "unit_price",
            "quantity", "line_total", "returnable",
        ]

    def get_returnable(self, line):
        return returnable_quantity(line)


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    shipping_method = ShippingMethodSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    can_return = serializers.SerializerMethodField()
    return_deadline = serializers.SerializerMethodField()
    returns = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "reference", "status", "status_label", "email", "full_name", "address_line1", "address_line2",
            "city", "postal_code", "country", "phone", "shipping_method", "subtotal", "shipping", "total", "currency",
            "lines", "expires_at", "created_at", "paid_at", "shipped_at", "delivered_at", "cancelled_at",
            "tracking_number", "can_cancel", "can_return", "return_deadline", "returns", "customer", "payments",
        ]

    @property
    def _staff(self):
        request = self.context.get("request")
        return bool(request and request.user.is_staff)

    def get_can_cancel(self, order):
        return order.status in (Order.Status.PENDING, Order.Status.PAID)

    def get_can_return(self, order):
        return can_return(order)

    def get_return_deadline(self, order):
        return return_deadline(order)

    def get_returns(self, order):
        return [
            {"id": r.id, "reference": r.reference, "status": r.status, "refund_amount": r.refund_amount, "created_at": r.created_at}
            for r in order.returns.all()
        ]

    def get_customer(self, order):
        # Only the back office sees the account behind the order
        if not self._staff:
            return None
        return {"email": order.user.email, "name": order.user.get_full_name()}

    def get_payments(self, order):
        if not self._staff:
            return None
        return [
            {"provider": p.provider, "status": p.status, "amount": p.amount, "refunded_amount": p.refunded_amount, "created_at": p.created_at}
            for p in order.payments.all()
        ]


class BagItemSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=20)


def bag_items(data: list[dict]) -> list[services.BagItem]:
    variants = Variant.objects.select_related("product", "colour", "size").prefetch_related("product__images__photo").in_bulk(
        [d["variant"] for d in data]
    )
    missing = [d["variant"] for d in data if d["variant"] not in variants]
    if missing:
        raise ValidationError({"items": f"Unknown variant: {missing[0]}."})
    return [services.BagItem(variants[d["variant"]], d["quantity"]) for d in data]


class QuoteRequestSerializer(serializers.Serializer):
    items = BagItemSerializer(many=True)
    shipping_method = serializers.SlugRelatedField(
        slug_field="code", queryset=ShippingMethod.objects.all(), required=False, allow_null=True
    )


class AddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    address_line1 = serializers.CharField(max_length=200)
    address_line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.RegexField(r"^[A-Za-z]{2}$", error_messages={"invalid": "Use the two-letter country code, for example IT."})
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class OrderCreateSerializer(serializers.Serializer):
    items = BagItemSerializer(many=True)
    shipping_method = serializers.SlugRelatedField(slug_field="code", queryset=ShippingMethod.objects.all())
    address = AddressSerializer()


@api_view(["POST"])
@permission_classes([AllowAny])
def quote(request):
    """Price a bag with current prices, stock and shipping. Nothing is reserved."""
    data = QuoteRequestSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    method = data.validated_data.get("shipping_method") or ShippingMethod.objects.first()
    result = services.quote(bag_items(data.validated_data["items"]), method)
    return Response(
        {
            "lines": result.lines,
            "subtotal": result.subtotal,
            "shipping": result.shipping,
            "total": result.total,
            "currency": result.currency,
            "shipping_method": method.code if method else None,
            "free_shipping_over": result.free_shipping_over,
            "problems": result.problems,
        }
    )


class OrderViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Customers see their own orders, staff see all of them.

    Filters: `status` (comma list). Staff only: `q` (reference, email or name), `date` (YYYY-MM-DD, day placed).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related("user", "shipping_method").prefetch_related(
            "lines", "payments", "returns", "lines__return_lines__request"
        )
        params = self.request.query_params
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        else:
            if q := params.get("q", "").strip():
                qs = qs.filter(Q(reference__iexact=q) | Q(email__icontains=q) | Q(full_name__icontains=q))
            if day := params.get("date"):
                try:
                    start = datetime.combine(date.fromisoformat(day), time.min, timezone.get_current_timezone())
                except ValueError:
                    raise ValidationError({"date": "Use the YYYY-MM-DD format."}) from None
                qs = qs.filter(created_at__gte=start, created_at__lt=start + timedelta(days=1))
        if statuses := [s for s in params.get("status", "").split(",") if s]:
            qs = qs.filter(status__in=statuses)
        return qs

    def list(self, request, *args, **kwargs):
        services.release_expired()
        return super().list(request, *args, **kwargs)

    def _respond(self, order, code=status.HTTP_200_OK):
        return Response(OrderSerializer(self.get_queryset().get(pk=order.pk), context=self.get_serializer_context()).data, status=code)

    def create(self, request, *args, **kwargs):
        """Reserve the stock for a few minutes, until the order is paid."""
        data = OrderCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            order = services.place_order(
                request.user,
                bag_items(data.validated_data["items"]),
                data.validated_data["shipping_method"],
                data.validated_data["address"],
            )
        except services.OutOfStock as exc:
            return Response({"detail": str(exc), "items": exc.items}, status=status.HTTP_409_CONFLICT)
        except services.OrderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(order, status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        """Start paying. Returns what the client needs to complete the payment."""
        order = self.get_object()
        try:
            payment, client_secret = start_checkout(order)
        except PaymentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {
                "payment_id": payment.id,
                "provider": payment.provider,
                "amount": payment.amount,
                "currency": payment.currency,
                "client_secret": client_secret,
                **get_provider(payment.provider).public_config(),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel before shipping. Paid orders are refunded in full."""
        try:
            order = services.cancel(self.get_object(), by_staff=request.user.is_staff)
        except services.OrderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(order)

    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    def ship(self, request, pk=None):
        try:
            order = services.ship(self.get_object(), str(request.data.get("tracking_number", "")))
        except services.OrderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(order)

    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    def deliver(self, request, pk=None):
        try:
            order = services.deliver(self.get_object())
        except services.OrderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._respond(order)


class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingMethod.objects.all()
    serializer_class = ShippingMethodSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "code"

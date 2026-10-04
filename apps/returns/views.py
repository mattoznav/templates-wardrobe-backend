from django.db.models import Q
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsStaff
from apps.orders.models import Order, OrderLine

from . import services
from .models import ReturnRequest


class ReturnLineSerializer(serializers.Serializer):
    order_line = serializers.IntegerField(source="order_line.id")
    product_name = serializers.CharField(source="order_line.product_name")
    product_slug = serializers.CharField(source="order_line.product_slug")
    colour = serializers.CharField(source="order_line.colour")
    size = serializers.CharField(source="order_line.size")
    sku = serializers.CharField(source="order_line.sku")
    image_url = serializers.CharField(source="order_line.image_url")
    unit_price = serializers.DecimalField(source="order_line.unit_price", max_digits=8, decimal_places=2)
    quantity = serializers.IntegerField()


class ReturnSerializer(serializers.ModelSerializer):
    lines = ReturnLineSerializer(many=True, read_only=True)
    order = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    value = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequest
        fields = [
            "id", "reference", "order", "status", "status_label", "reason", "reason_label", "note", "lines", "value",
            "refund_amount", "staff_note", "created_at", "closed_at",
        ]

    def get_order(self, r):
        return {"id": r.order_id, "reference": r.order.reference, "currency": r.order.currency, "email": r.order.email, "full_name": r.order.full_name}

    def get_value(self, r):
        return services.refund_value(r)


class PickSerializer(serializers.Serializer):
    order_line = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class ReturnCreateSerializer(serializers.Serializer):
    order = serializers.IntegerField()
    lines = PickSerializer(many=True)
    reason = serializers.ChoiceField(choices=ReturnRequest.Reason.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class StaffNoteSerializer(serializers.Serializer):
    staff_note = serializers.CharField(required=False, allow_blank=True, max_length=200)


class ReturnViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Customers request returns for their orders; staff receive and refund, or reject.

    Filters: `status`. Staff only: `q` (return or order reference, email).
    """

    serializer_class = ReturnSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ReturnRequest.objects.select_related("order").prefetch_related("lines__order_line")
        params = self.request.query_params
        if not self.request.user.is_staff:
            qs = qs.filter(order__user=self.request.user)
        elif q := params.get("q", "").strip():
            qs = qs.filter(Q(reference__iexact=q) | Q(order__reference__iexact=q) | Q(order__email__icontains=q))
        if s := params.get("status"):
            qs = qs.filter(status=s)
        return qs

    def create(self, request, *args, **kwargs):
        data = ReturnCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        orders = Order.objects.all() if request.user.is_staff else Order.objects.filter(user=request.user)
        order = orders.filter(pk=data.validated_data["order"]).first()
        if order is None:
            raise ValidationError({"order": "Order not found."})
        lines = OrderLine.objects.in_bulk([p["order_line"] for p in data.validated_data["lines"]])
        picks = []
        for p in data.validated_data["lines"]:
            if p["order_line"] not in lines:
                raise ValidationError({"lines": "Some pieces are not part of this order."})
            picks.append((lines[p["order_line"]], p["quantity"]))
        try:
            r = services.request_return(order, picks, data.validated_data["reason"], data.validated_data.get("note", ""))
        except services.ReturnError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReturnSerializer(self.get_queryset().get(pk=r.pk)).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    def receive(self, request, pk=None):
        """The parcel arrived in good shape: restock and refund."""
        note = StaffNoteSerializer(data=request.data)
        note.is_valid(raise_exception=True)
        try:
            r = services.receive(self.get_object(), note.validated_data.get("staff_note", ""))
        except services.ReturnError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReturnSerializer(self.get_queryset().get(pk=r.pk)).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    def reject(self, request, pk=None):
        note = StaffNoteSerializer(data=request.data)
        note.is_valid(raise_exception=True)
        try:
            r = services.reject(self.get_object(), note.validated_data.get("staff_note", ""))
        except services.ReturnError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReturnSerializer(self.get_queryset().get(pk=r.pk)).data)

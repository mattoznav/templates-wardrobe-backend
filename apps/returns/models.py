from django.db import models

from apps.orders.models import Order, OrderLine, new_reference


class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        REFUNDED = "refunded", "Received and refunded"
        REJECTED = "rejected", "Rejected"

    class Reason(models.TextChoices):
        TOO_SMALL = "too_small", "Too small"
        TOO_LARGE = "too_large", "Too large"
        NOT_AS_PICTURED = "not_as_pictured", "Not as pictured"
        CHANGED_MIND = "changed_mind", "Changed my mind"
        FAULTY = "faulty", "Faulty or damaged"
        OTHER = "other", "Other"

    reference = models.CharField(max_length=12, unique=True, default=new_reference, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="returns")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    reason = models.CharField(max_length=20, choices=Reason.choices)
    note = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    staff_note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference


class ReturnLine(models.Model):
    request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="lines")
    order_line = models.ForeignKey(OrderLine, on_delete=models.PROTECT, related_name="return_lines")
    quantity = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.request} {self.order_line.sku} x{self.quantity}"

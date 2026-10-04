from django.contrib import admin

from .models import ReturnLine, ReturnRequest


class ReturnLineInline(admin.TabularInline):
    model = ReturnLine
    extra = 0


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ["reference", "order", "status", "reason", "refund_amount", "created_at"]
    list_filter = ["status", "reason"]
    search_fields = ["reference", "order__reference"]
    inlines = [ReturnLineInline]

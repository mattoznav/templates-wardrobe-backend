from django.contrib import admin

from .models import Order, OrderLine, ShippingMethod


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ["variant", "product_name", "colour", "size", "sku", "unit_price", "quantity", "reserved"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["reference", "email", "status", "total", "currency", "created_at"]
    list_filter = ["status", "shipping_method"]
    search_fields = ["reference", "email", "full_name"]
    inlines = [OrderLineInline]


admin.site.register(ShippingMethod)

from django.contrib import admin

from .models import Category, Collection, Colour, Product, ProductImage, Size, Variant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "category", "price", "compare_at_price", "status", "is_new"]
    list_filter = ["department", "category", "status", "is_new"]
    search_fields = ["name", "slug", "variants__sku"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [ProductImageInline, VariantInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ["sku", "product", "colour", "size", "stock"]
    list_filter = ["colour", "size"]
    search_fields = ["sku", "product__name"]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ["title", "position"]
    filter_horizontal = ["products"]


admin.site.register(Category)
admin.site.register(Colour)
admin.site.register(Size)

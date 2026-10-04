from django.contrib import admin

from .models import Editorial, Photo, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "email", "currency"]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ["url", "photographer"]
    search_fields = ["url", "photographer"]


@admin.register(Editorial)
class EditorialAdmin(admin.ModelAdmin):
    list_display = ["key", "title"]

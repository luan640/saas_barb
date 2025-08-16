from django.contrib import admin
from .models import Shop, StaffMembership, Product, ProductPrice

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "owner__email")

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(StaffMembership)
class StaffMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "shop", "owner", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("user__email", "shop__name", "owner__email")

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "type", "default_price", "share_across_shops", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("name", "owner__email")

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ("product", "shop", "owner", "price")
    search_fields = ("product__name", "shop__name", "owner__email")

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

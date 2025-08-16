from django.contrib import admin
from .models import Shop, StaffMembership, Product, ProductPrice, Staff, Client

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "owner__email")

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "owner", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "user__email", "document")
    ordering = ("full_name", "user__email")

    @admin.display(description="Nome")
    def display_name(self, obj):
        return obj.full_name or getattr(obj.user, "email", "")

@admin.register(StaffMembership)
class StaffMembershipAdmin(admin.ModelAdmin):
    list_display = ("staff_name", "staff_email", "shop", "owner", "role", "is_active")
    list_filter = ("role", "is_active", "shop")
    search_fields = ("staff__full_name", "staff__user__email", "shop__name", "owner__email")
    autocomplete_fields = ("staff", "shop")

    @admin.display(description="Funcionário")
    def staff_name(self, obj):
        return obj.staff.full_name or obj.staff.user.email

    @admin.display(description="E-mail")
    def staff_email(self, obj):
        return obj.staff.user.email

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
    autocomplete_fields = ("product", "shop")
    
    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "owner", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "phone", "owner__email")

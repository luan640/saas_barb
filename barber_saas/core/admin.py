from django.contrib import admin

from .models import Store, Employee, Product


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "phone")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "store", "role")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "price")

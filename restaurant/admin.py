from django.contrib import admin

from .models import (
    InventoryItem, MenuItem, MenuItemIngredient, Order, OrderItem,
    Reservation, Table,
)


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_filter = ("category", "is_available")
    search_fields = ("name",)
    inlines = [MenuItemIngredientInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "unit", "low_stock_threshold", "is_low")
    search_fields = ("name",)

    @admin.display(boolean=True)
    def is_low(self, obj):
        return obj.is_low


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("number", "capacity", "status")
    list_filter = ("status",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "table", "party_size", "date_time", "status")
    list_filter = ("status", "table")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "customer_name", "status", "created_at", "total_price")
    list_filter = ("status",)
    inlines = [OrderItemInline]

    @admin.display(description="Total")
    def total_price(self, obj):
        return obj.total_price

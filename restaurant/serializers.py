from rest_framework import serializers

from .models import InventoryItem, MenuItem, Order, OrderItem, Reservation, Table


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ["id", "number", "capacity", "status"]


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ["id", "name", "description", "price", "category", "is_available"]


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ["id", "name", "quantity", "unit", "low_stock_threshold", "is_low"]


class ReservationSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source="table.number", read_only=True)

    class Meta:
        model = Reservation
        fields = ["id", "table", "table_number", "customer_name", "phone",
                  "party_size", "date_time", "status", "created_at"]
        read_only_fields = ["status", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="menu_item.name", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "name", "quantity", "unit_price", "subtotal"]
        read_only_fields = ["unit_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    table_number = serializers.CharField(source="table.number", read_only=True, default=None)

    class Meta:
        model = Order
        fields = ["id", "table", "table_number", "customer_name", "status",
                  "created_at", "items", "total_price"]
        read_only_fields = ["status", "created_at"]

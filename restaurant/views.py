from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    InventoryItem, MenuItem, MenuItemIngredient, Order, OrderItem,
    Reservation, Table, RESERVATION_DURATION,
)
from .serializers import (
    InventoryItemSerializer, MenuItemSerializer, OrderSerializer,
    ReservationSerializer, TableSerializer,
)


def home(request):
    return render(request, "index.html")


# ---------- Menu ----------
@api_view(["GET"])
def menu_list(request):
    items = MenuItem.objects.filter(is_available=True)
    return Response(MenuItemSerializer(items, many=True).data)


# ---------- Tables ----------
@api_view(["GET"])
def table_list(request):
    tables = Table.objects.all()
    return Response(TableSerializer(tables, many=True).data)


# ---------- Reservations ----------
@api_view(["GET", "POST"])
def reservation_list_create(request):
    if request.method == "GET":
        reservations = Reservation.objects.filter(status="active")
        return Response(ReservationSerializer(reservations, many=True).data)

    serializer = ReservationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    table = serializer.validated_data["table"]
    date_time = serializer.validated_data["date_time"]

    clashing = Reservation.objects.filter(table=table, status="active")
    for existing in clashing:
        if existing.overlaps(date_time):
            return Response(
                {"error": f"Table {table.number} is already reserved around that time."},
                status=400,
            )

    reservation = serializer.save(status="active")
    table.status = "reserved"
    table.save()
    return Response(ReservationSerializer(reservation).data, status=201)


@api_view(["DELETE"])
def reservation_cancel(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    reservation.status = "cancelled"
    reservation.save()
    # Free the table only if it has no other active/upcoming reservation right now
    if not Reservation.objects.filter(table=reservation.table, status="active").exists():
        if reservation.table.status == "reserved":
            reservation.table.status = "available"
            reservation.table.save()
    return Response({"message": "Reservation cancelled."})


# ---------- Orders ----------
@api_view(["GET", "POST"])
def order_list_create(request):
    if request.method == "GET":
        orders = Order.objects.all()
        status_filter = request.query_params.get("status")
        if status_filter:
            orders = orders.filter(status=status_filter)
        return Response(OrderSerializer(orders, many=True).data)

    table_id = request.data.get("table")
    customer_name = request.data.get("customer_name", "")
    items_data = request.data.get("items", [])

    if not items_data:
        return Response({"error": "Order must include at least one item."}, status=400)

    table = None
    if table_id:
        table = get_object_or_404(Table, pk=table_id)

    # Validate menu items and compute combined ingredient requirements
    menu_items = {}
    required = {}  # inventory_item_id -> total quantity needed
    for row in items_data:
        menu_item_id = row.get("menu_item")
        qty = int(row.get("quantity", 1))
        if qty <= 0:
            return Response({"error": "Quantity must be at least 1."}, status=400)
        menu_item = get_object_or_404(MenuItem, pk=menu_item_id, is_available=True)
        menu_items[menu_item_id] = (menu_item, menu_items.get(menu_item_id, (None, 0))[1] + qty)
        for ing in menu_item.ingredients.all():
            required[ing.inventory_item_id] = required.get(ing.inventory_item_id, Decimal("0")) + ing.quantity_required * qty

    # Check stock is sufficient before committing anything
    for inv_id, needed in required.items():
        inv = InventoryItem.objects.get(pk=inv_id)
        if inv.quantity < needed:
            return Response(
                {"error": f"Not enough {inv.name} in stock ({inv.quantity} {inv.unit} left, need {needed})."},
                status=400,
            )

    with transaction.atomic():
        order = Order.objects.create(table=table, customer_name=customer_name, status="pending")
        for menu_item, qty in menu_items.values():
            OrderItem.objects.create(order=order, menu_item=menu_item, quantity=qty, unit_price=menu_item.price)
        for inv_id, needed in required.items():
            inv = InventoryItem.objects.get(pk=inv_id)
            inv.quantity = inv.quantity - needed
            inv.save(update_fields=["quantity"])
        if table:
            table.status = "occupied"
            table.save()

    return Response(OrderSerializer(order).data, status=201)


@api_view(["GET"])
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return Response(OrderSerializer(order).data)


@api_view(["PATCH"])
def order_update_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.data.get("status")
    valid = [c[0] for c in Order.STATUS_CHOICES]
    if new_status not in valid:
        return Response({"error": f"Status must be one of {valid}."}, status=400)

    with transaction.atomic():
        if new_status == "cancelled" and order.status != "cancelled":
            # restock ingredients consumed by this order
            for item in order.items.all():
                for ing in item.menu_item.ingredients.all():
                    inv = InventoryItem.objects.get(pk=ing.inventory_item_id)
                    inv.quantity = inv.quantity + ing.quantity_required * item.quantity
                    inv.save(update_fields=["quantity"])
        order.status = new_status
        order.save()
        if new_status in ("paid", "cancelled") and order.table:
            still_reserved = Reservation.objects.filter(table=order.table, status="active").exists()
            order.table.status = "reserved" if still_reserved else "available"
            order.table.save()

    return Response(OrderSerializer(order).data)


# ---------- Reports (optional) ----------
@api_view(["GET"])
def report_daily_sales(request):
    today = timezone.localdate()
    orders = Order.objects.filter(created_at__date=today, status="paid")
    total = sum((o.total_price for o in orders), Decimal("0.00"))
    return Response({"date": str(today), "orders_paid": orders.count(), "revenue": total})


@api_view(["GET"])
def report_low_stock(request):
    items = [i for i in InventoryItem.objects.all() if i.is_low]
    return Response(InventoryItemSerializer(items, many=True).data)

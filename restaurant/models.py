from datetime import timedelta
from decimal import Decimal

from django.db import models

RESERVATION_DURATION = timedelta(hours=2)


class Table(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("reserved", "Reserved"),
    ]

    number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="available")

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Table {self.number}"


class InventoryItem(models.Model):
    name = models.CharField(max_length=100, unique=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default="pcs")  # kg, ltr, pcs...
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=5)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def is_low(self):
        return self.quantity <= self.low_stock_threshold


class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ("starter", "Starter"),
        ("main", "Main Course"),
        ("dessert", "Dessert"),
        ("beverage", "Beverage"),
    ]

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="main")
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class MenuItemIngredient(models.Model):
    """How much of an inventory item one unit of a menu item consumes."""
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="ingredients")
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("menu_item", "inventory_item")

    def __str__(self):
        return f"{self.menu_item} needs {self.quantity_required} {self.inventory_item.unit} {self.inventory_item.name}"


class Reservation(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("cancelled", "Cancelled")]

    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name="reservations")
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    party_size = models.PositiveIntegerField(default=2)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date_time"]

    def __str__(self):
        return f"{self.customer_name} - {self.table} @ {self.date_time}"

    def overlaps(self, other_start):
        """True if other_start falls within this reservation's 2-hour window (or vice versa)."""
        this_end = self.date_time + RESERVATION_DURATION
        other_end = other_start + RESERVATION_DURATION
        return self.date_time < other_end and other_start < this_end


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("preparing", "Preparing"),
        ("served", "Served"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer_name = models.CharField(max_length=120, blank=True)  # for takeaway orders
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} ({self.status})"

    @property
    def total_price(self):
        return sum((item.subtotal for item in self.items.all()), Decimal("0.00"))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)  # snapshot at order time

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

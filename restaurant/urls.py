from django.urls import path

from . import views

urlpatterns = [
    path("menu/", views.menu_list),
    path("tables/", views.table_list),
    path("reservations/", views.reservation_list_create),
    path("reservations/<int:reservation_id>/", views.reservation_cancel),
    path("orders/", views.order_list_create),
    path("orders/<int:order_id>/", views.order_detail),
    path("orders/<int:order_id>/status/", views.order_update_status),
    path("reports/daily-sales/", views.report_daily_sales),
    path("reports/low-stock/", views.report_low_stock),
]

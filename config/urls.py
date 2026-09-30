from django.contrib import admin
from django.urls import include, path

from restaurant import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("restaurant.urls")),
    path("", views.home),
]

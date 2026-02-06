from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.conf import settings

from .models import Product, Sale
from .views import build_monthly_history, ProductSimulationMixin

@admin.register(Product)
class ProductAdmin(ProductSimulationMixin, admin.ModelAdmin):
    list_display = ("sku", "name", "category", "stock", "created_at")
    search_fields = ("sku", "name", "category")
    list_filter = ("category", "created_at")
    ordering = ("-created_at",)

    
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "serial_number", "client_name", "total_price")
    list_filter = ("date", "product")
    search_fields = ("product__sku", "product__name", "serial_number", "client_name")
    ordering = ("-date",)

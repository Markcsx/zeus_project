from datetime import date
from uuid import uuid4

from django.db import models, transaction
from django.db.models import F
from django.utils import timezone


class Product(models.Model):
    sku = models.CharField(max_length=64, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    stock_min = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales")
    date = models.DateField(default=date.today)
    serial_number = models.CharField(max_length=64, unique=True, default="")
    client_name = models.CharField(max_length=255, blank=True, default="")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Sale({self.product.sku}, {self.date})"
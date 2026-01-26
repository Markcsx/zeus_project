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
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = str(uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales")
    date = models.DateField(default=date.today)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Sale({self.product.sku}, {self.date}, {self.quantity})"

    def save(self, *args, **kwargs):
        """Auto-ajusta stock del producto al crear/editar la venta."""
        with transaction.atomic():
            if self.pk:
                prev = Sale.objects.select_for_update().get(pk=self.pk)
                delta = self.quantity - prev.quantity  # venta nueva adicional
            else:
                delta = self.quantity

            super().save(*args, **kwargs)
            Product.objects.filter(pk=self.product_id).update(stock=F("stock") - delta)

    def delete(self, *args, **kwargs):
        """Devuelve stock al borrar la venta."""
        with transaction.atomic():
            qty = self.quantity
            product_id = self.product_id
            super().delete(*args, **kwargs)
            Product.objects.filter(pk=product_id).update(stock=F("stock") + qty)

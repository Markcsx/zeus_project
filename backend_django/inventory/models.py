from datetime import date

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone


class Product(models.Model):
    sku = models.CharField(max_length=64, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_initial = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    @staticmethod
    def _sku_part(value, fallback):
        letters = "".join(ch for ch in (value or "").upper() if "A" <= ch <= "Z")
        return (letters[:3] or fallback).ljust(3, "X")

    def _generate_sku(self):
        category_part = self._sku_part(self.category, "AUT")
        name_part = self._sku_part(self.name, "PRD")
        prefix = f"{category_part}-{name_part}"
        used_numbers = []

        existing = Product.objects.filter(sku__startswith=f"{prefix}-").values_list("sku", flat=True)
        for sku in existing:
            try:
                used_numbers.append(int(str(sku).rsplit("-", 1)[1]))
            except (IndexError, ValueError):
                continue

        next_number = (max(used_numbers) + 1) if used_numbers else Product.objects.count() + 1
        while True:
            candidate = f"{prefix}-{next_number:03d}"
            if not Product.objects.filter(sku=candidate).exists():
                return candidate
            next_number += 1

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self._generate_sku()
        if self._state.adding and self.stock_initial and not self.stock:
            self.stock = self.stock_initial
        super().save(*args, **kwargs)

    @property
    def units_sold_total(self):
        if not self.pk:
            return 0
        return self.sales.aggregate(total=Sum("quantity"))["total"] or 0

    @property
    def stock_received_total(self):
        if not self.pk:
            return 0
        return self.stock_movements.aggregate(total=Sum("quantity"))["total"] or 0

    def recalculate_stock(self, save=True):
        available = int(self.stock_initial or 0) + int(self.stock_received_total)
        self.stock = max(available - int(self.units_sold_total), 0)
        if save:
            Product.objects.filter(pk=self.pk).update(stock=self.stock)
        return self.stock

    def __str__(self):
        return self.sku or self.name


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales")
    date = models.DateField(default=date.today)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    serial_number = models.CharField(max_length=64, unique=True, default="")
    client_name = models.CharField(max_length=255, blank=True, default="")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Sale({self.product.sku}, {self.date}, qty={self.quantity})"


class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_movements")
    date = models.DateField(default=date.today)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Restock({self.product.sku}, {self.quantity}, {self.date})"


@receiver(post_save, sender=Sale)
@receiver(post_delete, sender=Sale)
@receiver(post_save, sender=StockMovement)
@receiver(post_delete, sender=StockMovement)
def update_product_stock(sender, instance, **kwargs):
    instance.product.recalculate_stock()


@receiver(post_save, sender=Product)
def update_product_stock_after_product_save(sender, instance, raw=False, **kwargs):
    if raw:
        return
    instance.recalculate_stock()

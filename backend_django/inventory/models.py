from datetime import date

from django.core.validators import MinValueValidator
from django.db import models
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

    @staticmethod
    def _sku_part(value, fallback):
        letters = "".join(ch for ch in (value or "").upper() if "A" <= ch <= "Z")
        return (letters[:3] or fallback).ljust(3, "X")

    def _generate_sku(self):
        """Return an autoparts-style SKU like FIL-ACE-011."""
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
        super().save(*args, **kwargs)

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

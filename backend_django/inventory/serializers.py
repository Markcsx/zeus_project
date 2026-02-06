from rest_framework import serializers
from .models import Product, Sale


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "sku", "name", "category", "description", "price", "stock", "stock_min", "created_at"]


class SaleSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = Sale
        fields = ["id", "product", "product_sku", "date", "quantity", "created_at"]

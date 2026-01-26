from django.shortcuts import render
from rest_framework import viewsets
from .models import Product, SalesRecord
from .serializers import ProductSerializer, SalesRecordSerializer


# Create your views here.
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer


class SalesRecordViewSet(viewsets.ModelViewSet):
    queryset = SalesRecord.objects.all().order_by('-sale_date')
    serializer_class = SalesRecordSerializer
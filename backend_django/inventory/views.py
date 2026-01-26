from collections import defaultdict
from datetime import date
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product, Sale
from .serializers import ProductSerializer, SaleSerializer


def _month_iter(start: date, end: date):
    """Yield (year, month) pairs from start to end inclusive."""
    year, month = start.year, start.month
    while (year < end.year) or (year == end.year and month <= end.month):
        yield year, month
        month = month + 1 if month < 12 else 1
        year = year + 1 if month == 1 else year


def build_monthly_history(product: Product):
    sales_qs = Sale.objects.filter(product=product).order_by("date")
    if not sales_qs.exists():
        return []

    first_date = sales_qs.first().date
    last_date = sales_qs.last().date

    monthly_totals = defaultdict(int)
    for sale in sales_qs:
        monthly_totals[(sale.date.year, sale.date.month)] += sale.quantity

    history = [monthly_totals.get((y, m), 0) for y, m in _month_iter(first_date, last_date)]
    return history


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        product = self.get_object()
        horizon = int(request.query_params.get("horizon", 12))
        freq = request.query_params.get("freq", "M")

        history = build_monthly_history(product)
        payload = {
            "sku": product.sku,
            "history": history,
            "horizon": horizon,
            "freq": freq,
        }

        try:
            import requests  # import local para no bloquear comandos si falta el paquete
        except ImportError:
            return Response(
                {"detail": "Falta el paquete 'requests'. Instálalo con pip install requests."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            response = requests.post(f"{settings.FASTAPI_URL}/forecast", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            return Response(
                {"detail": f"No se pudo contactar al servicio de pronóstico: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data)


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("product").all().order_by("-date")
    serializer_class = SaleSerializer

from collections import defaultdict
from datetime import date, datetime
from typing import Optional

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


def build_monthly_history(product: Product, start_date: Optional[date] = None):
    sales_qs = Sale.objects.filter(product=product).order_by("date")
    if start_date:
        sales_qs = sales_qs.filter(date__gte=start_date)
    if not sales_qs.exists():
        return []

    first_date = sales_qs.first().date
    last_date = sales_qs.last().date

    monthly_totals = defaultdict(int)
    for sale in sales_qs:
        monthly_totals[(sale.date.year, sale.date.month)] += sale.quantity

    history = [monthly_totals.get((y, m), 0) for y, m in _month_iter(first_date, last_date)]
    return history


class ProductSimulationMixin:
    """Helper mixin to simulate stock trajectory month by month."""

    @staticmethod
    def simulate_stock(start_stock, demand, incoming=None):
        incoming = incoming or []
        projection = []
        stock = start_stock
        oos_month = None

        for idx, qty in enumerate(demand):
            if idx < len(incoming):
                stock += incoming[idx]
            stock = max(stock - qty, 0)
            projection.append(stock)
            if stock == 0 and oos_month is None and qty > 0:
                oos_month = idx
        return projection, oos_month


class ProductViewSet(ProductSimulationMixin, viewsets.ModelViewSet):
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
            import requests  # lazy import para no romper makemigrations si falta
            response = requests.post(f"{settings.FASTAPI_URL}/forecast", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
        except ImportError:
            return Response(
                {"detail": "Falta el paquete 'requests'. Instálalo con pip install requests."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except requests.RequestException as exc:
            return Response(
                {"detail": f"No se pudo contactar al servicio de pronóstico: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data)

    @action(detail=True, methods=["get", "post"])
    def simulate(self, request, pk=None):
        """
        Simula el stock para los próximos meses.
        Body opcional:
        {
          "horizon": 12,
          "planned": [10, 8, ...],   # demanda manual; si se omite se usa forecast
          "incoming": [0, 20, ...]   # reposiciones por mes
        }
        """
        product = self.get_object()
        data_source = request.data if request.method == "POST" else request.query_params
        horizon = int(data_source.get("horizon", 12))
        planned = data_source.get("planned")
        incoming = data_source.get("incoming", [])
        start_date_param = data_source.get("start_date")
        current_stock = data_source.get("current_stock")

        start_date = None
        if start_date_param:
            try:
                start_date = datetime.fromisoformat(str(start_date_param)).date()
            except ValueError:
                return Response({"detail": "start_date debe ser YYYY-MM o YYYY-MM-DD"}, status=400)

        if current_stock is not None:
            try:
                stock_override = int(current_stock)
            except ValueError:
                return Response({"detail": "current_stock debe ser entero"}, status=400)
        else:
            stock_override = product.stock

        if planned is not None:
            demand = [max(float(x), 0) for x in planned][:horizon]
            if len(demand) < horizon:
                demand += [0.0] * (horizon - len(demand))
        else:
            history = build_monthly_history(product, start_date=start_date)
            payload = {
                "sku": product.sku,
                "history": history,
                "horizon": horizon,
                "freq": request.data.get("freq", "M"),
            }
            try:
                import requests
                response = requests.post(f"{settings.FASTAPI_URL}/forecast", json=payload, timeout=10)
                response.raise_for_status()
                demand = response.json().get("forecast", [])
            except ImportError:
                return Response(
                    {"detail": "Falta el paquete 'requests'. Instálalo con pip install requests."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except requests.RequestException as exc:
                return Response(
                    {"detail": f"No se pudo contactar al servicio de pronóstico: {exc}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        if len(demand) < horizon:
            demand += [0.0] * (horizon - len(demand))

        stock_projection, oos_month = self.simulate_stock(
            start_stock=stock_override,
            demand=demand[:horizon],
            incoming=incoming,
        )

        restock_suggestions = []
        if oos_month is not None:
            for idx, (stock_level, d) in enumerate(zip(stock_projection, demand)):
                if stock_level <= 0 and d > 0:
                    suggested_qty = int(d * 1.2)  # demanda + 20% colchón
                    restock_suggestions.append(
                        {"month_index": idx, "suggested_order_qty": suggested_qty}
                    )

        return Response(
            {
                "sku": product.sku,
                "horizon": horizon,
                "demand": demand[:horizon],
                "incoming": incoming,
                "stock_start": stock_override,
                "stock_projection": stock_projection,
                "out_of_stock_month_index": oos_month,
                "restock_suggestions": restock_suggestions,
                "start_date": start_date.isoformat() if start_date else None,
            }
        )


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("product").all().order_by("-date")
    serializer_class = SaleSerializer

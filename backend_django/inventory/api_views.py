from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product, Sale
from .serializers import ProductSerializer, SaleSerializer


def next_month(first_day: date) -> date:
    year = first_day.year + (1 if first_day.month == 12 else 0)
    month = 1 if first_day.month == 12 else first_day.month + 1
    return date(year, month, 1)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        """
        Predice ventas del próximo mes calculando unidades vendidas por mes
        (total_price / price del producto) y calcula el stock necesario para cubrirlas.
        """
        product = self.get_object()
        sales = Sale.objects.filter(product=product).order_by("date")
        price = product.price or Decimal("1")

        monthly_units = defaultdict(Decimal)
        for s in sales:
            units = (s.total_price or Decimal("0")) / price if price else Decimal("0")
            # guardamos con max(0, units) por si precio negativo
            units = max(units, Decimal("0"))
            monthly_units[(s.date.year, s.date.month)] += units

        history = []
        for (y, m) in sorted(monthly_units.keys()):
            history.append({"month": f"{y}-{m:02d}", "total_units": float(monthly_units[(y, m)])})

        forecast_units = int(round(history[-1]["total_units"])) if history else 0

        last_sale_date = sales.last().date if sales.exists() else date.today()
        target_month = next_month(last_sale_date.replace(day=1))

        stock_needed = max(forecast_units - product.stock, 0)

        return Response(
            {
                "product_id": product.id,
                "sku": product.sku,
                "current_stock": product.stock,
                "forecast_month": target_month.strftime("%Y-%m"),
                "predicted_sales_units": forecast_units,
                "stock_shortage": stock_needed,
                "stock_required": forecast_units,
                "history": history,
            }
        )


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("product").all().order_by("-date")
    serializer_class = SaleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        sale_id = params.get("id")
        if sale_id:
            try:
                qs = qs.filter(id=int(sale_id))
            except ValueError:
                pass  # id inválido: ignoramos filtro

        client = params.get("client_name")
        if client:
            qs = qs.filter(client_name__icontains=client.strip())

        date_str = params.get("date")
        if date_str:
            try:
                qs = qs.filter(date=datetime.fromisoformat(date_str).date())
            except ValueError:
                pass  # fecha inválida: ignoramos filtro

        return qs

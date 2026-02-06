from datetime import date, datetime

from django.db.models import Count
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
        Predice ventas del próximo mes usando el promedio mensual histórico
        (conteo de ventas) y calcula stock necesario para cubrirlas.
        """
        product = self.get_object()
        sales_qs = list(
            Sale.objects.filter(product=product)
            .values("date__year", "date__month")
            .annotate(total=Count("id"))
            .order_by("date__year", "date__month")
        )

        history = [row["total"] for row in sales_qs]
        # Predicción simple: repetir el total del último mes observado
        forecast_units = history[-1] if history else 0

        last_sale_date = (
            Sale.objects.filter(product=product).order_by("-date").first().date if history else date.today()
        )
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
                "history": [
                    {
                        "month": f"{row['date__year']}-{row['date__month']:02d}",
                        "total_sales": row["total"],
                    }
                    for row in sales_qs
                ],
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

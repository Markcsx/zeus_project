from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response

from .forecasting import ForecastingDependencyError, lstm_forecast
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

        monthly_units = defaultdict(Decimal)
        for s in sales:
            monthly_units[(s.date.year, s.date.month)] += Decimal(s.quantity or 0)

        history = []
        for (y, m) in sorted(monthly_units.keys()):
            history.append({"month": f"{y}-{m:02d}", "total_units": float(monthly_units[(y, m)])})

        try:
            forecast = lstm_forecast((item["total_units"] for item in history), horizon=12)
        except ForecastingDependencyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        forecast_units = int(round(forecast.values[0])) if forecast.values else 0

        last_sale_date = sales.last().date if sales.exists() else date.today()
        target_month = next_month(last_sale_date.replace(day=1))
        annual_forecast = []
        forecast_month = target_month
        for raw_units in forecast.values:
            monthly_units = int(round(raw_units))
            annual_forecast.append(
                {
                    "month": forecast_month.strftime("%Y-%m"),
                    "predicted_sales_units": monthly_units,
                    "stock_required": monthly_units,
                    "stock_shortage": max(monthly_units - product.stock, 0),
                }
            )
            forecast_month = next_month(forecast_month)

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
                "forecast_model": forecast.method,
                "forecast_lookback": forecast.lookback,
                "forecast_epochs": forecast.epochs,
                "history_points": forecast.history_points,
                "training_samples": forecast.training_samples,
                "forecast_message": forecast.message,
                "annual_forecast": annual_forecast,
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

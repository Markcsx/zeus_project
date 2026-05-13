from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .forecasting import ForecastingDependencyError, lstm_forecast
from .models import Product, Sale, StockMovement
from .serializers import ProductSerializer, SaleSerializer


def next_month(first_day: date) -> date:
    year = first_day.year + (1 if first_day.month == 12 else 0)
    month = 1 if first_day.month == 12 else first_day.month + 1
    return date(year, month, 1)


def parse_month(month_value: str):
    try:
        return datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError):
        return None


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        product = self.get_object()
        sales = Sale.objects.filter(product=product).order_by("date")

        monthly_units = defaultdict(Decimal)
        for sale in sales:
            monthly_units[(sale.date.year, sale.date.month)] += Decimal(sale.quantity or 0)

        history = [
            {"month": f"{year}-{month:02d}", "total_units": float(monthly_units[(year, month)])}
            for year, month in sorted(monthly_units.keys())
        ]

        try:
            forecast = lstm_forecast((item["total_units"] for item in history), horizon=12)
        except ForecastingDependencyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        forecast_units = int(round(forecast.values[0])) if forecast.values else 0
        last_sale_date = sales.last().date if sales.exists() else date.today()
        requested_month = parse_month(request.query_params.get("start_month"))
        target_month = requested_month or next_month(last_sale_date.replace(day=1))
        annual_forecast = []
        forecast_month = target_month
        projected_stock = product.stock

        for raw_units in forecast.values:
            monthly_units_forecast = int(round(raw_units))
            stock_shortage = max(monthly_units_forecast - projected_stock, 0)
            stock_after_month = max(projected_stock - monthly_units_forecast, 0)
            annual_forecast.append(
                {
                    "month": forecast_month.strftime("%Y-%m"),
                    "predicted_sales_units": monthly_units_forecast,
                    "stock_required": monthly_units_forecast,
                    "starting_stock": projected_stock,
                    "stock_shortage": stock_shortage,
                    "recommended_restock": stock_shortage,
                    "stock_after_month": stock_after_month,
                }
            )
            projected_stock = stock_after_month
            forecast_month = next_month(forecast_month)

        stock_needed = annual_forecast[0]["stock_shortage"] if annual_forecast else max(forecast_units - product.stock, 0)

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

    @action(detail=True, methods=["post"])
    def restock(self, request, pk=None):
        product = self.get_object()
        try:
            quantity = int(request.data.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0
        if quantity <= 0:
            return Response({"quantity": ["Debe ser mayor que cero."]}, status=status.HTTP_400_BAD_REQUEST)

        note = str(request.data.get("note", "")).strip()
        StockMovement.objects.create(product=product, quantity=quantity, note=note)
        product.refresh_from_db()
        return Response(ProductSerializer(product).data)


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
                pass

        client = params.get("client_name")
        if client:
            qs = qs.filter(client_name__icontains=client.strip())

        product_id = params.get("product")
        if product_id:
            try:
                qs = qs.filter(product_id=int(product_id))
            except ValueError:
                pass

        date_str = params.get("date")
        if date_str:
            try:
                qs = qs.filter(date=datetime.fromisoformat(date_str).date())
            except ValueError:
                pass

        return qs

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Product, Sale
from .serializers import (
    ProductSerializer,
    SaleSerializer,
)


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


def single_month_bootstrap_forecast(base_total: float, source_date: date, start_month: date, horizon: int):
    """Fallback para historia de un solo mes: escala por dias del mes origen."""
    days_in_source = calendar.monthrange(source_date.year, source_date.month)[1] or 1
    avg_daily = base_total / days_in_source

    forecasts = []
    current = start_month
    for _ in range(horizon):
        days_in_month = calendar.monthrange(current.year, current.month)[1] or 1
        forecasts.append(round(avg_daily * days_in_month, 2))
        current = (current + timedelta(days=32)).replace(day=1)
    return forecasts


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
        evaluate = request.query_params.get("evaluate", "false").lower() == "true"

        history = build_monthly_history(product)
        last_date = (
            Sale.objects.filter(product=product).order_by("-date").first().date if history else date.today()
        )
        start_month = (last_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        model_name = "ETS"
        metrics_payload = None

        if len(history) == 1:
            forecast_values = single_month_bootstrap_forecast(
                base_total=history[0],
                source_date=last_date,
                start_month=start_month,
                horizon=horizon,
            )
            data = {"forecast": forecast_values}
            model_name = "BASELINE"
        else:
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
                    {"detail": "Falta el paquete 'requests'. Instalalo con pip install requests."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except requests.RequestException as exc:
                return Response(
                    {"detail": f"No se pudo contactar al servicio de pronostico: {exc}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        forecast_values = data.get("forecast", [])

        forecast_objs = []
        for i, value in enumerate(forecast_values):
            forecast_date = (start_month + timedelta(days=32 * i)).replace(day=1)
            forecast_objs.append(
                Forecast(
                    product=product,
                    model_name=model_name,
                    forecast_date=forecast_date,
                    forecast_value=value,
                )
            )
        if forecast_objs:
            Forecast.objects.bulk_create(forecast_objs)

        if evaluate and len(history) >= 6 and model_name == "ETS":
            # simple hold-out: ultimos test_len puntos para evaluar
            test_len = min(3, len(history) // 3) or 1
            train_hist = history[:-test_len]
            test_hist = history[-test_len:]
            eval_payload = {
                "sku": product.sku,
                "history": train_hist,
                "horizon": test_len,
                "freq": freq,
            }
            try:
                import requests
                import time
                import numpy as np

                t0 = time.perf_counter()
                r2 = requests.post(f"{settings.FASTAPI_URL}/forecast", json=eval_payload, timeout=10)
                r2.raise_for_status()
                pred_eval = r2.json().get("forecast", [])
                elapsed = time.perf_counter() - t0
                if len(pred_eval) >= test_len:
                    y_true = np.array(test_hist, dtype=float)
                    y_pred = np.array(pred_eval[:test_len], dtype=float)
                    mae = float(np.mean(np.abs(y_true - y_pred)))
                    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
                    mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100)

                    period_label = last_date.strftime("%Y-%m")
                    metric_obj = ForecastMetric.objects.create(
                        product=product,
                        period=period_label,
                        method="ETS",
                        mae=mae,
                        rmse=rmse,
                        mape=mape,
                        prediction_time_seconds=elapsed,
                    )
                    metrics_payload = ForecastMetricSerializer(metric_obj).data
            except Exception as exc:  # noqa: BLE001
                metrics_payload = {"error": str(exc)}

        return Response(
            {
                "forecast": forecast_values,
                "model": model_name,
                "horizon": horizon,
                "history_length": len(history),
                "metrics": metrics_payload,
            }
        )

    @action(detail=True, methods=["get", "post"])
    def simulate(self, request, pk=None):
        """
        Simula el stock para los proximos meses.
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
            if len(history) == 1:
                sales_qs = Sale.objects.filter(product=product)
                if start_date:
                    sales_qs = sales_qs.filter(date__gte=start_date)
                base_date = sales_qs.order_by("-date").first().date if sales_qs.exists() else date.today()
                start_month = (base_date.replace(day=1) + timedelta(days=32)).replace(day=1)
                demand = single_month_bootstrap_forecast(
                    base_total=history[0],
                    source_date=base_date,
                    start_month=start_month,
                    horizon=horizon,
                )
            else:
                payload = {
                    "sku": product.sku,
                    "history": history,
                    "horizon": horizon,
                    "freq": data_source.get("freq", "M"),
                }
                try:
                    import requests
                    response = requests.post(f"{settings.FASTAPI_URL}/forecast", json=payload, timeout=10)
                    response.raise_for_status()
                    demand = response.json().get("forecast", [])
                except ImportError:
                    return Response(
                        {"detail": "Falta el paquete 'requests'. Instalalo con pip install requests."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                except requests.RequestException as exc:
                    return Response(
                        {"detail": f"No se pudo contactar al servicio de pronostico: {exc}"},
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
                    suggested_qty = int(d * 1.2)  # demanda + 20% colchon
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

    @action(detail=True, methods=["get"])
    def metrics(self, request, pk=None):
        """Devuelve métricas guardadas para el producto."""
        product = self.get_object()
        metrics = product.metrics.all()
        serializer = ForecastMetricSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def forecasts(self, request, pk=None):
        """Devuelve últimos pronósticos guardados para el producto."""
        product = self.get_object()
        forecasts = product.forecasts.all()[:50]
        serializer = ForecastSerializer(forecasts, many=True)
        return Response(serializer.data)


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("product").all().order_by("-date")
    serializer_class = SaleSerializer

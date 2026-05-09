from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .forecasting import ForecastResult
from .models import Product, Sale


class ProductForecastTests(TestCase):
    def test_auto_sku_uses_autoparts_format(self):
        product = Product.objects.create(
            name="Filtro de aire deportivo",
            category="Filtros",
            price=Decimal("45.00"),
        )

        self.assertRegex(product.sku, r"^FIL-FIL-\d{3}$")

    def test_auto_sku_increments_for_same_prefix(self):
        first = Product.objects.create(name="Sensor de temperatura", category="Sensores")
        second = Product.objects.create(name="Sensor de presion", category="Sensores")

        self.assertEqual(first.sku, "SEN-SEN-001")
        self.assertEqual(second.sku, "SEN-SEN-002")

    def create_sale(self, product, sale_date, units):
        Sale.objects.create(
            product=product,
            date=sale_date,
            quantity=units,
            serial_number=f"S-{sale_date:%Y%m}",
            total_price=product.price * Decimal(units),
        )

    def test_forecast_uses_lstm_when_history_is_sufficient(self):
        product = Product.objects.create(name="Mouse", price=Decimal("10.00"), stock=3)
        for month, units in enumerate([4, 7, 6, 9, 8, 11], start=1):
            self.create_sale(product, date(2026, month, 1), units)

        forecast_result = ForecastResult(
            values=[12.0, 15.0, 18.0, 10.0, 22.0, 24.0, 30.0, 28.0, 16.0, 19.0, 35.0, 40.0],
            method="LSTM_KERAS_TENSORFLOW",
            lookback=12,
            epochs=40,
            history_points=6,
            training_samples=4,
        )
        with patch("inventory.api_views.lstm_forecast", return_value=forecast_result):
            response = self.client.get(reverse("product-forecast", args=[product.pk]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["forecast_model"], "LSTM_KERAS_TENSORFLOW")
        self.assertEqual(data["history_points"], 6)
        self.assertEqual(data["forecast_lookback"], 12)
        self.assertEqual(data["predicted_sales_units"], 12)
        self.assertEqual(len(data["annual_forecast"]), 12)
        self.assertEqual(data["annual_forecast"][0]["stock_required"], 12)

    def test_forecast_falls_back_for_short_history(self):
        product = Product.objects.create(name="Keyboard", price=Decimal("20.00"), stock=1)
        self.create_sale(product, date(2026, 1, 1), 5)

        forecast_result = ForecastResult(
            values=[5.0],
            method="LSTM_INSUFFICIENT_HISTORY",
            lookback=0,
            epochs=0,
            history_points=1,
            message="Se requieren al menos 24 periodos historicos para entrenar la LSTM.",
        )
        with patch("inventory.api_views.lstm_forecast", return_value=forecast_result):
            response = self.client.get(reverse("product-forecast", args=[product.pk]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["forecast_model"], "LSTM_INSUFFICIENT_HISTORY")
        self.assertEqual(data["predicted_sales_units"], 5)

    def test_sales_api_includes_units_sold(self):
        product = Product.objects.create(name="Monitor", price=Decimal("50.00"), stock=1)
        sale = Sale.objects.create(
            product=product,
            date=date(2026, 1, 1),
            quantity=3,
            serial_number="SALE-UNITS",
            total_price=Decimal("150.00"),
        )

        response = self.client.get(reverse("sale-detail", args=[sale.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["units_sold"], 3.0)

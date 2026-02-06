from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.conf import settings

from .models import Product, Sale
from .views import build_monthly_history, ProductSimulationMixin


class SaleInline(admin.TabularInline):
    model = Sale
    extra = 1
    fields = ("date", "quantity")


@admin.register(Product)
class ProductAdmin(ProductSimulationMixin, admin.ModelAdmin):
    list_display = ("sku", "name", "category", "stock", "created_at")
    search_fields = ("sku", "name", "category")
    list_filter = ("category", "created_at")
    ordering = ("-created_at",)
    inlines = [SaleInline]
    fieldsets = (
        (None, {"fields": ("sku", "name", "category", "description", "price", "stock", "created_at")}),
    )
    actions = ["action_forecast", "action_simulate"]

    def action_forecast(self, request, queryset):
        """Lanza forecast 12m sobre los productos seleccionados y muestra resumen."""
        if queryset.count() == 1:
            product = queryset.first()
            return HttpResponseRedirect(f"/api/products/{product.id}/forecast/?horizon=12&freq=M")

        ok, errors = 0, []
        for product in queryset:
            history = build_monthly_history(product)
            payload = {"sku": product.sku, "history": history, "horizon": 12, "freq": "M"}
            try:
                import requests

                r = requests.post(f"{settings.FASTAPI_URL}/forecast", json=payload, timeout=10)
                r.raise_for_status()
                forecast = r.json().get("forecast", [])
                ok += 1
                messages.info(
                    request,
                    f"[{product.sku}] Forecast 12m: {forecast[:6]}{' ...' if len(forecast) > 6 else ''}",
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{product.sku}: {exc}")
        if errors:
            messages.error(request, " / ".join(errors))
        if ok and not errors:
            messages.success(request, f"Forecast ejecutado para {ok} producto(s).")

    action_forecast.short_description = "Calcular forecast 12m (envía a FastAPI)"  # type: ignore[attr-defined]

    def action_simulate(self, request, queryset):
        """Simula stock 12m usando forecast base (sin reposiciones)."""
        if queryset.count() == 1:
            product = queryset.first()
            return HttpResponseRedirect(f"/api/products/{product.id}/simulate/?horizon=12")

        ok, errors = 0, []
        for product in queryset:
            history = build_monthly_history(product)
            payload = {"sku": product.sku, "history": history, "horizon": 12, "freq": "M"}
            try:
                import requests

                r = requests.post(f"{settings.FASTAPI_URL}/forecast", json=payload, timeout=10)
                r.raise_for_status()
                demand = r.json().get("forecast", [])
                projection, oos = self.simulate_stock(product.stock, demand)
                ok += 1
                msg = f"[{product.sku}] stock→ {projection[:6]}{' ...' if len(projection)>6 else ''}"
                if oos is not None:
                    msg += f" | se agota en mes índice {oos}"
                messages.info(request, msg)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{product.sku}: {exc}")
        if errors:
            messages.error(request, " / ".join(errors))
        if ok and not errors:
            messages.success(request, f"Simulación ejecutada para {ok} producto(s).")

    action_simulate.short_description = "Simular stock 12m (forecast baseline)"  # type: ignore[attr-defined]


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "quantity")
    list_filter = ("date", "product")
    search_fields = ("product__sku", "product__name")
    ordering = ("-date",)

import csv
import io
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from rest_framework.reverse import reverse

from .models import Product, Sale

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "stock", "created_at")
    search_fields = ("sku", "name", "category")
    list_filter = ("category", "created_at")
    ordering = ("-created_at",)
    actions = ["go_to_forecast"]

    @admin.action(description="Ver forecast API")
    def go_to_forecast(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Selecciona exactamente un producto.", messages.WARNING)
            return
        product = queryset.first()
        url = reverse("product-forecast", args=[product.pk], request=request)
        return HttpResponseRedirect(url)

    
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "serial_number", "client_name", "total_price")
    list_filter = ("date", "product")
    search_fields = ("product__sku", "product__name", "serial_number", "client_name")
    ordering = ("-date",)

    change_list_template = "admin/inventory/sale/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="inventory_sale_import_csv",
            )
        ]
        return custom + urls

    def import_csv_view(self, request):
        """Carga masiva de ventas desde CSV con encabezados."""
        sample = "sku,date,serial_number,client_name,total_price\nSKU123,2026-02-01,SN001,Cliente 1,120.50"

        if request.method == "POST" and request.FILES.get("file"):
            uploaded = request.FILES["file"]
            try:
                decoded = uploaded.read().decode("utf-8")
            except UnicodeDecodeError:
                self.message_user(request, "El archivo debe ser UTF-8.", messages.ERROR)
                return HttpResponseRedirect("../")

            # Detecta separador (soporta ';' o ',')
            first_line = decoded.splitlines()[0] if decoded else ""
            delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
            reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
            created = 0
            errors = []

            def parse_decimal(raw: str) -> Decimal:
                raw = raw.strip()
                if not raw:
                    return Decimal("0")
                # normaliza formatos tipo "1.234,56" -> "1234.56"
                normalized = raw.replace(".", "").replace(",", ".")
                return Decimal(normalized)

            for idx, row in enumerate(reader, start=2):  # start=2 por el header
                try:
                    sku = (row.get("sku") or "").strip()
                    product = None
                    if sku:
                        try:
                            product = Product.objects.get(sku=sku)
                        except Product.DoesNotExist:
                            raise ValueError(f"sku '{sku}' no existe")
                    else:
                        # Si falta sku, usar único producto si existe exactamente uno
                        total_products = Product.objects.count()
                        if total_products == 1:
                            product = Product.objects.first()
                        else:
                            raise ValueError("sku requerido (o define un único producto por defecto)")
                    if product is None:
                        raise ValueError("No se pudo resolver el producto")

                    date_str = (row.get("date") or "").strip()
                    sale_date = (
                        datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
                    )

                    serial = (row.get("serial_number") or "").strip()
                    if not serial:
                        serial = f"{sku}-{uuid4().hex[:6].upper()}"

                    client = (row.get("client_name") or "").strip()
                    total_raw = (row.get("total_price") or "").strip()
                    try:
                        total_price = parse_decimal(total_raw)
                    except Exception:
                        raise ValueError(f"total_price inválido: '{total_raw}'")

                    Sale.objects.create(
                        product=product,
                        date=sale_date,
                        serial_number=serial,
                        client_name=client,
                        total_price=total_price,
                    )
                    created += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Línea {idx}: {exc}")

            if created:
                self.message_user(request, f"{created} ventas creadas.", messages.SUCCESS)
            if errors:
                # usar mensajes separados para no cortar contenido
                for msg in errors[:10]:  # mostramos primeros 10 para no saturar
                    self.message_user(request, msg, messages.WARNING)
                if len(errors) > 10:
                    self.message_user(
                        request, f"Otras {len(errors) - 10} líneas con errores.", messages.WARNING
                    )
            return HttpResponseRedirect("../")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "sample": sample.replace(",", ";"),
        }
        return TemplateResponse(request, "admin/inventory/sale/import_csv.html", context)

import csv
import io
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from rest_framework.reverse import reverse

from .models import Product, Sale, StockMovement


def csv_reader_from_upload(uploaded):
    decoded = uploaded.read().decode("utf-8")
    first_line = decoded.splitlines()[0] if decoded else ""
    delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
    return csv.DictReader(io.StringIO(decoded), delimiter=delimiter)


def parse_decimal(raw):
    value = str(raw or "").strip()
    if not value:
        return Decimal("0")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return Decimal(value)


def parse_date(raw):
    raw = str(raw or "").strip()
    return datetime.strptime(raw, "%Y-%m-%d").date() if raw else date.today()


def csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "stock_initial", "stock_received_total", "stock", "created_at")
    search_fields = ("sku", "name", "category")
    list_filter = ("category", "created_at")
    ordering = ("-created_at",)
    actions = ["go_to_forecast"]
    change_list_template = "admin/inventory/product/change_list.html"

    def get_urls(self):
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="inventory_product_import_csv",
            ),
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_product_export_csv",
            )
        ] + super().get_urls()

    @admin.action(description="Ver forecast API")
    def go_to_forecast(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Selecciona exactamente un producto.", messages.WARNING)
            return
        product = queryset.first()
        url = reverse("product-forecast", args=[product.pk], request=request)
        return HttpResponseRedirect(url)

    def import_csv_view(self, request):
        sample = "sku,name,category,description,price,stock_initial\nFIL-ACE-001,Filtro de aceite,Filtros,Filtro premium,42.90,320"

        if request.method == "POST" and request.FILES.get("file"):
            try:
                reader = csv_reader_from_upload(request.FILES["file"])
            except UnicodeDecodeError:
                self.message_user(request, "El archivo debe ser UTF-8.", messages.ERROR)
                return HttpResponseRedirect("../")

            created = 0
            updated = 0
            errors = []

            for idx, row in enumerate(reader, start=2):
                try:
                    sku = (row.get("sku") or "").strip()
                    name = (row.get("name") or "").strip()
                    if not name:
                        raise ValueError("name requerido")

                    stock_initial = int((row.get("stock_initial") or row.get("stock") or "0").strip() or 0)
                    if stock_initial < 0:
                        raise ValueError("stock_initial no puede ser negativo")

                    defaults = {
                        "name": name,
                        "category": (row.get("category") or "").strip(),
                        "description": (row.get("description") or "").strip(),
                        "price": parse_decimal(row.get("price")),
                        "stock_initial": stock_initial,
                        "stock": stock_initial,
                    }

                    if sku:
                        product, was_created = Product.objects.update_or_create(sku=sku, defaults=defaults)
                    else:
                        product = Product.objects.create(**defaults)
                        was_created = True
                    product.recalculate_stock()
                    created += int(was_created)
                    updated += int(not was_created)
                except Exception as exc:
                    errors.append(f"Linea {idx}: {exc}")

            if created:
                self.message_user(request, f"{created} productos creados.", messages.SUCCESS)
            if updated:
                self.message_user(request, f"{updated} productos actualizados.", messages.SUCCESS)
            for msg in errors[:10]:
                self.message_user(request, msg, messages.WARNING)
            if len(errors) > 10:
                self.message_user(request, f"Otras {len(errors) - 10} lineas con errores.", messages.WARNING)
            return HttpResponseRedirect("../")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "sample": sample.replace(",", ";"),
        }
        return TemplateResponse(request, "admin/inventory/product/import_csv.html", context)

    def export_csv_view(self, request):
        headers = ["sku", "name", "category", "description", "price", "stock_initial", "stock"]
        products = Product.objects.order_by("sku")
        rows = (
            [
                product.sku,
                product.name,
                product.category,
                product.description,
                product.price,
                product.stock_initial,
                product.stock,
            ]
            for product in products
        )
        return csv_response("productos.csv", headers, rows)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "quantity", "serial_number", "client_name", "total_price")
    list_filter = ("date", "product")
    search_fields = ("product__sku", "product__name", "serial_number", "client_name")
    ordering = ("-date",)
    change_list_template = "admin/inventory/sale/change_list.html"

    def get_urls(self):
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="inventory_sale_import_csv",
            ),
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_sale_export_csv",
            )
        ] + super().get_urls()

    def import_csv_view(self, request):
        sample = "sku,date,quantity,serial_number,client_name,total_price\nSKU123,2026-02-01,3,SN001,Cliente 1,120.50"

        if request.method == "POST" and request.FILES.get("file"):
            try:
                reader = csv_reader_from_upload(request.FILES["file"])
            except UnicodeDecodeError:
                self.message_user(request, "El archivo debe ser UTF-8.", messages.ERROR)
                return HttpResponseRedirect("../")
            created = 0
            errors = []

            for idx, row in enumerate(reader, start=2):
                try:
                    sku = (row.get("sku") or "").strip()
                    product = None
                    if sku:
                        try:
                            product = Product.objects.get(sku=sku)
                        except Product.DoesNotExist:
                            raise ValueError(f"sku '{sku}' no existe")
                    elif Product.objects.count() == 1:
                        product = Product.objects.first()
                    else:
                        raise ValueError("sku requerido")

                    sale_date = parse_date(row.get("date"))
                    serial = (row.get("serial_number") or "").strip() or f"{sku}-{uuid4().hex[:6].upper()}"
                    client = (row.get("client_name") or "").strip()
                    quantity_raw = (row.get("quantity") or row.get("units_sold") or "1").strip()
                    quantity = int(quantity_raw)
                    if quantity <= 0:
                        raise ValueError("quantity debe ser mayor que cero")

                    Sale.objects.create(
                        product=product,
                        date=sale_date,
                        quantity=quantity,
                        serial_number=serial,
                        client_name=client,
                        total_price=parse_decimal((row.get("total_price") or "").strip()),
                    )
                    created += 1
                except Exception as exc:
                    errors.append(f"Linea {idx}: {exc}")

            if created:
                self.message_user(request, f"{created} ventas creadas.", messages.SUCCESS)
            for msg in errors[:10]:
                self.message_user(request, msg, messages.WARNING)
            if len(errors) > 10:
                self.message_user(request, f"Otras {len(errors) - 10} lineas con errores.", messages.WARNING)
            return HttpResponseRedirect("../")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "sample": sample.replace(",", ";"),
        }
        return TemplateResponse(request, "admin/inventory/sale/import_csv.html", context)

    def export_csv_view(self, request):
        headers = ["sku", "date", "quantity", "serial_number", "client_name", "total_price"]
        sales = Sale.objects.select_related("product").order_by("date", "id")
        rows = (
            [
                sale.product.sku,
                sale.date.isoformat(),
                sale.quantity,
                sale.serial_number,
                sale.client_name,
                sale.total_price,
            ]
            for sale in sales
        )
        return csv_response("ventas.csv", headers, rows)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "quantity", "note", "created_at")
    list_filter = ("date", "product")
    search_fields = ("product__sku", "product__name", "note")
    ordering = ("-date", "-id")
    change_list_template = "admin/inventory/stockmovement/change_list.html"

    def get_urls(self):
        return [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="inventory_stockmovement_import_csv",
            ),
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="inventory_stockmovement_export_csv",
            )
        ] + super().get_urls()

    def import_csv_view(self, request):
        sample = "sku,date,quantity,note\nFIL-ACE-001,2026-05-13,50,Compra proveedor"

        if request.method == "POST" and request.FILES.get("file"):
            try:
                reader = csv_reader_from_upload(request.FILES["file"])
            except UnicodeDecodeError:
                self.message_user(request, "El archivo debe ser UTF-8.", messages.ERROR)
                return HttpResponseRedirect("../")

            created = 0
            errors = []

            for idx, row in enumerate(reader, start=2):
                try:
                    sku = (row.get("sku") or "").strip()
                    if not sku:
                        raise ValueError("sku requerido")
                    product = Product.objects.get(sku=sku)
                    quantity = int((row.get("quantity") or "").strip())
                    if quantity <= 0:
                        raise ValueError("quantity debe ser mayor que cero")
                    StockMovement.objects.create(
                        product=product,
                        date=parse_date(row.get("date")),
                        quantity=quantity,
                        note=(row.get("note") or "").strip(),
                    )
                    created += 1
                except Product.DoesNotExist:
                    errors.append(f"Linea {idx}: sku no existe")
                except Exception as exc:
                    errors.append(f"Linea {idx}: {exc}")

            if created:
                self.message_user(request, f"{created} movimientos creados.", messages.SUCCESS)
            for msg in errors[:10]:
                self.message_user(request, msg, messages.WARNING)
            if len(errors) > 10:
                self.message_user(request, f"Otras {len(errors) - 10} lineas con errores.", messages.WARNING)
            return HttpResponseRedirect("../")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "sample": sample.replace(",", ";"),
        }
        return TemplateResponse(request, "admin/inventory/stockmovement/import_csv.html", context)

    def export_csv_view(self, request):
        headers = ["sku", "date", "quantity", "note"]
        movements = StockMovement.objects.select_related("product").order_by("date", "id")
        rows = (
            [
                movement.product.sku,
                movement.date.isoformat(),
                movement.quantity,
                movement.note,
            ]
            for movement in movements
        )
        return csv_response("movimientos_stock.csv", headers, rows)

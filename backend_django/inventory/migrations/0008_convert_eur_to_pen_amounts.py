from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


EUR_TO_PEN_RATE = Decimal("4.00")
CENT = Decimal("0.01")


def _to_pen(value):
    if value is None:
        return None
    return (Decimal(value) * EUR_TO_PEN_RATE).quantize(CENT, rounding=ROUND_HALF_UP)


def _to_eur(value):
    if value is None:
        return None
    return (Decimal(value) / EUR_TO_PEN_RATE).quantize(CENT, rounding=ROUND_HALF_UP)


def forwards(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    Sale = apps.get_model("inventory", "Sale")

    for product in Product.objects.all().only("id", "price").iterator():
        product.price = _to_pen(product.price)
        product.save(update_fields=["price"])

    for sale in Sale.objects.all().only("id", "total_price").iterator():
        sale.total_price = _to_pen(sale.total_price)
        sale.save(update_fields=["total_price"])


def backwards(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    Sale = apps.get_model("inventory", "Sale")

    for product in Product.objects.all().only("id", "price").iterator():
        product.price = _to_eur(product.price)
        product.save(update_fields=["price"])

    for sale in Sale.objects.all().only("id", "total_price").iterator():
        sale.total_price = _to_eur(sale.total_price)
        sale.save(update_fields=["total_price"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_rename_tpotal_price_sale_total_price"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

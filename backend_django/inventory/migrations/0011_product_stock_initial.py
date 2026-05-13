
import django.core.validators
from django.db import migrations, models
from django.db.models import Sum


def populate_initial_and_current_stock(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    for product in Product.objects.all():
        sold = product.sales.aggregate(total=Sum("quantity"))["total"] or 0
        product.stock_initial = int(product.stock or 0) + int(sold)
        product.stock = max(product.stock_initial - int(sold), 0)
        product.save(update_fields=["stock_initial", "stock"])


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0010_alter_sale_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='stock_initial',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.RunPython(populate_initial_and_current_stock, migrations.RunPython.noop),
    ]

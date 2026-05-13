
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_product_stock_min_forecast_forecastmetric'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forecastmetric',
            name='product',
        ),
        migrations.DeleteModel(
            name='Forecast',
        ),
        migrations.DeleteModel(
            name='ForecastMetric',
        ),
    ]

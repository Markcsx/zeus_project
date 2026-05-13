
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_stockmovement'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='stock_min',
        ),
    ]

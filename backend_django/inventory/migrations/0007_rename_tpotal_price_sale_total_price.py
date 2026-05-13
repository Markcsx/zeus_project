
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_remove_sale_created_at_remove_sale_quantity_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sale',
            old_name='tpotal_price',
            new_name='total_price',
        ),
    ]

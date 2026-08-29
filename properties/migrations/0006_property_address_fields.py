from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0005_seed_property_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='address_number',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='property',
            name='avenue_street',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]

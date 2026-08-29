from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0003_property_services'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='property',
            constraint=models.CheckConstraint(
                check=models.Q(electricity_days_per_week__isnull=True)
                | models.Q(electricity_days_per_week__lte=7),
                name='property_electricity_days_max_7',
            ),
        ),
        migrations.AddConstraint(
            model_name='property',
            constraint=models.CheckConstraint(
                check=models.Q(water_days_per_week__isnull=True)
                | models.Q(water_days_per_week__lte=7),
                name='property_water_days_max_7',
            ),
        ),
    ]

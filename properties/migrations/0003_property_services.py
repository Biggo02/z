from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='electricity_days_per_week',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='electricity_source',
            field=models.CharField(blank=True, choices=[('GRID', 'Réseau public'), ('GENERATOR', 'Groupe électrogène'), ('SOLAR', 'Solaire'), ('BATTERY', 'Batterie / onduleur'), ('HYBRID', 'Hybride'), ('OTHER', 'Autre')], max_length=20),
        ),
        migrations.AddField(
            model_name='property',
            name='water_days_per_week',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='water_source',
            field=models.CharField(blank=True, choices=[('NETWORK', 'Réseau public'), ('BOREHOLE', 'Forage'), ('WELL', 'Puits'), ('CISTERN', 'Citerne'), ('SPRING', 'Source naturelle'), ('TRUCK', 'Camion-citerne'), ('OTHER', 'Autre')], max_length=20),
        ),
    ]

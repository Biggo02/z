from django.db import migrations


class Migration(migrations.Migration):
    """Remove tables left by the retired parent/child location system.

    The application now stores location fields directly on Property.
    This migration is backend-compatible with both SQLite (used by CI/tests)
    and PostgreSQL (used in production).
    """

    dependencies = [
        ('properties', '0006_property_address_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'DROP TABLE IF EXISTS properties_propertylocation; '
                'DROP TABLE IF EXISTS properties_locationnode;'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

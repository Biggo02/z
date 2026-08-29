from django.db import migrations


DEFAULT_PROPERTY_TYPES = [
    'Maison',
    'Appartement',
    'Studio',
    'Chambre',
    'Duplex',
    'Villa',
    'Autre',
]


def seed_property_types(apps, schema_editor):
    PropertyType = apps.get_model('properties', 'PropertyType')

    for order, name in enumerate(DEFAULT_PROPERTY_TYPES, start=1):
        property_type, _created = PropertyType.objects.get_or_create(
            name=name,
            defaults={
                'order': order,
                'active': True,
            },
        )

        # Keep the built-in choices available even when a previous manual
        # seed created one of them with a different order or inactive state.
        changed = []
        if property_type.order != order:
            property_type.order = order
            changed.append('order')
        if not property_type.active:
            property_type.active = True
            changed.append('active')
        if changed:
            property_type.save(update_fields=changed)


def unseed_property_types(apps, schema_editor):
    PropertyType = apps.get_model('properties', 'PropertyType')
    PropertyType.objects.filter(name__in=DEFAULT_PROPERTY_TYPES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0004_property_service_limits'),
    ]

    operations = [
        migrations.RunPython(seed_property_types, unseed_property_types),
    ]

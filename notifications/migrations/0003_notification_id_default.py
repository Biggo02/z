from django.db import migrations, models


def populate_notification_ids(apps, schema_editor):
    Notification = apps.get_model('notifications', 'Notification')
    import uuid
    for row in Notification.objects.filter(notification_id=''):
        row.notification_id = f'NTF-{uuid.uuid4().hex[:10].upper()}'
        row.save(update_fields=['notification_id'])


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_id',
            field=models.CharField(default='TEMP', editable=False, max_length=40, unique=True),
        ),
        migrations.RunPython(populate_notification_ids, migrations.RunPython.noop),
    ]

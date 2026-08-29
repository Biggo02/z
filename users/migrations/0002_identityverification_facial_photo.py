import os
import uuid

from django.db import migrations, models
import core.validators


def facial_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or '.jpg'
    return f'private/identity/facial/{instance.user_id}/{uuid.uuid4().hex}{ext}'


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='identityverification',
            name='facial_photo',
            field=models.ImageField(blank=True, null=True, upload_to=facial_upload_path, validators=[core.validators.validate_image_upload]),
        ),
    ]

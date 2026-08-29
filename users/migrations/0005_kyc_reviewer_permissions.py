from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_kyc_analysis_history_private_storage'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='can_review_kyc',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='identityverification',
            name='assigned_reviewer',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'is_staff': True, 'can_review_kyc': True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_kyc_verifications',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

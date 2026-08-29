# Generated manually for the Fasthome KYC pipeline.

import core.storage
import core.validators
import users.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_alter_identityverification_facial_photo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identityverification',
            name='document_file',
            field=models.FileField(
                upload_to='identity/documents/',
                storage=core.storage.PrivateFileSystemStorage(),
                validators=[core.validators.validate_identity_document],
            ),
        ),
        migrations.AlterField(
            model_name='identityverification',
            name='facial_photo',
            field=models.ImageField(
                blank=True,
                null=True,
                storage=core.storage.PrivateFileSystemStorage(),
                upload_to=users.models.facial_upload_path,
                validators=[core.validators.validate_image_upload],
            ),
        ),
        migrations.CreateModel(
            name='IdentityVerificationAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quality_score', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('ocr_engine', models.CharField(default='unavailable', max_length=40)),
                ('ocr_text', models.TextField(blank=True)),
                ('extracted_name', models.CharField(blank=True, max_length=255)),
                ('name_match_score', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('expiry_ok', models.BooleanField(blank=True, null=True)),
                ('fraud_signals', models.JSONField(blank=True, default=list)),
                ('face_match_score', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('face_explanation', models.TextField(blank=True)),
                ('confidence_score', models.PositiveSmallIntegerField(default=0)),
                ('decision', models.CharField(choices=[('AUTO_VERIFIED', 'Validation automatique'), ('MANUAL_REVIEW', 'Vérification manuelle'), ('REJECTED', 'Rejet automatique')], default='MANUAL_REVIEW', max_length=30)),
                ('explanation', models.TextField(blank=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('verification', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='users.identityverification')),
            ],
        ),
        migrations.CreateModel(
            name='IdentityVerificationEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('SUBMITTED', 'Soumis'), ('AUTOMATED_CHECK', 'Contrôle automatique'), ('MANUAL_DECISION', 'Décision manuelle'), ('DOCUMENT_ACCESSED', 'Document consulté')], max_length=30)),
                ('from_status', models.CharField(blank=True, max_length=20)),
                ('to_status', models.CharField(blank=True, max_length=20)),
                ('from_facial_status', models.CharField(blank=True, max_length=20)),
                ('to_facial_status', models.CharField(blank=True, max_length=20)),
                ('reason', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kyc_events', to=settings.AUTH_USER_MODEL)),
                ('verification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='users.identityverification')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]

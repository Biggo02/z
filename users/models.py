import os
import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from core.storage import PrivateFileSystemStorage
from core.validators import validate_identity_document, validate_image_upload


private_storage = PrivateFileSystemStorage()


def make_code(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:10].upper()}'


def facial_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or '.jpg'
    return f'identity/facial/{instance.user_id}/{uuid.uuid4().hex}{ext}'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, unique=True)
    last_name = models.CharField(max_length=100)
    postname = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True, blank=True)
    SEX_CHOICES = [('M', 'Homme'), ('F', 'Femme')]
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)
    profession = models.CharField(max_length=160, blank=True)
    fasthome_id = models.CharField(max_length=32, unique=True, editable=False)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_certified = models.BooleanField(default=False)
    can_review_kyc = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True, validators=[validate_image_upload])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone', 'last_name', 'first_name']

    def save(self, *args, **kwargs):
        if not self.fasthome_id:
            self.fasthome_id = make_code('FH')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_full_name()} ({self.fasthome_id})'


class IdentityVerification(models.Model):
    DOCUMENT_TYPES = [('PASSPORT', 'Passeport'), ('VOTER_CARD', "Carte d'électeur"), ('DRIVING_LICENSE', 'Permis de conduire')]
    STATUS = [('PENDING', 'En attente'), ('IN_REVIEW', 'En vérification'), ('VERIFIED', 'Vérifiée'), ('REJECTED', 'Refusée'), ('RETRY', 'À refaire')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='identity_verification')
    assigned_reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_kyc_verifications',
        limit_choices_to={'is_staff': True, 'can_review_kyc': True},
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='identity/documents/', storage=private_storage, validators=[validate_identity_document])
    facial_photo = models.ImageField(upload_to=facial_upload_path, storage=private_storage, null=True, blank=True, validators=[validate_image_upload])
    facial_status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.assigned_reviewer_id:
            reviewer = self.assigned_reviewer
            if not reviewer.is_staff or not reviewer.can_review_kyc:
                raise ValidationError({'assigned_reviewer': 'Le réviseur KYC doit être un agent habilité.'})
        if self.facial_status == 'VERIFIED' and not self.facial_photo:
            raise ValidationError({'facial_photo': 'Une photo faciale est obligatoire pour valider le visage.'})
        if self.facial_status == 'VERIFIED' and self.status != 'VERIFIED':
            raise ValidationError({'facial_status': 'Le document d’identité doit être validé avant le visage.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        certified = self.status == 'VERIFIED' and self.facial_status == 'VERIFIED' and bool(self.facial_photo)
        user = User.objects.filter(pk=self.user_id).first()
        if not user:
            return
        update_fields = []
        if user.is_certified != certified:
            user.is_certified = certified
            update_fields.append('is_certified')
        # Never copy a KYC selfie into profile_photo. The selfie is biometric
        # material and must remain in the private KYC storage boundary.
        if update_fields:
            update_fields.append('updated_at')
            user.save(update_fields=update_fields)

    def __str__(self):
        return f'{self.user.fasthome_id} - {self.status}'


class IdentityVerificationAnalysis(models.Model):
    DECISIONS = [('AUTO_VERIFIED', 'Validation automatique'), ('MANUAL_REVIEW', 'Vérification manuelle'), ('REJECTED', 'Rejet automatique')]
    verification = models.OneToOneField(IdentityVerification, on_delete=models.CASCADE, related_name='analysis')
    quality_score = models.PositiveSmallIntegerField(null=True, blank=True)
    ocr_engine = models.CharField(max_length=40, default='unavailable')
    ocr_text = models.TextField(blank=True)
    extracted_name = models.CharField(max_length=255, blank=True)
    name_match_score = models.PositiveSmallIntegerField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    expiry_ok = models.BooleanField(null=True, blank=True)
    fraud_signals = models.JSONField(default=list, blank=True)
    face_match_score = models.PositiveSmallIntegerField(null=True, blank=True)
    face_explanation = models.TextField(blank=True)
    confidence_score = models.PositiveSmallIntegerField(default=0)
    decision = models.CharField(max_length=30, choices=DECISIONS, default='MANUAL_REVIEW')
    explanation = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Analyse {self.verification_id} — {self.confidence_score}%'


class IdentityVerificationEvent(models.Model):
    EVENT_TYPES = [('SUBMITTED', 'Soumis'), ('AUTOMATED_CHECK', 'Contrôle automatique'), ('MANUAL_DECISION', 'Décision manuelle'), ('DOCUMENT_ACCESSED', 'Document consulté')]
    verification = models.ForeignKey(IdentityVerification, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='kyc_events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    from_facial_status = models.CharField(max_length=20, blank=True)
    to_facial_status = models.CharField(max_length=20, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.verification_id} — {self.event_type} — {self.created_at:%Y-%m-%d %H:%M}'

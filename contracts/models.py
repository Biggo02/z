import uuid
from django.core.exceptions import ValidationError
from django.db import models

from core.storage import PrivateFileSystemStorage
from core.validators import validate_identity_document


private_contract_storage = PrivateFileSystemStorage()


class Contract(models.Model):
    TYPES = [('TENANT', 'Sofasthome - Locataire'), ('LANDLORD', 'Sofasthome - Bailleur')]
    STATUS = [('PENDING', 'En attente'), ('SIGNED', 'Signé'), ('UPLOADED', 'Téléversé'), ('VALIDATED', 'Validé'), ('REJECTED', 'Rejeté')]
    contract_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='contracts')
    contract_type = models.CharField(max_length=10, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    signed_document = models.FileField(
        upload_to='private/contracts/',
        storage=private_contract_storage,
        null=True,
        blank=True,
        validators=[validate_identity_document],
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='uploaded_contracts')

    def clean(self):
        super().clean()
        if self.status in {'UPLOADED', 'VALIDATED'} and not self.signed_document:
            raise ValidationError({'signed_document': 'Un contrat téléversé ou validé doit posséder un document signé.'})
        if self.status == 'VALIDATED' and not self.uploaded_by:
            raise ValidationError({'uploaded_by': 'Un contrat validé doit être téléversé par un utilisateur interne identifié.'})

    def save(self, *args, **kwargs):
        if not self.contract_id:
            prefix = 'FCL' if self.contract_type == 'TENANT' else 'FCB'
            self.contract_id = f'{prefix}-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

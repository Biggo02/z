import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class RentalCase(models.Model):
    STATUS = [('OPEN', 'Ouvert'), ('UNDER_REVIEW', 'En vérification'), ('ACCEPTED', 'Accepté'), ('CONTRACTING', 'Contractualisation'), ('OFFICIAL', 'Officiel'), ('REJECTED', 'Refusé'), ('CLOSED', 'Clôturé')]
    case_id = models.CharField(max_length=32, unique=True, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='rental_cases')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='rental_cases_as_tenant')
    visit = models.OneToOneField('visits.VisitRequest', on_delete=models.PROTECT, related_name='rental_case')
    status = models.CharField(max_length=20, choices=STATUS, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.case_id:
            self.case_id = f'DOS-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)


class Lease(models.Model):
    STATUS = [('PENDING', 'En attente'), ('ACTIVE', 'Active'), ('RENEWAL', 'Renouvellement'), ('TERMINATION', 'Résiliation'), ('CLOSED', 'Clôturée')]
    lease_id = models.CharField(max_length=32, unique=True, editable=False)
    rental_case = models.OneToOneField(RentalCase, on_delete=models.PROTECT, related_name='lease')
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='leases')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='leases_as_tenant')
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='leases_as_landlord')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(max_digits=14, decimal_places=2)
    guarantee_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.lease_id:
            self.lease_id = f'FL-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)


class RenewalRequest(models.Model):
    STATUS = [('REQUESTED', 'Demandé'), ('APPROVED', 'Accepté'), ('REFUSED', 'Refusé'), ('CANCELLED', 'Annulé')]
    request_id = models.CharField(max_length=32, unique=True, editable=False)
    lease = models.ForeignKey(Lease, on_delete=models.PROTECT, related_name='renewal_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='renewal_requests')
    requested_end_date = models.DateField()
    proposed_monthly_rent = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='decided_renewals')

    def clean(self):
        super().clean()
        if self.lease_id and self.requested_end_date:
            baseline = self.lease.end_date or self.lease.start_date
            if baseline and self.requested_end_date <= baseline:
                raise ValidationError({'requested_end_date': 'La nouvelle date de fin doit être postérieure à la date de fin actuelle.'})

    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = f'REN-{uuid.uuid4().hex[:10].upper()}'
        self.full_clean()
        super().save(*args, **kwargs)


class LeaseExit(models.Model):
    STATUS = [('REQUESTED', 'Demandée'), ('APPROVED', 'Acceptée'), ('REFUSED', 'Refusée'), ('COMPLETED', 'Terminée'), ('CANCELLED', 'Annulée')]
    exit_id = models.CharField(max_length=32, unique=True, editable=False)
    lease = models.ForeignKey(Lease, on_delete=models.PROTECT, related_name='exit_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='lease_exit_requests')
    requested_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='REQUESTED')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='decided_lease_exits')

    def clean(self):
        super().clean()
        if self.lease_id and self.requested_date:
            baseline = self.lease.start_date
            if baseline and self.requested_date < baseline:
                raise ValidationError({'requested_date': 'La date de sortie ne peut pas précéder le début de la location.'})

    def save(self, *args, **kwargs):
        if not self.exit_id:
            self.exit_id = f'SOR-{uuid.uuid4().hex[:10].upper()}'
        self.full_clean()
        super().save(*args, **kwargs)

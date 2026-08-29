import uuid
from django.conf import settings
from django.db import models
from django.urls import NoReverseMatch, reverse


def generate_notification_id():
    return f'NTF-{uuid.uuid4().hex[:10].upper()}'


class Notification(models.Model):
    LEVELS = [('ACTION', 'Action requise'), ('INFO', 'Information'), ('SUCCESS', 'Réussite')]
    notification_id = models.CharField(max_length=40, unique=True, editable=False, default=generate_notification_id)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    level = models.CharField(max_length=10, choices=LEVELS, default='INFO')
    title = models.CharField(max_length=200)
    message = models.TextField()
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.notification_id:
            self.notification_id = generate_notification_id()
        super().save(*args, **kwargs)

    @property
    def action_url(self):
        routes = {
            'VisitRequest': ('office_visits' if self.recipient.is_staff else 'activity', {}),
            'PropertyPublication': ('office_publications' if self.recipient.is_staff else 'my_properties', {}),
            'IdentityVerification': ('office_verifications' if self.recipient.is_staff else 'certification', {}),
            'RentalCase': ('office_cases' if self.recipient.is_staff else 'activity', {}),
            'Contract': ('office_contracts' if self.recipient.is_staff else 'lease_detail', {}),
            'InspectionReport': ('office_reports' if self.recipient.is_staff else 'lease_detail', {}),
            'PaymentReceipt': ('office_receipt' if self.recipient.is_staff else 'activity', {}),
            'RentInstallment': ('office_dashboard' if self.recipient.is_staff else 'activity', {}),
            'LandlordPayout': ('office_payout' if self.recipient.is_staff else 'lease_detail', {}),
            'RenewalRequest': ('office_lifecycle_requests' if self.recipient.is_staff else 'activity', {}),
            'LeaseExit': ('office_lifecycle_requests' if self.recipient.is_staff else 'activity', {}),
            'Lease': ('office_dashboard' if self.recipient.is_staff else 'lease_detail', {}),
        }
        route = routes.get(self.object_type)
        if not route:
            return reverse('notifications')
        name, kwargs = route
        try:
            if name == 'lease_detail' and self.object_type in {'Contract', 'InspectionReport', 'LandlordPayout', 'Lease'}:
                # These objects carry the lease identifier only indirectly; the generic activity page is safer.
                return reverse('activity')
            if name in {'office_receipt', 'office_payout'}:
                return reverse('office_dashboard')
            return reverse(name, kwargs=kwargs)
        except NoReverseMatch:
            return reverse('notifications')

import re
import uuid
from datetime import datetime

from django.conf import settings
from django.db import models


class VisitRequest(models.Model):
    STATUS = [('REQUESTED', 'Demandée'), ('CONFIRMED', 'Confirmée'), ('REFUSED', 'Refusée'), ('COMPLETED', 'Effectuée'), ('CANCELLED', 'Annulée')]
    visit_id = models.CharField(max_length=32, unique=True, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='visit_requests')
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='visit_requests')
    requested_date = models.DateField()
    requested_time_slot = models.CharField(max_length=80, blank=True)
    fasthome_approved = models.BooleanField(default=False)
    landlord_approved = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default='REQUESTED')
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='completed_visits')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def scheduled_at(self):
        """Backward-compatible datetime used by dashboard templates.

        VisitRequest stores the date and optional time slot separately. The
        dashboard historically expected a single scheduled_at value, so
        expose the start of the selected slot without changing the database
        schema.
        """
        if not self.requested_date:
            return None
        match = re.search(r'(\d{1,2})h(\d{2})', self.requested_time_slot or '')
        if not match:
            return None
        hour, minute = int(match.group(1)), int(match.group(2))
        return datetime.combine(self.requested_date, datetime.min.time().replace(hour=hour, minute=minute))

    def save(self, *args, **kwargs):
        if not self.visit_id:
            self.visit_id = f'VIS-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

    def refresh_confirmation_status(self):
        if self.fasthome_approved and self.landlord_approved:
            self.status = 'CONFIRMED'
            self.save(update_fields=['status'])

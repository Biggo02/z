import uuid
from django.db import models

class InspectionReport(models.Model):
    TYPES = [('ENTRY', 'Entrée'), ('EXIT', 'Sortie')]
    STATUS = [('DRAFT', 'Brouillon'), ('VALIDATED', 'Validé')]
    report_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='inspection_reports')
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='inspection_reports')
    report_type = models.CharField(max_length=10, choices=TYPES, default='ENTRY')
    status = models.CharField(max_length=15, choices=STATUS, default='DRAFT')
    observations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.report_id:
            self.report_id = f'FPV-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

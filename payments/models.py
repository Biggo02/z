from calendar import monthrange
from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction


class RentInstallment(models.Model):
    STATUS = [
        ('UPCOMING', 'À venir'),
        ('PARTIAL', 'Partiellement payé'),
        ('PAID', 'Payé'),
        ('LATE', 'En retard'),
        ('REGULARIZED', 'Régularisé'),
    ]
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='installments')
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default='UPCOMING')

    def total_received(self):
        return sum((payment.amount for payment in self.payments.all()), Decimal('0'))

    def total_paid_to_landlord(self):
        return sum((payout.amount for payout in self.payouts.all()), Decimal('0'))

    def remaining_to_receive(self):
        return max(self.amount_due - self.total_received(), Decimal('0'))

    def remaining_to_pay_out(self):
        return max(self.amount_due - self.total_paid_to_landlord(), Decimal('0'))

    def refresh_payment_status(self):
        total = self.total_received()
        if total >= self.amount_due:
            new_status = 'PAID'
        elif total > 0:
            new_status = 'PARTIAL'
        else:
            new_status = self.status if self.status == 'LATE' else 'UPCOMING'
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        return self.status

    def next_due_date(self):
        year = self.due_date.year + (1 if self.due_date.month == 12 else 0)
        month = 1 if self.due_date.month == 12 else self.due_date.month + 1
        return self.due_date.replace(year=year, month=month, day=min(self.due_date.day, monthrange(year, month)[1]))

    def ensure_next_installment(self):
        if self.total_received() < self.amount_due:
            return None
        installment, _ = RentInstallment.objects.get_or_create(
            lease=self.lease,
            due_date=self.next_due_date(),
            defaults={'amount_due': self.lease.monthly_rent, 'status': 'UPCOMING'},
        )
        return installment


class PaymentReceipt(models.Model):
    payment_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='payment_receipts')
    installment = models.ForeignKey(RentInstallment, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    received_at = models.DateTimeField()
    recorded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='recorded_receipts')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Le montant reçu doit être supérieur à zéro.'})
        if self.installment_id and self.lease_id and self.installment.lease_id != self.lease_id:
            raise ValidationError({'installment': 'L’échéance sélectionnée n’appartient pas à cette location.'})
        if self.pk:
            original = type(self).objects.only('amount', 'lease_id', 'installment_id').get(pk=self.pk)
            if self.lease_id != original.lease_id or self.installment_id != original.installment_id:
                raise ValidationError({'installment': 'Une écriture de paiement existante ne peut pas être déplacée vers une autre location ou échéance.'})
            existing_total = self.installment.total_received() - original.amount
        else:
            existing_total = self.installment.total_received() if self.installment_id else Decimal('0')
        if self.installment_id and self.amount + existing_total > self.installment.amount_due:
            raise ValidationError({'amount': 'Le montant reçu dépasse le solde de l’échéance.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.installment_id:
                self.installment = RentInstallment.objects.select_for_update().get(pk=self.installment_id)
            self.full_clean()
            if not self.payment_id:
                self.payment_id = f'PAY-{uuid.uuid4().hex[:10].upper()}'
            super().save(*args, **kwargs)
            installment = RentInstallment.objects.select_for_update().get(pk=self.installment_id)
            installment.refresh_payment_status()
            if installment.status == 'PAID':
                installment.ensure_next_installment()


class LandlordPayout(models.Model):
    payout_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='landlord_payouts')
    installment = models.ForeignKey(RentInstallment, on_delete=models.PROTECT, related_name='payouts')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_at = models.DateTimeField()
    recorded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='recorded_payouts')
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='PAID')

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Le montant versé doit être supérieur à zéro.'})
        if self.installment_id and self.lease_id and self.installment.lease_id != self.lease_id:
            raise ValidationError({'installment': 'L’échéance sélectionnée n’appartient pas à cette location.'})

        installment = self.installment if self.installment_id else None
        if installment:
            # Flux indépendant : locataire -> Fasthome et Fasthome -> bailleur.
            # Fasthome doit verser l'échéance complète en une seule fois,
            # même si le locataire a payé Fasthome en plusieurs tranches.
            if self.amount != installment.amount_due:
                raise ValidationError({'amount': 'Fasthome doit verser au bailleur le montant total de l’échéance en une seule fois.'})
            if self.paid_at and self.paid_at.date() > installment.due_date:
                raise ValidationError({'paid_at': 'Le versement au bailleur doit être effectué au plus tard à la date d’échéance.'})

        if self.pk:
            original = type(self).objects.only('amount', 'lease_id', 'installment_id').get(pk=self.pk)
            if self.lease_id != original.lease_id or self.installment_id != original.installment_id:
                raise ValidationError({'installment': 'Un versement existant ne peut pas être déplacé vers une autre location ou échéance.'})
        elif installment and installment.payouts.exists():
            raise ValidationError({'installment': 'Cette échéance a déjà été versée au bailleur. Fasthome ne fractionne pas le versement.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.installment_id:
                self.installment = RentInstallment.objects.select_for_update().get(pk=self.installment_id)
            self.full_clean()
            if not self.payout_id:
                self.payout_id = f'PAY-OUT-{uuid.uuid4().hex[:10].upper()}'
            super().save(*args, **kwargs)

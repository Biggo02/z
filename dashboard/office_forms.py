from decimal import Decimal

from django import forms
from django.utils import timezone

from leasing.models import Lease
from payments.models import RentInstallment
from payments.models import PaymentReceipt, LandlordPayout


class ReceiptForm(forms.Form):
    lease = forms.ModelChoiceField(queryset=Lease.objects.select_related('property').all())
    installment = forms.ModelChoiceField(queryset=RentInstallment.objects.select_related('lease').all())
    amount = forms.DecimalField(min_value=Decimal('0.01'), max_digits=14, decimal_places=2)
    received_at = forms.DateTimeField(initial=timezone.now)
    reference = forms.CharField(required=False, max_length=100)
    notes = forms.CharField(required=False, max_length=2000, widget=forms.Textarea)

    def clean(self):
        cleaned = super().clean()
        lease = cleaned.get('lease')
        installment = cleaned.get('installment')
        amount = cleaned.get('amount')
        if lease and installment and installment.lease_id != lease.id:
            raise forms.ValidationError('La location et l’échéance ne correspondent pas.')
        if installment and amount:
            already_received = sum((p.amount for p in PaymentReceipt.objects.filter(installment=installment)), Decimal('0'))
            if already_received + amount > installment.amount_due:
                raise forms.ValidationError('Le paiement dépasse le solde restant de cette échéance.')
        return cleaned


class PayoutForm(forms.Form):
    lease = forms.ModelChoiceField(queryset=Lease.objects.select_related('property').all())
    installment = forms.ModelChoiceField(queryset=RentInstallment.objects.select_related('lease').all())
    amount = forms.DecimalField(min_value=Decimal('0.01'), max_digits=14, decimal_places=2, help_text='Le montant doit correspondre à 100 % de l’échéance. Fasthome ne fractionne pas le versement.')
    paid_at = forms.DateTimeField(initial=timezone.now, help_text='Le versement doit être effectué au plus tard à la date d’échéance.')
    reference = forms.CharField(required=False, max_length=100)

    def clean(self):
        cleaned = super().clean()
        lease = cleaned.get('lease')
        installment = cleaned.get('installment')
        amount = cleaned.get('amount')
        paid_at = cleaned.get('paid_at')
        if lease and installment and installment.lease_id != lease.id:
            raise forms.ValidationError('La location et l’échéance ne correspondent pas.')
        if installment:
            if amount is not None and amount != installment.amount_due:
                raise forms.ValidationError('Fasthome doit verser au bailleur 100 % du montant de l’échéance, en une seule fois.')
            if paid_at and paid_at.date() > installment.due_date:
                raise forms.ValidationError('Le versement au bailleur doit être effectué au plus tard à la date d’échéance.')
            if LandlordPayout.objects.filter(installment=installment).exists():
                raise forms.ValidationError('Cette échéance a déjà été versée au bailleur. Aucun second versement n’est autorisé.')
        return cleaned

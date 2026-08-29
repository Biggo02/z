from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from leasing.models import Lease, RentalCase
from properties.models import Property, PropertyType
from users.models import User
from visits.models import VisitRequest
from .models import LandlordPayout, PaymentReceipt, RentInstallment


class PaymentInvariantTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email='landlord@example.com', password='A-secure-password-123',
            phone='+243900000101', last_name='Landlord', first_name='Test',
        )
        self.tenant = User.objects.create_user(
            email='tenant@example.com', password='A-secure-password-123',
            phone='+243900000102', last_name='Tenant', first_name='Test',
        )
        property_type, _created = PropertyType.objects.get_or_create(
            name='Appartement', defaults={'active': True, 'order': 2},
        )
        if not property_type.active:
            property_type.active = True
            property_type.save(update_fields=['active'])
        self.property = Property.objects.create(
            owner=self.landlord, property_type=property_type,
            province='Haut-Katanga', city_or_territory='Lubumbashi', neighborhood='Golf',
            bedroom_count=2, living_room_count=1, max_occupants=4,
            monthly_rent=Decimal('300000'), status='RENTED',
        )
        self.visit = VisitRequest.objects.create(
            property=self.property, requester=self.tenant, requested_date=date.today(),
            fasthome_approved=True, landlord_approved=True, status='COMPLETED',
        )
        self.case = RentalCase.objects.create(
            property=self.property, tenant=self.tenant, visit=self.visit, status='CONTRACTING',
        )
        self.lease = Lease.objects.create(
            rental_case=self.case, property=self.property, tenant=self.tenant,
            landlord=self.landlord, monthly_rent=Decimal('300000'), status='ACTIVE',
        )
        self.installment = RentInstallment.objects.create(
            lease=self.lease, due_date=date.today(), amount_due=Decimal('300000'),
        )

    def _user(self):
        return self.landlord

    def _payment(self, amount, installment=None, lease=None):
        installment = installment or self.installment
        lease = lease or self.lease
        return PaymentReceipt.objects.create(
            lease=lease, installment=installment, amount=Decimal(amount),
            received_at='2026-08-20T10:00:00Z', recorded_by=self._user(),
        )

    def _payout(self, amount='300000', installment=None, paid_at='2026-08-20T12:00:00Z'):
        return LandlordPayout.objects.create(
            lease=self.lease, installment=installment or self.installment,
            amount=Decimal(amount), paid_at=paid_at, recorded_by=self._user(),
        )

    def test_payment_can_be_split_into_multiple_tranches(self):
        self._payment('100000'); self._payment('200000')
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.total_received(), Decimal('300000'))
        self.assertEqual(self.installment.status, 'PAID')

    def test_partial_payment_marks_installment_partial(self):
        self._payment('100000'); self.installment.refresh_from_db()
        self.assertEqual(self.installment.status, 'PARTIAL')
        self.assertEqual(self.installment.remaining_to_receive(), Decimal('200000'))

    def test_full_payment_creates_next_month_installment(self):
        self._payment('300000')
        self.assertEqual(RentInstallment.objects.filter(lease=self.lease).count(), 2)

    def test_payment_cannot_exceed_due_amount(self):
        self._payment('250000')
        with self.assertRaises(ValidationError): self._payment('60000')

    def test_payment_must_be_positive(self):
        for amount in (Decimal('0'), Decimal('-1')):
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError): self._payment(amount)

    def test_payment_installment_must_belong_to_lease(self):
        other_installment = RentInstallment.objects.create(
            lease=self.lease, due_date=date.today().replace(day=2), amount_due=Decimal('300000'),
        )
        other_lease = Lease.objects.exclude(pk=self.lease.pk).first()
        if other_lease is None:
            other_visit = VisitRequest.objects.create(
                property=self.property, requester=self.tenant, requested_date=date.today(),
                fasthome_approved=True, landlord_approved=True, status='COMPLETED',
            )
            other_case = RentalCase.objects.create(property=self.property, tenant=self.tenant, visit=other_visit, status='CONTRACTING')
            other_lease = Lease.objects.create(
                rental_case=other_case, property=self.property, tenant=self.tenant,
                landlord=self.landlord, monthly_rent=Decimal('300000'), status='ACTIVE',
            )
        other_installment.lease = other_lease
        other_installment.save(update_fields=['lease'])
        with self.assertRaises(ValidationError): self._payment('1000', installment=other_installment)

    def test_existing_payment_cannot_be_updated_to_exceed_installment_balance(self):
        payment = self._payment('100000')
        payment.amount = Decimal('300001')
        with self.assertRaises(ValidationError): payment.save()

    def test_existing_payment_cannot_be_moved_to_another_installment(self):
        payment = self._payment('100000')
        other_installment = RentInstallment.objects.create(
            lease=self.lease, due_date=date.today().replace(day=2), amount_due=Decimal('300000'),
        )
        payment.installment = other_installment
        with self.assertRaises(ValidationError): payment.save()

    def test_payout_cannot_exceed_amount_received(self):
        self._payment('150000')
        with self.assertRaises(ValidationError):
            LandlordPayout.objects.create(
                lease=self.lease, installment=self.installment, amount=Decimal('150001'),
                paid_at='2026-08-20T12:00:00Z', recorded_by=self._user(),
            )

    def test_payout_cannot_be_partial(self):
        self._payment('300000')
        with self.assertRaises(ValidationError):
            self._payout('100000')

    def test_payout_cannot_be_split_into_multiple_tranches(self):
        self._payment('300000')
        self._payout('300000')
        with self.assertRaises(ValidationError):
            self._payout('1', paid_at='2026-08-20T13:00:00Z')

    def test_payout_is_full_and_independent_of_tenant_payment(self):
        self._payment('100000')
        payout = self._payout('300000')
        self.assertEqual(payout.amount, self.installment.amount_due)

    def test_existing_payout_cannot_be_updated_to_partial_or_excess(self):
        payout = self._payout('300000')
        payout.amount = Decimal('100000')
        with self.assertRaises(ValidationError): payout.save()
        payout.amount = Decimal('300001')
        with self.assertRaises(ValidationError): payout.save()

    def test_existing_payout_cannot_be_moved_to_another_installment(self):
        payout = self._payout('300000')
        other_installment = RentInstallment.objects.create(
            lease=self.lease, due_date=date.today().replace(day=2), amount_due=Decimal('300000'),
        )
        payout.installment = other_installment
        with self.assertRaises(ValidationError): payout.save()

    def test_payout_must_be_positive(self):
        for amount in (Decimal('0'), Decimal('-1')):
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError):
                    LandlordPayout.objects.create(lease=self.lease, installment=self.installment, amount=amount, paid_at='2026-08-20T12:00:00Z', recorded_by=self._user())

    def test_payout_must_be_on_or_before_due_date(self):
        late_date = self.installment.due_date + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self._payout('300000', paid_at=f'{late_date.isoformat()}T12:00:00Z')

    def test_payout_installment_must_belong_to_lease(self):
        other_visit = VisitRequest.objects.create(property=self.property, requester=self.tenant, requested_date=date.today(), status='COMPLETED')
        other_case = RentalCase.objects.create(property=self.property, tenant=self.tenant, visit=other_visit, status='CONTRACTING')
        other_lease = Lease.objects.create(rental_case=other_case, property=self.property, tenant=self.tenant, landlord=self.landlord, monthly_rent=Decimal('300000'), status='ACTIVE')
        other_installment = RentInstallment.objects.create(lease=other_lease, due_date=date.today(), amount_due=Decimal('300000'))
        with self.assertRaises(ValidationError):
            LandlordPayout.objects.create(lease=self.lease, installment=other_installment, amount=Decimal('300000'), paid_at='2026-08-20T12:00:00Z', recorded_by=self._user())

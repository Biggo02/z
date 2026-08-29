from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from properties.models import Property, PropertyType
from users.models import User
from leasing.models import Lease, RentalCase, RenewalRequest, LeaseExit
from visits.models import VisitRequest


class LeaseLifecycleTests(TestCase):
    def setUp(self):
        self.tenant = User.objects.create_user(email='life-tenant@example.com', password='A-secure-password-123', phone='+243900001101', last_name='Tenant', first_name='Life')
        self.landlord = User.objects.create_user(email='life-landlord@example.com', password='A-secure-password-123', phone='+243900001102', last_name='Landlord', first_name='Life')
        self.staff = User.objects.create_user(email='life-staff@example.com', password='A-secure-password-123', phone='+243900001103', last_name='Staff', first_name='Life', is_staff=True)
        ptype = PropertyType.objects.create(name='Maison lifecycle')
        self.property = Property.objects.create(owner=self.landlord, property_type=ptype, province='Haut-Katanga', city_or_territory='Lubumbashi', neighborhood='Golf', bedroom_count=2, living_room_count=1, max_occupants=4, monthly_rent=Decimal('300000'), status='RENTED')
        self.visit = VisitRequest.objects.create(property=self.property, requester=self.tenant, requested_date=date.today(), requested_time_slot='09:00-10:00', status='COMPLETED')
        self.case = RentalCase.objects.create(property=self.property, tenant=self.tenant, visit=self.visit, status='OFFICIAL')
        self.lease = Lease.objects.create(rental_case=self.case, property=self.property, tenant=self.tenant, landlord=self.landlord, start_date=date.today(), end_date=date.today() + timedelta(days=365), monthly_rent=Decimal('300000'), status='ACTIVE')

    def test_tenant_can_request_renewal(self):
        self.client.force_login(self.tenant)
        response = self.client.post(reverse('request_renewal', args=[self.lease.lease_id]), {'requested_end_date': date.today() + timedelta(days=730), 'proposed_monthly_rent': '320000', 'reason': 'Continuer la location'}, follow=True)
        self.assertEqual(response.status_code, 200)
        request = RenewalRequest.objects.get(lease=self.lease)
        self.assertEqual(request.requested_by, self.tenant)
        self.assertEqual(request.status, 'REQUESTED')

    def test_duplicate_renewal_request_is_blocked(self):
        RenewalRequest.objects.create(lease=self.lease, requested_by=self.tenant, requested_end_date=date.today() + timedelta(days=730))
        self.client.force_login(self.tenant)
        self.client.post(reverse('request_renewal', args=[self.lease.lease_id]), {'requested_end_date': date.today() + timedelta(days=800)}, follow=True)
        self.assertEqual(RenewalRequest.objects.filter(lease=self.lease, status='REQUESTED').count(), 1)

    def test_staff_can_approve_renewal(self):
        renewal = RenewalRequest.objects.create(lease=self.lease, requested_by=self.tenant, requested_end_date=date.today() + timedelta(days=730), proposed_monthly_rent=Decimal('320000'))
        self.client.force_login(self.staff)
        response = self.client.post(reverse('decide_renewal', args=[renewal.request_id]), {'action': 'approve'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.lease.refresh_from_db(); renewal.refresh_from_db()
        self.assertEqual(renewal.status, 'APPROVED')
        self.assertEqual(self.lease.status, 'RENEWAL')
        self.assertEqual(self.lease.monthly_rent, Decimal('320000'))

    def test_tenant_can_request_exit(self):
        self.client.force_login(self.tenant)
        response = self.client.post(reverse('request_exit', args=[self.lease.lease_id]), {'requested_date': date.today() + timedelta(days=30), 'reason': 'Déménagement'}, follow=True)
        self.assertEqual(response.status_code, 200)
        exit_request = LeaseExit.objects.get(lease=self.lease)
        self.assertEqual(exit_request.status, 'REQUESTED')

    def test_staff_can_approve_exit_and_move_lease_to_termination(self):
        exit_request = LeaseExit.objects.create(lease=self.lease, requested_by=self.tenant, requested_date=date.today() + timedelta(days=30))
        self.client.force_login(self.staff)
        response = self.client.post(reverse('decide_exit', args=[exit_request.exit_id]), {'action': 'approve'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.lease.refresh_from_db(); exit_request.refresh_from_db()
        self.assertEqual(exit_request.status, 'APPROVED')
        self.assertEqual(self.lease.status, 'TERMINATION')

    def test_landlord_cannot_create_tenant_renewal_or_exit_request(self):
        self.client.force_login(self.landlord)
        renewal_response = self.client.post(reverse('request_renewal', args=[self.lease.lease_id]), {'requested_end_date': date.today() + timedelta(days=730)}, follow=True)
        exit_response = self.client.post(reverse('request_exit', args=[self.lease.lease_id]), {'requested_date': date.today() + timedelta(days=30)}, follow=True)
        self.assertEqual(renewal_response.status_code, 200)
        self.assertEqual(exit_response.status_code, 200)
        self.assertFalse(RenewalRequest.objects.filter(lease=self.lease).exists())
        self.assertFalse(LeaseExit.objects.filter(lease=self.lease).exists())

    def test_staff_cannot_contract_second_case_for_property_with_active_lease(self):
        second_tenant = User.objects.create_user(email='life-second-tenant@example.com', password='A-secure-password-123', phone='+243900001104', last_name='Tenant', first_name='Second')
        second_visit = VisitRequest.objects.create(property=self.property, requester=second_tenant, requested_date=date.today(), requested_time_slot='10:00-11:00', status='COMPLETED')
        second_case = RentalCase.objects.create(property=self.property, tenant=second_tenant, visit=second_visit, status='OPEN')

        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_accept_case', args=[second_case.case_id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Lease.objects.filter(property=self.property).count(), 1)
        second_case.refresh_from_db()
        self.assertEqual(second_case.status, 'OPEN')

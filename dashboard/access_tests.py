from datetime import date, timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from contracts.models import Contract
from core.storage import PrivateFileSystemStorage
from leasing.models import Lease, RentalCase
from properties.models import Property, PropertyType
from users.models import User
from visits.models import VisitRequest


class AccessControlTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', password='A-secure-password-123',
            phone='+243900001001', last_name='Owner', first_name='Test',
            is_certified=True,
        )
        self.other = User.objects.create_user(
            email='other@example.com', password='A-secure-password-123',
            phone='+243900001002', last_name='Other', first_name='Test',
            is_certified=True,
        )
        self.staff = User.objects.create_user(
            email='staff@example.com', password='A-secure-password-123',
            phone='+243900001003', last_name='Staff', first_name='Test',
            is_staff=True,
        )

        ptype, _created = PropertyType.objects.get_or_create(
            name='Appartement',
            defaults={'active': True, 'order': 2},
        )
        if not ptype.active:
            ptype.active = True
            ptype.save(update_fields=['active'])

        self.property = Property.objects.create(
            owner=self.owner, property_type=ptype,
            province='Haut-Katanga', city_or_territory='Lubumbashi',
            neighborhood='Golf', bedroom_count=2, living_room_count=1,
            max_occupants=4, monthly_rent=Decimal('300000'), status='AVAILABLE',
        )

    def _lease(self):
        visit = VisitRequest.objects.create(
            property=self.property,
            requester=self.other,
            requested_date=date.today() + timedelta(days=1),
            status='COMPLETED',
        )
        case = RentalCase.objects.create(
            property=self.property,
            tenant=self.other,
            visit=visit,
            status='CONTRACTING',
        )
        return Lease.objects.create(
            rental_case=case,
            property=self.property,
            tenant=self.other,
            landlord=self.owner,
            monthly_rent=Decimal('300000'),
            status='ACTIVE',
        )

    def test_owner_can_open_edit_but_other_user_cannot(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('property_edit', args=[self.property.property_id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.other)
        response = self.client.get(reverse('property_edit', args=[self.property.property_id]), follow=True)
        self.assertEqual(response.status_code, 404)

    def test_non_staff_cannot_complete_visit(self):
        visit = VisitRequest.objects.create(
            property=self.property, requester=self.other,
            requested_date=date.today() + timedelta(days=1),
            fasthome_approved=True, landlord_approved=True, status='CONFIRMED',
        )
        self.client.force_login(self.other)
        response = self.client.post(reverse('office_complete_visit', args=[visit.visit_id]), follow=True)
        self.assertIn(response.status_code, {200, 403})
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'CONFIRMED')

    def test_landlord_and_tenant_can_read_their_lease_but_outsider_cannot(self):
        lease = self._lease()
        self.client.force_login(self.owner)
        response = self.client.get(reverse('lease_detail', args=[lease.lease_id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.other)
        response = self.client.get(reverse('lease_detail', args=[lease.lease_id]), follow=True)
        self.assertEqual(response.status_code, 200)
        outsider = User.objects.create_user(
            email='outsider@example.com', password='A-secure-password-123',
            phone='+243900001004', last_name='Outsider', first_name='Test',
        )
        self.client.force_login(outsider)
        response = self.client.get(reverse('lease_detail', args=[lease.lease_id]), follow=False)
        self.assertIn(response.status_code, {301, 302})

    def test_staff_dashboard_access(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('office_dashboard'), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_contract_document_is_private_and_party_scoped(self):
        lease = self._lease()
        contract = Contract.objects.create(
            lease=lease,
            contract_type='TENANT',
            status='VALIDATED',
            uploaded_by=self.staff,
            signed_document=SimpleUploadedFile(
                'tenant-contract.pdf', b'%PDF-1.4 private contract', content_type='application/pdf'
            ),
        )
        self.assertIsInstance(contract.signed_document.storage, PrivateFileSystemStorage)

        self.client.force_login(self.other)
        response = self.client.get(reverse('contract_document', args=[contract.contract_id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))

        self.client.force_login(self.owner)
        response = self.client.get(reverse('contract_document', args=[contract.contract_id]))
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.staff)
        response = self.client.get(reverse('contract_document', args=[contract.contract_id]))
        self.assertEqual(response.status_code, 200)

    def test_outsider_cannot_download_contract_by_identifier(self):
        lease = self._lease()
        contract = Contract.objects.create(
            lease=lease,
            contract_type='LANDLORD',
            status='VALIDATED',
            uploaded_by=self.staff,
            signed_document=SimpleUploadedFile(
                'landlord-contract.pdf', b'%PDF-1.4 private contract', content_type='application/pdf'
            ),
        )
        self.client.force_login(self.other)
        response = self.client.get(reverse('contract_document', args=[contract.contract_id]))
        self.assertEqual(response.status_code, 404)

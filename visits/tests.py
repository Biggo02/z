from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from properties.models import Property, PropertyPublication, PropertyType
from users.models import User
from .models import VisitRequest


class VisitWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner-visit@example.com', password='A-secure-password-123',
            phone='+243900000201', last_name='Owner', first_name='Visit',
        )
        self.tenant = User.objects.create_user(
            email='tenant-visit@example.com', password='A-secure-password-123',
            phone='+243900000202', last_name='Tenant', first_name='Visit',
        )
        self.tenant.is_certified = True
        self.tenant.save(update_fields=['is_certified'])
        self.outsider = User.objects.create_user(
            email='outsider-visit@example.com', password='A-secure-password-123',
            phone='+243900000203', last_name='Outside', first_name='Visit',
        )
        property_type = PropertyType.objects.create(name='Maison visite')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type,
            furnished=False, province='Haut-Katanga', city_or_territory='Lubumbashi',
            administrative_subdivision='Commune', neighborhood='Golf',
            bedroom_count=2, living_room_count=1, max_occupants=4,
            monthly_rent=Decimal('300000'), status='AVAILABLE',
        )
        PropertyPublication.objects.create(property=self.property, status='PUBLISHED')

    def _create_available_property(self, neighborhood):
        return Property.objects.create(
            owner=self.owner, property_type=self.property.property_type,
            furnished=False, province='Haut-Katanga', city_or_territory='Lubumbashi',
            administrative_subdivision='Commune', neighborhood=neighborhood,
            bedroom_count=2, living_room_count=1, max_occupants=4,
            monthly_rent=Decimal('300000'), status='AVAILABLE',
        )

    def test_request_visit_is_post_only_and_does_not_expose_requester_to_owner(self):
        self.client.force_login(self.tenant)
        response = self.client.post(reverse('request_visit', args=[self.property.property_id]), {
            'requested_date': (date.today() + timedelta(days=2)).isoformat(),
            'requested_time_slot': '10:00-12:00',
        })
        self.assertEqual(response.status_code, 302)
        visit = VisitRequest.objects.get(property=self.property)
        self.assertEqual(visit.requester_id, self.tenant.id)
        self.assertFalse(visit.landlord_approved)

    def test_tenant_can_choose_take_only_after_completed_visit(self):
        visit = VisitRequest.objects.create(
            property=self.property, requester=self.tenant,
            requested_date=date.today() + timedelta(days=1),
            fasthome_approved=True, landlord_approved=True, status='CONFIRMED',
        )
        self.client.force_login(self.tenant)
        before = self.client.post(reverse('tenant_decision', args=[visit.visit_id]), {'action': 'take'})
        self.assertEqual(before.status_code, 404)
        self.assertFalse(hasattr(visit, 'rental_case'))
        visit.status = 'COMPLETED'
        visit.save(update_fields=['status'])
        response = self.client.post(reverse('tenant_decision', args=[visit.visit_id]), {'action': 'take'})
        self.assertEqual(response.status_code, 302)
        visit.refresh_from_db()
        self.assertTrue(hasattr(visit, 'rental_case'))
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'UNDER_REVIEW')

    def test_outsider_cannot_make_tenant_decision(self):
        visit = VisitRequest.objects.create(
            property=self.property, requester=self.tenant,
            requested_date=date.today() + timedelta(days=1), status='COMPLETED',
        )
        self.client.force_login(self.outsider)
        response = self.client.post(reverse('tenant_decision', args=[visit.visit_id]), {'action': 'take'})
        self.assertEqual(response.status_code, 404)

    def test_tenant_can_have_at_most_two_active_visit_requests(self):
        first_property = self.property
        second_property = self._create_available_property('Bel-Air')
        third_property = self._create_available_property('Kampemba')
        self.client.force_login(self.tenant)
        for prop in (first_property, second_property):
            response = self.client.post(reverse('request_visit', args=[prop.property_id]), {
                'requested_date': (date.today() + timedelta(days=2)).isoformat(),
                'requested_time_slot': '10:00-12:00',
            })
            self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('request_visit', args=[third_property.property_id]), {
            'requested_date': (date.today() + timedelta(days=2)).isoformat(),
            'requested_time_slot': '10:00-12:00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VisitRequest.objects.filter(requester=self.tenant).count(), 2)

    def test_request_visit_locks_tenant_before_counting_active_requests(self):
        """The active-visit check must run while the tenant row is locked."""
        self.client.force_login(self.tenant)
        self.client.post(reverse('request_visit', args=[self.property.property_id]), {
            'requested_date': (date.today() + timedelta(days=2)).isoformat(),
            'requested_time_slot': '10:00-12:00',
        })
        self.assertEqual(
            VisitRequest.objects.filter(
                requester=self.tenant, status__in=['REQUESTED', 'CONFIRMED']
            ).count(),
            1,
        )

    def test_landlord_can_approve_without_receiving_requester_identity(self):
        visit = VisitRequest.objects.create(
            property=self.property, requester=self.tenant,
            requested_date=date.today() + timedelta(days=1), status='REQUESTED',
        )
        self.client.force_login(self.owner)
        response = self.client.post(reverse('landlord_visit_decision', args=[visit.visit_id]), {'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        visit.refresh_from_db()
        self.assertTrue(visit.landlord_approved)
        self.assertFalse(response.context if hasattr(response, 'context') else False)

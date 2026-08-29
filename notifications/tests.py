from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from properties.models import Property, PropertyType
from users.models import User
from visits.models import VisitRequest
from .models import Notification
from .services import (
    visit_fasthome_approved,
    visit_landlord_approved,
    visit_landlord_refused,
    visit_confirmed,
)


class VisitNotificationRulesTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='notification-owner@example.com', password='A-secure-password-123',
            phone='+243900001001', last_name='Owner', first_name='Notification',
        )
        self.tenant = User.objects.create_user(
            email='notification-tenant@example.com', password='A-secure-password-123',
            phone='+243900001002', last_name='Tenant', first_name='Notification',
        )
        self.staff = User.objects.create_user(
            email='notification-staff@example.com', password='A-secure-password-123',
            phone='+243900001003', last_name='Staff', first_name='Notification',
            is_staff=True,
        )
        property_type = PropertyType.objects.create(name='Appartement notifications')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type,
            province='Haut-Katanga', city_or_territory='Lubumbashi',
            neighborhood='Golf', bedroom_count=2, living_room_count=1,
            max_occupants=4, monthly_rent=Decimal('300000'), status='AVAILABLE',
        )

    def _visit(self, **kwargs):
        defaults = {
            'property': self.property,
            'requester': self.tenant,
            'requested_date': date.today() + timedelta(days=2),
            'status': 'REQUESTED',
        }
        defaults.update(kwargs)
        return VisitRequest.objects.create(**defaults)

    def test_landlord_accepts_only_staff_is_notified(self):
        visit = self._visit(landlord_approved=True)
        visit_landlord_approved(visit)
        self.assertFalse(Notification.objects.filter(recipient=self.tenant).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.owner).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.staff, object_id=visit.visit_id).exists())

    def test_landlord_refuses_only_staff_is_notified(self):
        visit = self._visit(status='REFUSED')
        visit_landlord_refused(visit)
        self.assertFalse(Notification.objects.filter(recipient=self.tenant).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.owner).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.staff, object_id=visit.visit_id).exists())

    def test_fasthome_accepts_first_nobody_is_notified(self):
        visit = self._visit(fasthome_approved=True)
        visit_fasthome_approved(visit)
        self.assertEqual(Notification.objects.filter(object_type='VisitRequest', object_id=visit.visit_id).count(), 0)

    def test_second_acceptance_confirms_and_notifies_three_actors(self):
        visit = self._visit(fasthome_approved=True, landlord_approved=True, status='CONFIRMED')
        visit_confirmed(visit)
        self.assertTrue(Notification.objects.filter(recipient=self.tenant, object_id=visit.visit_id, title='Visite définitivement confirmée').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.owner, object_id=visit.visit_id, title='Visite définitivement confirmée').exists())
        self.assertTrue(Notification.objects.filter(recipient=self.staff, object_id=visit.visit_id, title='Visite confirmée').exists())

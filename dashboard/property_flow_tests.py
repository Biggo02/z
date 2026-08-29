from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from properties.models import Property, PropertyPublication, PropertyType
from users.models import User


class PropertyFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='flow-owner@example.com',
            password='A-secure-password-123',
            phone='+243900008001',
            last_name='Flow',
            first_name='Owner',
            is_certified=True,
        )
        self.other = User.objects.create_user(
            email='flow-other@example.com',
            password='A-secure-password-123',
            phone='+243900008002',
            last_name='Flow',
            first_name='Other',
            is_certified=True,
        )
        self.ptype = PropertyType.objects.create(name='Maison flow')

    def test_owner_can_create_draft(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('property_create'),
            {
                'property_type': self.ptype.pk,
                'province': 'Haut-Katanga',
                'city_or_territory': 'Lubumbashi',
                'neighborhood': 'Golf',
                'bedroom_count': '2',
                'living_room_count': '1',
                'bathroom_count': '1',
                'toilet_count': '1',
                'has_kitchen': 'yes',
                'monthly_rent': '300000',
                'max_occupants': '4',
            },
        )
        self.assertEqual(response.status_code, 302)
        prop = Property.objects.get(owner=self.owner)
        self.assertEqual(prop.publication.status, 'DRAFT')
        self.assertEqual(prop.city_or_territory, 'Lubumbashi')

    def test_non_certified_user_cannot_start_publication(self):
        self.owner.is_certified = False
        self.owner.save(update_fields=['is_certified'])
        self.client.force_login(self.owner)
        response = self.client.get(reverse('property_create'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('certification'))
        self.assertFalse(Property.objects.filter(owner=self.owner).exists())

    def test_owner_cannot_edit_another_owners_property(self):
        prop = Property.objects.create(
            owner=self.owner,
            property_type=self.ptype,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            neighborhood='Golf',
            monthly_rent=Decimal('300000'),
            max_occupants=4,
        )
        PropertyPublication.objects.create(property=prop, status='DRAFT')
        self.client.force_login(self.other)
        response = self.client.get(reverse('property_edit', args=[prop.property_id]))
        self.assertIn(response.status_code, {302, 403, 404})

    def test_submission_requires_declarations_and_collaboration(self):
        prop = Property.objects.create(
            owner=self.owner,
            property_type=self.ptype,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            neighborhood='Golf',
            monthly_rent=Decimal('300000'),
            max_occupants=4,
        )
        PropertyPublication.objects.create(property=prop, status='DRAFT')
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('property_edit', args=[prop.property_id]),
            {
                'submit': '1',
                'province': 'Haut-Katanga',
                'city_or_territory': 'Lubumbashi',
                'neighborhood': 'Golf',
                'monthly_rent': '300000',
                'max_occupants': '4',
                'bedroom_count': '2',
                'living_room_count': '1',
                'bathroom_count': '1',
                'toilet_count': '1',
                'has_kitchen': 'yes',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        prop.refresh_from_db()
        self.assertEqual(prop.status, 'DRAFT')
        self.assertEqual(prop.publication.status, 'DRAFT')

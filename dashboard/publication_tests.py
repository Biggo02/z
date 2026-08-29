from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification
from properties.models import CollaborationConsent, Property, PropertyDeclaration, PropertyPublication, PropertyType
from users.models import User


class PublicationModerationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='publication-owner@example.com', password='A-secure-password-123', phone='+243900009001', last_name='Owner', first_name='Publication', is_certified=True)
        self.staff = User.objects.create_user(email='publication-staff@example.com', password='A-secure-password-123', phone='+243900009002', last_name='Staff', first_name='Publication', is_staff=True)
        ptype = PropertyType.objects.create(name='Maison publication')
        self.property = Property.objects.create(owner=self.owner, property_type=ptype, province='Haut-Katanga', city_or_territory='Lubumbashi', neighborhood='Golf', bedroom_count=2, living_room_count=1, max_occupants=4, monthly_rent=Decimal('300000'), status='UNDER_REVIEW')
        self.publication = PropertyPublication.objects.create(property=self.property, status='SUBMITTED')
        now = timezone.now()
        PropertyDeclaration.objects.create(publication=self.publication, relationship_to_property='Propriétaire', right_to_offer_confirmed=True, accuracy_confirmed=True, photos_authentic_confirmed=True, authorization_confirmed=True, acknowledged_responsibility=True, accepted_at=now)
        CollaborationConsent.objects.create(publication=self.publication, verification_accepted=True, presentation_accepted=True, visits_accepted=True, management_accepted=True, collaboration_accepted=True, terms_version='v1', accepted_at=now)

    def test_staff_can_publish_submission(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_publication_decision', args=[self.publication.publication_id]), {'action': 'approve'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.publication.refresh_from_db(); self.property.refresh_from_db()
        self.assertEqual(self.publication.status, 'PUBLISHED')
        self.assertEqual(self.property.status, 'AVAILABLE')
        self.assertTrue(Notification.objects.filter(recipient=self.owner, object_id=self.publication.publication_id).exists())

    def test_staff_can_request_correction_with_reason(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_publication_decision', args=[self.publication.publication_id]), {'action': 'correction', 'reason': 'Corriger la localisation et ajouter les informations manquantes.'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.publication.refresh_from_db(); self.property.refresh_from_db()
        self.assertEqual(self.publication.status, 'CORRECTION_REQUIRED')
        self.assertEqual(self.property.status, 'DRAFT')
        self.assertIn('Corriger la localisation', self.publication.correction_message)
        self.assertTrue(Notification.objects.filter(recipient=self.owner, object_id=self.publication.publication_id, level='ACTION').exists())

    def test_correction_requires_reason(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_publication_decision', args=[self.publication.publication_id]), {'action': 'correction'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'SUBMITTED')

    def test_non_staff_cannot_moderate_publication(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('office_publication_decision', args=[self.publication.publication_id]), {'action': 'approve'}, follow=True)
        self.assertIn(response.status_code, {200, 302, 403})
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'SUBMITTED')

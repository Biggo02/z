from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from properties.models import CollaborationConsent, Property, PropertyDeclaration, PropertyPhoto, PropertyPublication, PropertyType


class PropertyPublicationFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='bailleur@example.com', password='pass12345', phone='0990000000',
            last_name='Test', first_name='Bailleur', is_certified=True,
        )
        self.client.force_login(self.user)
        self.property_type, _ = PropertyType.objects.get_or_create(name='Maison', defaults={'active': True})
        if not self.property_type.active:
            self.property_type.active = True
            self.property_type.save(update_fields=['active'])

    def make_property(self, ready=False, status='DRAFT', publication_status='DRAFT'):
        prop = Property.objects.create(
            owner=self.user, property_type=self.property_type,
            province='Haut-Katanga', city_or_territory='Lubumbashi', neighborhood='Golf',
            avenue_street='Avenue Test', address_number='10', monthly_rent=500,
            max_occupants=4, bedroom_count=1, living_room_count=1, bathroom_count=1,
            toilet_count=1, has_kitchen=True, status=status,
        )
        publication = PropertyPublication.objects.create(property=prop, status=publication_status)
        if ready:
            now = timezone.now()
            PropertyDeclaration.objects.create(
                publication=publication, relationship_to_property='Propriétaire',
                right_to_offer_confirmed=True, accuracy_confirmed=True,
                photos_authentic_confirmed=True, authorization_confirmed=True,
                acknowledged_responsibility=True, accepted_at=now,
            )
            CollaborationConsent.objects.create(
                publication=publication, terms_version='v1', verification_accepted=True,
                presentation_accepted=True, visits_accepted=True,
                management_accepted=True, collaboration_accepted=True, accepted_at=now,
            )
            for category, filename in [
                ('EXTERIOR', 'exterieur.jpg'), ('LIVING_ROOM', 'salon.jpg'),
                ('BEDROOM', 'chambre.jpg'), ('KITCHEN', 'cuisine.jpg'),
                ('BATHROOM', 'salle-de-bain.jpg'), ('TOILET', 'toilette.jpg'),
            ]:
                fake = SimpleUploadedFile(filename, b'fake-image', content_type='image/jpeg')
                PropertyPhoto.objects.create(property=prop, image=fake, category=category, order=1)
        return prop, publication

    def test_ready_draft_can_be_submitted(self):
        prop, publication = self.make_property(ready=True)
        response = self.client.post(reverse('property_submit', args=[prop.property_id]))
        self.assertRedirects(response, reverse('property_manage', args=[prop.property_id]))
        publication.refresh_from_db(); prop.refresh_from_db()
        self.assertEqual(publication.status, 'SUBMITTED')
        self.assertEqual(prop.status, 'UNDER_REVIEW')
        self.assertIsNotNone(publication.submitted_at)

    def test_incomplete_draft_cannot_be_submitted(self):
        prop, publication = self.make_property(ready=False)
        self.client.post(reverse('property_submit', args=[prop.property_id]))
        publication.refresh_from_db(); prop.refresh_from_db()
        self.assertEqual(publication.status, 'DRAFT')
        self.assertEqual(prop.status, 'DRAFT')

    def test_only_real_draft_can_be_deleted(self):
        prop, _ = self.make_property()
        response = self.client.post(reverse('property_delete_draft', args=[prop.property_id]))
        self.assertRedirects(response, reverse('my_properties'))
        self.assertFalse(Property.objects.filter(pk=prop.pk).exists())

    def test_submitted_property_cannot_be_deleted_as_draft(self):
        prop, _ = self.make_property(ready=True, status='UNDER_REVIEW', publication_status='SUBMITTED')
        response = self.client.post(reverse('property_delete_draft', args=[prop.property_id]))
        self.assertRedirects(response, reverse('property_manage', args=[prop.property_id]))
        self.assertTrue(Property.objects.filter(pk=prop.pk).exists())

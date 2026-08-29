from django.core.exceptions import ValidationError
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from .models import Property, PropertyPhoto, PropertyType
from .photo_optimization import save_photos as optimized_save_photos


class PropertyDynamicPhotoUploadTests(TestCase):
    PNG_1X1 = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff\xff\x7f\x00\t\xfb\x03\xfd*\x86\xe3\x8a'
        b'\x00\x00\x00\x00IEND\xaeB`\x82'
    )

    @classmethod
    def setUpTestData(cls):
        from users.models import User
        cls.user = User.objects.create_user(
            email='photo-test@example.com',
            password='test-password-123',
            is_certified=True,
        )
        cls.property_type = PropertyType.objects.create(name='Maison photo test')

    def setUp(self):
        self.property = Property.objects.create(
            owner=self.user,
            property_type=self.property_type,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            bedroom_count=2,
            living_room_count=1,
            bathroom_count=1,
            toilet_count=1,
            has_kitchen=True,
        )

    def upload(self, name):
        return SimpleUploadedFile(name, self.PNG_1X1, content_type='image/png')

    def request_with_files(self, files):
        return RequestFactory().post('/properties/create/', data=files)

    def test_photos_are_saved_one_per_declared_zone(self):
        request = self.request_with_files({
            'photos_exterior': [self.upload('exterior.png')],
            'photos_bedroom_1': [self.upload('bedroom-1.png')],
            'photos_bedroom_2': [self.upload('bedroom-2.png')],
            'photos_living_room_1': [self.upload('living.png')],
            'photos_kitchen': [self.upload('kitchen.png')],
            'photos_bathroom_1': [self.upload('bathroom.png')],
        })
        post = {
            'bedroom_count': '2',
            'living_room_count': '1',
            'bathroom_count': '1',
            'toilet_count': '1',
            'has_kitchen': 'yes',
        }

        optimized_save_photos(self.property, request, post)

        self.assertEqual(self.property.photos.count(), 6)
        self.assertEqual(self.property.photos.filter(category='BEDROOM', order=1).count(), 1)
        self.assertEqual(self.property.photos.filter(category='BEDROOM', order=2).count(), 1)
        self.assertEqual(self.property.photos.filter(category='LIVING_ROOM', order=1).count(), 1)
        self.assertEqual(self.property.photos.filter(category='KITCHEN', order=1).count(), 1)
        self.assertEqual(self.property.photos.filter(category='BATHROOM', order=1).count(), 1)
        self.assertEqual(self.property.photos.filter(category='EXTERIOR', order=1).count(), 1)
        self.assertTrue(self.property.photos.get(category='EXTERIOR', order=1).is_primary)

    def test_each_declared_zone_rejects_a_second_photo(self):
        request = self.request_with_files({
            'photos_bedroom_1': [self.upload('bedroom-1-a.png'), self.upload('bedroom-1-b.png')],
        })
        post = {
            'bedroom_count': '1',
            'living_room_count': '0',
            'bathroom_count': '0',
            'toilet_count': '0',
            'has_kitchen': 'no',
        }

        with self.assertRaisesMessage(ValidationError, 'Chambre 1 : maximum 1 photo.'):
            optimized_save_photos(self.property, request, post)
        self.assertEqual(PropertyPhoto.objects.filter(property=self.property).count(), 0)

    def test_no_global_photo_limit_for_many_declared_zones(self):
        self.property.bedroom_count = 41
        self.property.save(update_fields=['bedroom_count'])

        for number in range(1, 42):
            PropertyPhoto.objects.create(
                property=self.property,
                image=self.upload(f'bedroom-{number}.png'),
                category='BEDROOM',
                order=number,
            )

        request = self.request_with_files({'photos_exterior': [self.upload('exterior.png')]})
        post = {
            'bedroom_count': '41',
            'living_room_count': '0',
            'bathroom_count': '0',
            'toilet_count': '0',
            'has_kitchen': 'no',
        }

        optimized_save_photos(self.property, request, post)

        self.assertEqual(self.property.photos.count(), 42)
        self.assertEqual(self.property.photos.filter(category='EXTERIOR', order=1).count(), 1)
        self.assertEqual(self.property.photos.filter(category='BEDROOM').count(), 41)

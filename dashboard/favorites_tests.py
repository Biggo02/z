from django.test import TestCase
from django.urls import reverse
from properties.models import Favorite, Property, PropertyType
from users.models import User

class FavoriteFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='favorite@example.com', password='A-secure-password-123', phone='+243900007001', last_name='Favorite', first_name='User')
        self.ptype = PropertyType.objects.create(name='Maison favorite')
        self.property = Property.objects.create(owner=self.user, property_type=self.ptype, province='Haut-Katanga', city_or_territory='Lubumbashi', neighborhood='Golf', monthly_rent=300000, max_occupants=4, status='AVAILABLE')

    def test_toggle_favorite(self):
        self.client.force_login(self.user)
        self.client.post(reverse('toggle_favorite', args=[self.property.property_id]))
        self.assertTrue(Favorite.objects.filter(user=self.user, property=self.property).exists())
        self.client.post(reverse('toggle_favorite', args=[self.property.property_id]))
        self.assertFalse(Favorite.objects.filter(user=self.user, property=self.property).exists())

    def test_favorites_are_private_to_authenticated_user(self):
        self.client.force_login(self.user)
        self.client.post(reverse('toggle_favorite', args=[self.property.property_id]))
        other = User.objects.create_user(email='favorite-other@example.com', password='A-secure-password-123', phone='+243900007002', last_name='Other', first_name='User')
        self.client.force_login(other)
        response = self.client.get(reverse('favorites'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.property.property_id)

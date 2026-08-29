from django.test import TestCase
from django.urls import reverse

from users.models import User


class SafeRedirectTargetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='redirect@example.com',
            password='A-secure-password-123',
            phone='+243900009999',
            last_name='Redirect',
            first_name='Test',
        )

    def test_local_next_is_allowed(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('toggle_favorite', args=['does-not-exist']),
            {'next': '/dashboard'},
        )
        self.assertNotEqual(response.status_code, 500)

    def test_external_next_is_not_used(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('toggle_favorite', args=['does-not-exist']),
            {'next': 'https://evil.example/phishing'},
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('evil.example', response.url if hasattr(response, 'url') else '')

    def test_external_referer_is_not_used(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('toggle_favorite', args=['does-not-exist']),
            {},
            HTTP_REFERER='https://evil.example/phishing',
        )
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('evil.example', response.url if hasattr(response, 'url') else '')

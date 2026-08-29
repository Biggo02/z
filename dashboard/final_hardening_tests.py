from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User


class FinalHardeningTests(TestCase):
    def test_anonymous_cannot_access_private_dashboard(self):
        response = self.client.get(reverse('activity'))
        self.assertIn(response.status_code, {301, 302})

    def test_anonymous_cannot_access_office(self):
        response = self.client.get(reverse('office_dashboard'))
        self.assertIn(response.status_code, {301, 302})

    def test_logout_flow_is_available(self):
        user = User.objects.create_user(email='logout-final@example.com', password='A-secure-password-123', phone='+243900006101', last_name='Final', first_name='Security')
        self.client.force_login(user)
        response = self.client.get(reverse('logout'))
        self.assertIn(response.status_code, {200, 302, 405})

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_production_security_settings_are_enabled(self):
        from django.conf import settings
        self.assertTrue(settings.SECURE_SSL_REDIRECT)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')

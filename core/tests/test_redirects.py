from django.test import RequestFactory, SimpleTestCase

from core.redirects import safe_redirect_target


class SafeRedirectTargetTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_local_path_is_allowed(self):
        request = self.factory.get('/favorites/')
        self.assertEqual(safe_redirect_target(request, '/dashboard/'), '/dashboard/')

    def test_same_host_absolute_url_is_allowed(self):
        request = self.factory.get('/favorites/')
        self.assertEqual(
            safe_redirect_target(request, 'http://testserver/dashboard/'),
            'http://testserver/dashboard/',
        )

    def test_external_url_falls_back(self):
        request = self.factory.get('/favorites/')
        self.assertEqual(
            safe_redirect_target(request, 'https://evil.example/phishing'),
            'home',
        )

    def test_protocol_relative_external_url_falls_back(self):
        request = self.factory.get('/favorites/')
        self.assertEqual(
            safe_redirect_target(request, '//evil.example/phishing'),
            'home',
        )

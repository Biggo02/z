from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse


class AdminSmokeTests(TestCase):
    """Vérifie que les parcours essentiels de l'administration ne renvoient pas 500."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin_user = User.objects.create_superuser(
            email='admin-smoke@example.test',
            password='AdminSmokePass123!',
            phone='+243000000001',
            last_name='Admin',
            first_name='Smoke',
        )

    def test_all_registered_admin_routes_render(self):
        self.client.force_login(self.admin_user)
        failures = []

        for model in admin.site._registry:
            opts = model._meta
            base = f'admin:{opts.app_label}_{opts.model_name}'
            routes = [(f'{base}_changelist', 'liste'), (f'{base}_add', 'ajout')]

            obj = model.objects.order_by('pk').first()
            if obj is not None:
                routes.append((f'{base}_change', 'modification'))

            for url_name, label in routes:
                try:
                    url = reverse(url_name, args=[obj.pk]) if url_name.endswith('_change') else reverse(url_name)
                except NoReverseMatch:
                    continue
                except Exception as exc:  # noqa: BLE001
                    failures.append(f'{url_name} ({label}): {type(exc).__name__}: {exc}')
                    continue

                try:
                    response = self.client.get(url)
                except Exception as exc:  # noqa: BLE001
                    failures.append(f'{url_name} ({label}): {type(exc).__name__}: {exc}')
                    continue

                if response.status_code >= 500:
                    failures.append(f'{url_name} ({label}): HTTP {response.status_code}')

        self.assertFalse(
            failures,
            'Erreurs de parcours Admin détectées :\n' + '\n'.join(failures),
        )

    def test_admin_is_french(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Administration Fasthome', response.content.decode('utf-8'))

    def test_no_ambiguous_parentheses_plural_in_templates(self):
        """Interdit les formulations visibles du type « logement(s) »."""
        templates_root = Path(__file__).resolve().parents[1] / 'templates'
        offenders = []
        for path in templates_root.rglob('*.html'):
            text = path.read_text(encoding='utf-8')
            if '(s)' in text:
                offenders.append(str(path.relative_to(templates_root.parent)))
        self.assertFalse(
            offenders,
            'Formulations « (s) » encore présentes dans :\n' + '\n'.join(offenders),
        )

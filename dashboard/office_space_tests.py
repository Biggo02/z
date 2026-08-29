from django.test import TestCase
from django.urls import reverse

from users.models import User


class OfficeSpaceTests(TestCase):
    def setUp(self):
        self.agent = User.objects.create_user(
            email='agent@fasthome.test',
            password='AgentPassword123!',
            phone='0990000001',
            first_name='Agent',
            last_name='Test',
            is_staff=True,
        )
        self.admin = User.objects.create_superuser(
            email='admin@fasthome.test',
            password='AdminPassword123!',
            phone='0990000002',
            first_name='Admin',
            last_name='Test',
        )
        self.user = User.objects.create_user(
            email='user@fasthome.test',
            password='UserPassword123!',
            phone='0990000003',
            first_name='User',
            last_name='Test',
        )

    def test_agent_can_open_operational_office_but_not_user_admin_area(self):
        self.client.force_login(self.agent)
        self.assertEqual(self.client.get(reverse('office_dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('office_users')).status_code, 302)

    def test_admin_can_open_office_and_user_management(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('office_dashboard')).status_code, 200)
        response = self.client.get(reverse('office_users'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'agent@fasthome.test')
        self.assertContains(response, 'ADMIN')

    def test_normal_user_cannot_open_office(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('office_dashboard')).status_code, 302)
        self.assertEqual(self.client.get(reverse('office_users')).status_code, 302)

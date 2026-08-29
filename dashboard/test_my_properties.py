from django.test import SimpleTestCase
from django.urls import reverse


class MyPropertiesRoutingTests(SimpleTestCase):
    def test_my_properties_routes_exist(self):
        self.assertEqual(reverse('my_properties'), '/dashboard/properties/')
        self.assertEqual(reverse('property_manage', args=['FP-TEST']), '/dashboard/properties/FP-TEST/')

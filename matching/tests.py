from decimal import Decimal

from django.test import TestCase

from properties.models import Property, PropertyType
from users.models import User
from .models import SearchRequest
from .views import score_property


class MatchingCriteriaTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='matching-owner@example.com', password='A-secure-password-123',
            phone='+243900000301', last_name='Matching', first_name='Owner',
        )
        property_type = PropertyType.objects.create(name='Appartement matching')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=property_type,
            furnished=True,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            administrative_subdivision='Commune Lubumbashi',
            neighborhood='Golf',
            bedroom_count=3,
            living_room_count=2,
            max_occupants=5,
            monthly_rent=Decimal('350000'),
            status='AVAILABLE',
        )

    def make_search(self, **overrides):
        data = dict(
            furnished_preference='YES',
            province='haut-katanga',
            city_or_territory='LUBUMBASHI',
            administrative_subdivision='Commune Lubumbashi',
            neighborhood='golf',
            minimum_living_rooms=2,
            minimum_bedrooms=3,
            maximum_budget=Decimal('400000'),
            requested_occupants=4,
        )
        data.update(overrides)
        return SearchRequest.objects.create(**data)

    def test_all_defined_criteria_must_match(self):
        search = self.make_search()
        score, breakdown = score_property(self.property, search)
        self.assertEqual(score, Decimal('100'))
        self.assertTrue(all(value == 100 for value in breakdown.values()))

    def test_one_failed_criterion_rejects_property(self):
        search = self.make_search(maximum_budget=Decimal('300000'))
        score, breakdown = score_property(self.property, search)
        self.assertEqual(score, Decimal('0'))
        self.assertEqual(breakdown['budget'], 0)

    def test_typo_and_accents_in_location_are_accepted(self):
        search = self.make_search(
            province='Haut Katanga',
            city_or_territory='Lubumbashii',
            neighborhood='Gollf',
        )
        score, breakdown = score_property(self.property, search)
        self.assertEqual(score, Decimal('100'))
        self.assertEqual(breakdown['province'], 100)
        self.assertEqual(breakdown['city'], 100)
        self.assertEqual(breakdown['neighborhood'], 100)

    def test_non_matching_location_is_rejected(self):
        search = self.make_search(city_or_territory='Likasi')
        score, breakdown = score_property(self.property, search)
        self.assertEqual(score, Decimal('0'))
        self.assertEqual(breakdown['city'], 0)

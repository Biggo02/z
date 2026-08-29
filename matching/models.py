from django.conf import settings
from django.db import models

class SearchRequest(models.Model):
    FURNISHED = [('YES', 'Oui'), ('NO', 'Non'), ('ANY', "Peu importe")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    furnished_preference = models.CharField(max_length=3, choices=FURNISHED, default='ANY')
    province = models.CharField(max_length=100)
    city_or_territory = models.CharField(max_length=120)
    administrative_subdivision = models.CharField(max_length=160, blank=True)
    neighborhood = models.CharField(max_length=160, blank=True)
    minimum_living_rooms = models.PositiveIntegerField(default=0)
    minimum_bedrooms = models.PositiveIntegerField(default=0)
    maximum_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    requested_occupants = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class MatchingResult(models.Model):
    search = models.ForeignKey(SearchRequest, on_delete=models.CASCADE, related_name='results')
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    criteria_breakdown = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-score']

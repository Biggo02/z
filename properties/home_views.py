from django.shortcuts import render

from .models import Favorite, Property, PropertyType


def home_reference(request):
    properties = list(
        Property.objects.filter(
            status='AVAILABLE',
            publication__status='PUBLISHED',
        )
        .select_related('property_type')
        .prefetch_related('photos')[:24]
    )
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(
                user=request.user,
                property_id__in=[p.pk for p in properties],
            ).values_list('property_id', flat=True)
        )
    property_types = PropertyType.objects.filter(active=True).order_by('name')
    return render(request, 'home_new.html', {
        'properties': properties,
        'favorite_ids': favorite_ids,
        'property_types': property_types,
    })

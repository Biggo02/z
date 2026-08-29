from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Property, PropertyPublication, PropertyType
from .views import (
    _positive,
    _service_days,
    _address_from_post,
    _save_dynamic_details,
    _save_consents,
    _save_photos,
)


@login_required
@transaction.atomic
def property_autosave(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Méthode non autorisée.'}, status=405)
    if not request.user.is_certified:
        return JsonResponse({'ok': False, 'error': 'Votre compte doit être certifié.'}, status=403)

    post = request.POST
    property_id = (post.get('property_id') or '').strip()
    prop_type_id = post.get('property_type')

    if property_id:
        prop = get_object_or_404(
            Property.objects.select_for_update().select_related('publication', 'property_type'),
            property_id=property_id,
            owner=request.user,
        )
        if prop.status not in {'DRAFT'} or prop.publication.status not in {'DRAFT', 'CORRECTION_REQUIRED'}:
            return JsonResponse({'ok': False, 'error': 'Ce logement n’est plus un brouillon.'}, status=409)
    else:
        if not prop_type_id:
            return JsonResponse({'ok': False, 'error': 'Sélectionnez d’abord le type de logement.'}, status=400)
        prop_type = get_object_or_404(PropertyType, pk=prop_type_id, active=True)
        prop = Property.objects.create(
            owner=request.user,
            property_type=prop_type,
            province='',
            city_or_territory='',
            neighborhood='',
            avenue_street='',
            address_number='',
            max_occupants=1,
            status='DRAFT',
        )
        PropertyPublication.objects.create(property=prop, status='DRAFT')
        prop = Property.objects.select_for_update().select_related('publication', 'property_type').get(pk=prop.pk)

    if prop_type_id:
        prop.property_type_id = prop_type_id
    prop.furnished = post.get('furnished') == 'yes'
    prop.bedroom_count = _positive(post.get('bedroom_count'), prop.bedroom_count)
    prop.living_room_count = _positive(post.get('living_room_count'), prop.living_room_count)
    prop.bathroom_count = _positive(post.get('bathroom_count'), prop.bathroom_count)
    prop.toilet_count = _positive(post.get('toilet_count'), prop.toilet_count)
    prop.has_kitchen = post.get('has_kitchen') == 'yes'
    prop.floor = post.get('floor', '').strip()
    prop.ceiling_type = post.get('ceiling_type', '').strip()
    prop.floor_type = post.get('floor_type', '').strip()
    prop.electricity_source = post.get('electricity_source', '').strip()
    prop.electricity_days_per_week = _service_days(post.get('electricity_days_per_week'))
    prop.water_source = post.get('water_source', '').strip()
    prop.water_days_per_week = _service_days(post.get('water_days_per_week'))
    prop.province = post.get('province', '').strip()
    prop.city_or_territory = post.get('city_or_territory', '').strip()
    prop.administrative_subdivision = post.get('administrative_subdivision', '').strip()
    prop.neighborhood = post.get('neighborhood', '').strip()
    prop.avenue_street = post.get('avenue_street', '').strip()
    prop.address_number = post.get('address_number', '').strip()
    prop.exact_address = _address_from_post(post)
    prop.google_maps_url = post.get('google_maps_url', '').strip()
    prop.latitude = post.get('latitude') or None
    prop.longitude = post.get('longitude') or None
    prop.monthly_rent = post.get('monthly_rent') or None
    prop.guarantee_amount = post.get('guarantee_amount') or None
    prop.max_occupants = max(1, _positive(post.get('max_occupants'), prop.max_occupants))
    prop.save()

    _save_dynamic_details(prop, post)
    _save_consents(prop.publication, post)
    _save_photos(prop, request, post)

    return JsonResponse({
        'ok': True,
        'property_id': prop.property_id,
        'publication_id': prop.publication.publication_id,
        'status': prop.status,
        'message': 'Brouillon sauvegardé automatiquement.',
    })

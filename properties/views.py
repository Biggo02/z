from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Bathroom, Bedroom, CollaborationConsent, Kitchen, LivingRoom, Property,
    PropertyDeclaration, PropertyFeature, PropertyPhoto, PropertyPublication, PropertyType, Toilet,
    Favorite,
)

FEATURE_OPTIONS = [
    ('courtyard', 'Cour'), ('garden', 'Jardin'), ('terrace', 'Terrasse'),
    ('balcony', 'Balcon'), ('veranda', 'Véranda'), ('parking', 'Parking'), ('garage', 'Garage'),
    ('security_guard', 'Gardien'), ('fence', 'Clôture'), ('secure_door', 'Porte sécurisée'),
    ('cameras', 'Caméras'), ('alarm', 'Alarme'), ('secure_parking', 'Parking sécurisé'),
]
PHOTO_MAX_PER_ROOM = 5
PHOTO_MAX_TOTAL = 40
PHOTO_CATEGORIES = {
    'exterior': 'EXTERIOR', 'living_room': 'LIVING_ROOM', 'bedroom': 'BEDROOM',
    'kitchen': 'KITCHEN', 'bathroom': 'BATHROOM', 'toilet': 'TOILET',
    'parking': 'PARKING', 'garden': 'GARDEN',
}


def home(request):
    properties = list(Property.objects.filter(status='AVAILABLE', publication__status='PUBLISHED').select_related('property_type').prefetch_related('photos')[:24])
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(Favorite.objects.filter(user=request.user, property_id__in=[p.pk for p in properties]).values_list('property_id', flat=True))
    return render(request, 'home.html', {'properties': properties, 'favorite_ids': favorite_ids})


def property_detail(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('property_type').prefetch_related('photos', 'features', 'bedrooms', 'living_rooms', 'bathrooms', 'toilets'), property_id=property_id)
    photos = list(prop.photos.all().order_by('order', 'id'))
    return render(request, 'properties/detail.html', {'property': prop, 'property_photos': photos})


def _positive(value, default=0):
    try:
        return max(0, int(value or default))
    except (TypeError, ValueError):
        return default


def _service_days(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 7 else None


def _address_from_post(post):
    avenue = post.get('avenue_street', '').strip()
    number = post.get('address_number', '').strip()
    if avenue and number:
        return f'{avenue}, n° {number}'
    return avenue or number


def _photo_slots(post):
    slots = [('exterior', 'Extérieur', PHOTO_CATEGORIES['exterior'], 1)]
    for i in range(1, _positive(post.get('living_room_count')) + 1): slots.append((f'living_room_{i}', f'Salon {i}', PHOTO_CATEGORIES['living_room'], i))
    for i in range(1, _positive(post.get('bedroom_count')) + 1): slots.append((f'bedroom_{i}', f'Chambre {i}', PHOTO_CATEGORIES['bedroom'], i))
    if post.get('has_kitchen') == 'yes': slots.append(('kitchen', 'Cuisine', PHOTO_CATEGORIES['kitchen'], 1))
    for i in range(1, _positive(post.get('bathroom_count')) + 1): slots.append((f'bathroom_{i}', f'Salle de bain {i}', PHOTO_CATEGORIES['bathroom'], i))
    for i in range(1, _positive(post.get('toilet_count')) + 1): slots.append((f'toilet_{i}', f'Toilette {i}', PHOTO_CATEGORIES['toilet'], i))
    if post.get('parking') == 'on' or post.get('garage') == 'on': slots.append(('parking', 'Parking / Garage', PHOTO_CATEGORIES['parking'], 1))
    if post.get('garden') == 'on': slots.append(('garden', 'Jardin', PHOTO_CATEGORIES['garden'], 1))
    return slots


def _save_dynamic_details(prop, post):
    prop.bedrooms.all().delete()
    for number in range(1, _positive(post.get('bedroom_count')) + 1):
        Bedroom.objects.create(property=prop, number=number, bed_type=post.get(f'bed_{number}_type', ''), mattress=post.get(f'bed_{number}_mattress') == 'on', wardrobe=post.get(f'bed_{number}_wardrobe') == 'on', bedside_table=post.get(f'bed_{number}_bedside') == 'on', desk=post.get(f'bed_{number}_desk') == 'on', chair=post.get(f'bed_{number}_chair') == 'on', curtains=post.get(f'bed_{number}_curtains') == 'on', mosquito_net=post.get(f'bed_{number}_mosquito') == 'on', fan=post.get(f'bed_{number}_fan') == 'on', air_conditioning=post.get(f'bed_{number}_ac') == 'on')
    prop.living_rooms.all().delete()
    for number in range(1, _positive(post.get('living_room_count')) + 1):
        LivingRoom.objects.create(property=prop, number=number, sofa=post.get(f'living_{number}_sofa') == 'on', coffee_table=post.get(f'living_{number}_table') == 'on', television=post.get(f'living_{number}_tv') == 'on', curtains=post.get(f'living_{number}_curtains') == 'on', fan=post.get(f'living_{number}_fan') == 'on', air_conditioning=post.get(f'living_{number}_ac') == 'on')
    prop.bathrooms.all().delete()
    for number in range(1, _positive(post.get('bathroom_count')) + 1):
        Bathroom.objects.create(property=prop, number=number, location_type=post.get(f'bathroom_{number}_location', 'INTERIOR'), access_type=post.get(f'bathroom_{number}_access', ''), hot_water=post.get(f'bathroom_{number}_hot') == 'on', shower=post.get(f'bathroom_{number}_shower') == 'on', bathtub=post.get(f'bathroom_{number}_bathtub') == 'on', sink=post.get(f'bathroom_{number}_sink') == 'on', mirror=post.get(f'bathroom_{number}_mirror') == 'on', storage=post.get(f'bathroom_{number}_storage') == 'on')
    prop.toilets.all().delete()
    for number in range(1, _positive(post.get('toilet_count')) + 1):
        Toilet.objects.create(property=prop, number=number, location_type=post.get(f'toilet_{number}_location', 'INTERIOR'), access_type=post.get(f'toilet_{number}_access', ''), toilet_type=post.get(f'toilet_{number}_type', 'BOWL'))
    if prop.has_kitchen:
        kitchen, _ = Kitchen.objects.get_or_create(property=prop)
        kitchen.equipped = post.get('kitchen_equipped') == 'on'
        for field in ['stove', 'oven', 'refrigerator', 'freezer', 'microwave', 'hood', 'sink', 'cupboards', 'table', 'chairs']: setattr(kitchen, field, post.get(f'kitchen_{field}') == 'on')
        kitchen.save()
    else: Kitchen.objects.filter(property=prop).delete()
    prop.features.all().delete()
    exterior = {'courtyard', 'garden', 'terrace', 'balcony', 'veranda', 'parking', 'garage'}
    for key, _label in FEATURE_OPTIONS:
        if post.get(key) == 'on': PropertyFeature.objects.create(property=prop, key=key, category='EXTERIOR' if key in exterior else 'SECURITY', value='true')


def _save_consents(publication, post):
    declaration, _ = PropertyDeclaration.objects.get_or_create(publication=publication, defaults={'relationship_to_property': ''})
    declaration.relationship_to_property = post.get('relationship_to_property', '').strip()
    declaration.right_to_offer_confirmed = post.get('right_to_offer_confirmed') == 'on'
    declaration.accuracy_confirmed = post.get('accuracy_confirmed') == 'on'
    declaration.photos_authentic_confirmed = post.get('photos_authentic_confirmed') == 'on'
    declaration.authorization_confirmed = post.get('authorization_confirmed') == 'on'
    declaration.acknowledged_responsibility = post.get('acknowledged_responsibility') == 'on'
    declaration.accepted_at = timezone.now() if all([declaration.right_to_offer_confirmed, declaration.accuracy_confirmed, declaration.photos_authentic_confirmed, declaration.authorization_confirmed, declaration.acknowledged_responsibility]) else None
    declaration.save()
    consent, _ = CollaborationConsent.objects.get_or_create(publication=publication, defaults={'terms_version': 'v1'})
    consent.verification_accepted = post.get('verification_accepted') == 'on'
    consent.presentation_accepted = post.get('presentation_accepted') == 'on'
    consent.visits_accepted = post.get('visits_accepted') == 'on'
    consent.management_accepted = post.get('management_accepted') == 'on'
    consent.collaboration_accepted = post.get('collaboration_accepted') == 'on'
    consent.accepted_at = timezone.now() if all([consent.verification_accepted, consent.presentation_accepted, consent.visits_accepted, consent.management_accepted, consent.collaboration_accepted]) else None
    consent.save()


def _context(**extra):
    return {'features': FEATURE_OPTIONS, 'electricity_sources': Property.ELECTRICITY_SOURCES, 'water_sources': Property.WATER_SOURCES, 'floor_types': Property.FLOOR_TYPES, 'ceiling_types': Property.CEILING_TYPES, **extra}


def _validate_publication_ready(publication):
    if not publication.declaration.accepted_at: raise ValidationError('Toutes les déclarations obligatoires doivent être acceptées.')
    if not publication.collaboration_consent.accepted_at: raise ValidationError('Toutes les conditions de collaboration avec Fasthome doivent être acceptées.')
    prop = publication.property
    if not all([prop.province, prop.city_or_territory, prop.neighborhood, prop.avenue_street, prop.address_number]): raise ValidationError('La localisation et l’adresse exacte du logement sont incomplètes. Renseignez les champs de localisation et l’adresse exacte.')
    if not prop.monthly_rent or prop.monthly_rent <= 0: raise ValidationError('Le loyer mensuel doit être renseigné et supérieur à zéro.')
    if not prop.max_occupants or prop.max_occupants < 1: raise ValidationError('La capacité maximale d’occupants doit être supérieure à zéro.')


def _save_photos(prop, request, post):
    uploads_by_slot = []
    total_new = 0
    for slot_key, label, category, room_number in _photo_slots(post):
        files = request.FILES.getlist(f'photos_{slot_key}')
        if len(files) > PHOTO_MAX_PER_ROOM: raise ValidationError(f'{label} : maximum {PHOTO_MAX_PER_ROOM} photos.')
        if files: uploads_by_slot.append((label, category, room_number, files)); total_new += len(files)
    if total_new == 0: return
    existing_total = prop.photos.count()
    if existing_total + total_new > PHOTO_MAX_TOTAL: raise ValidationError(f'Maximum {PHOTO_MAX_TOTAL} photos par logement.')
    for label, category, room_number, files in uploads_by_slot:
        existing_slot = prop.photos.filter(category=category, order=room_number).count()
        if existing_slot + len(files) > PHOTO_MAX_PER_ROOM: raise ValidationError(f'{label} : il reste seulement {PHOTO_MAX_PER_ROOM - existing_slot} emplacement(s) photo.')
        for image in files:
            PropertyPhoto.objects.create(property=prop, image=image, category=category, order=room_number, is_primary=(existing_total == 0))
            existing_total += 1


@login_required
def property_create(request):
    if not request.user.is_certified:
        messages.error(request, 'Votre compte doit être certifié avant de publier un logement.')
        return redirect('certification')
    types = PropertyType.objects.filter(active=True)
    if request.method == 'POST':
        prop_type = get_object_or_404(PropertyType, pk=request.POST.get('property_type'))
        try:
            with transaction.atomic():
                prop = Property.objects.create(owner=request.user, property_type=prop_type, furnished=request.POST.get('furnished') == 'yes', province=request.POST.get('province', '').strip(), city_or_territory=request.POST.get('city_or_territory', '').strip(), administrative_subdivision=request.POST.get('administrative_subdivision', '').strip(), neighborhood=request.POST.get('neighborhood', '').strip(), avenue_street=request.POST.get('avenue_street', '').strip(), address_number=request.POST.get('address_number', '').strip(), exact_address=_address_from_post(request.POST), google_maps_url=request.POST.get('google_maps_url', '').strip(), bedroom_count=_positive(request.POST.get('bedroom_count')), living_room_count=_positive(request.POST.get('living_room_count')), bathroom_count=_positive(request.POST.get('bathroom_count')), toilet_count=_positive(request.POST.get('toilet_count')), has_kitchen=request.POST.get('has_kitchen') == 'yes', floor=request.POST.get('floor', '').strip(), ceiling_type=request.POST.get('ceiling_type', '').strip(), floor_type=request.POST.get('floor_type', '').strip(), electricity_source=request.POST.get('electricity_source', '').strip(), electricity_days_per_week=_service_days(request.POST.get('electricity_days_per_week')), water_source=request.POST.get('water_source', '').strip(), water_days_per_week=_service_days(request.POST.get('water_days_per_week')), monthly_rent=request.POST.get('monthly_rent') or None, guarantee_amount=request.POST.get('guarantee_amount') or None, max_occupants=max(1, _positive(request.POST.get('max_occupants'), 1)))
                prop.save()
                publication = PropertyPublication.objects.create(property=prop, status='DRAFT')
                _save_dynamic_details(prop, request.POST)
                _save_consents(publication, request.POST)
                _save_photos(prop, request, request.POST)
            messages.success(request, f'Brouillon {publication.publication_id} créé pour le logement {prop.property_id}.')
            return redirect('property_edit', property_id=prop.property_id)
        except (ValidationError, TypeError, ValueError) as exc: messages.error(request, str(exc))
    return render(request, 'properties/form.html', _context(types=types, creating=True))


@login_required
def property_edit(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('publication', 'property_type'), property_id=property_id, owner=request.user)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                prop.furnished = request.POST.get('furnished') == 'yes'
                prop.bedroom_count = _positive(request.POST.get('bedroom_count'), prop.bedroom_count)
                prop.living_room_count = _positive(request.POST.get('living_room_count'), prop.living_room_count)
                prop.bathroom_count = _positive(request.POST.get('bathroom_count'), prop.bathroom_count)
                prop.toilet_count = _positive(request.POST.get('toilet_count'), prop.toilet_count)
                prop.has_kitchen = request.POST.get('has_kitchen') == 'yes'
                prop.floor = request.POST.get('floor', '').strip()
                prop.ceiling_type = request.POST.get('ceiling_type', '').strip()
                prop.floor_type = request.POST.get('floor_type', '').strip()
                prop.electricity_source = request.POST.get('electricity_source', '').strip()
                prop.electricity_days_per_week = _service_days(request.POST.get('electricity_days_per_week'))
                prop.water_source = request.POST.get('water_source', '').strip()
                prop.water_days_per_week = _service_days(request.POST.get('water_days_per_week'))
                prop.province = request.POST.get('province', '').strip()
                prop.city_or_territory = request.POST.get('city_or_territory', '').strip()
                prop.administrative_subdivision = request.POST.get('administrative_subdivision', '').strip()
                prop.neighborhood = request.POST.get('neighborhood', '').strip()
                prop.avenue_street = request.POST.get('avenue_street', '').strip()
                prop.address_number = request.POST.get('address_number', '').strip()
                prop.exact_address = _address_from_post(request.POST)
                prop.google_maps_url = request.POST.get('google_maps_url', '').strip()
                prop.latitude = request.POST.get('latitude') or None
                prop.longitude = request.POST.get('longitude') or None
                prop.monthly_rent = request.POST.get('monthly_rent') or None
                prop.guarantee_amount = request.POST.get('guarantee_amount') or None
                prop.max_occupants = max(1, _positive(request.POST.get('max_occupants'), prop.max_occupants))
                prop.save()
                _save_dynamic_details(prop, request.POST)
                _save_consents(prop.publication, request.POST)
                _save_photos(prop, request, request.POST)
                if request.POST.get('submit') == '1':
                    _validate_publication_ready(prop.publication)
                    prop.status = 'UNDER_REVIEW'
                    prop.publication.status = 'SUBMITTED'
                    prop.publication.submitted_at = timezone.now()
                    prop.publication.save(update_fields=['status', 'submitted_at', 'updated_at'])
                else:
                    prop.save(update_fields=['updated_at'])
            messages.success(request, 'Modifications enregistrées.')
            if request.POST.get('submit') == '1': messages.success(request, 'Publication soumise à Fasthome pour vérification.')
            return redirect('property_edit', property_id=prop.property_id)
        except (ValidationError, TypeError, ValueError) as exc: messages.error(request, str(exc))
    return render(request, 'properties/form.html', _context(types=PropertyType.objects.filter(active=True), property=prop, creating=False))

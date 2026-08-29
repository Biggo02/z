from decimal import Decimal
import re
import unicodedata
from difflib import SequenceMatcher

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import render

from properties.models import Property
from .models import MatchingResult, SearchRequest

LOCATION_FIELDS = ('province', 'city_or_territory', 'administrative_subdivision', 'neighborhood')


def _normalize(value):
    value = unicodedata.normalize('NFKD', value or '')
    value = ''.join(c for c in value if not unicodedata.combining(c)).casefold()
    value = re.sub(r'[^\w\s]', ' ', value, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', value).strip()


def _tokens(value):
    return _normalize(value).split()


def _location_match(actual, requested):
    actual_n, requested_n = _normalize(actual), _normalize(requested)
    if not actual_n or not requested_n:
        return False
    if actual_n == requested_n:
        return True
    actual_tokens, requested_tokens = _tokens(actual_n), _tokens(requested_n)
    if len(actual_tokens) != len(requested_tokens):
        return SequenceMatcher(None, actual_n, requested_n).ratio() >= 0.90
    return all(SequenceMatcher(None, a, b).ratio() >= 0.86 for a, b in zip(actual_tokens, requested_tokens))


def score_property(prop, search):
    checks = {}
    if search.maximum_budget is not None:
        checks['budget'] = prop.monthly_rent is not None and prop.monthly_rent <= search.maximum_budget
    for field, key in [('province', 'province'), ('city_or_territory', 'city'), ('administrative_subdivision', 'subdivision'), ('neighborhood', 'neighborhood')]:
        requested = getattr(search, field)
        if requested:
            checks[key] = _location_match(getattr(prop, field), requested)
    if search.minimum_bedrooms:
        checks['bedrooms'] = prop.bedroom_count >= search.minimum_bedrooms
    if search.minimum_living_rooms:
        checks['living_rooms'] = prop.living_room_count >= search.minimum_living_rooms
    if search.furnished_preference != 'ANY':
        checks['furnished'] = ((search.furnished_preference == 'YES') == prop.furnished)
    if search.requested_occupants:
        checks['occupants'] = prop.max_occupants >= search.requested_occupants
    matched = bool(checks) and all(checks.values())
    return (Decimal('100') if matched else Decimal('0'), {key: (100 if ok else 0) for key, ok in checks.items()})


def _post_int(request, name, default=0, minimum=0):
    raw = (request.POST.get(name) or '').strip()
    try:
        value = int(raw) if raw else default
    except ValueError as exc:
        raise ValidationError(f'Valeur invalide pour {name}.') from exc
    if value < minimum:
        raise ValidationError(f'Valeur invalide pour {name}.')
    return value


def matching(request):
    results, values = [], None
    if request.method == 'POST':
        values = request.POST
        try:
            requested_occupants = _post_int(request, 'requested_occupants', 1, 1)
            minimum_living_rooms = _post_int(request, 'minimum_living_rooms')
            minimum_bedrooms = _post_int(request, 'minimum_bedrooms')
            budget_raw = (request.POST.get('maximum_budget') or '').strip()
            maximum_budget = Decimal(budget_raw) if budget_raw else None
            if maximum_budget is not None and maximum_budget < 0:
                raise ValidationError('Le budget maximum ne peut pas être négatif.')
            furnished_preference = request.POST.get('furnished_preference', 'ANY')
            if furnished_preference not in {'ANY', 'YES', 'NO'}:
                raise ValidationError('Préférence meublé invalide.')
            search = SearchRequest.objects.create(
                user=request.user if request.user.is_authenticated else None,
                furnished_preference=furnished_preference,
                province=request.POST.get('province', '').strip(),
                city_or_territory=request.POST.get('city_or_territory', '').strip(),
                administrative_subdivision=request.POST.get('administrative_subdivision', '').strip(),
                neighborhood=request.POST.get('neighborhood', '').strip(),
                minimum_living_rooms=minimum_living_rooms,
                minimum_bedrooms=minimum_bedrooms,
                maximum_budget=maximum_budget,
                requested_occupants=requested_occupants,
            )
            filters = Q(status='AVAILABLE') & Q(publication__status='PUBLISHED')
            if maximum_budget is not None:
                filters &= Q(monthly_rent__isnull=False, monthly_rent__lte=maximum_budget)
            if minimum_bedrooms:
                filters &= Q(bedroom_count__gte=minimum_bedrooms)
            if minimum_living_rooms:
                filters &= Q(living_room_count__gte=minimum_living_rooms)
            if requested_occupants:
                filters &= Q(max_occupants__gte=requested_occupants)
            if furnished_preference == 'YES': filters &= Q(furnished=True)
            elif furnished_preference == 'NO': filters &= Q(furnished=False)
            # Text locations intentionally remain in Python because typo/accent tolerance is required.
            queryset = (Property.objects.filter(filters)
                        .select_related('property_type', 'publication')
                        .prefetch_related('photos')
                        .order_by('monthly_rent', 'property_id'))
            for prop in queryset:
                score, breakdown = score_property(prop, search)
                if score == Decimal('100'):
                    results.append(MatchingResult.objects.create(search=search, property=prop, score=score, criteria_breakdown=breakdown))
            results.sort(key=lambda item: (-item.score, item.property.monthly_rent or Decimal('999999999')))
        except (ValidationError, ArithmeticError) as exc:
            messages.error(request, str(exc))
    return render(request, 'matching/index.html', {'results': results, 'values': values})

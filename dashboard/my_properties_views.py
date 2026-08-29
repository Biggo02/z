from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from properties.models import Property


def _category(property_obj):
    """Return exactly one user-facing Mes logements category.

    Priority is intentional: once a publication is submitted it is NEVER
    considered incomplete, even if a legacy Property.status still says DRAFT.
    """
    publication = getattr(property_obj, 'publication', None)
    publication_status = getattr(publication, 'status', None)

    if property_obj.status == 'RENTED' or publication_status == 'RENTED':
        return 'rented'
    if property_obj.status == 'AVAILABLE' or publication_status == 'PUBLISHED':
        return 'available'
    if property_obj.status == 'UNDER_REVIEW' or publication_status in {'SUBMITTED', 'UNDER_REVIEW'}:
        return 'review'
    if publication_status in {'DRAFT', 'CORRECTION_REQUIRED'} or publication is None:
        return 'draft'
    return 'draft'


@login_required
def my_properties(request):
    properties = list(
        request.user.properties
        .select_related('property_type', 'publication')
        .prefetch_related('photos')
        .order_by('-updated_at', '-created_at')
    )
    categories = [_category(p) for p in properties]
    counts = {
        'all': len(properties),
        'available': categories.count('available'),
        'review': categories.count('review'),
        'draft': categories.count('draft'),
        'rented': categories.count('rented'),
    }
    return render(request, 'dashboard/my_properties.html', {'properties': properties, 'counts': counts})


@login_required
def property_manage(request, property_id):
    prop = get_object_or_404(
        Property.objects.select_related('property_type', 'publication').prefetch_related('photos'),
        property_id=property_id,
        owner=request.user,
    )
    return render(request, 'dashboard/property_manage.html', {
        'property': prop,
        'publication': getattr(prop, 'publication', None),
    })

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from notifications.services import publication_submitted
from properties.models import Property, PropertyPublication
from visits.models import VisitRequest


def _publication_checklist(property_obj, publication):
    missing = []
    if not property_obj.property_type_id:
        missing.append(('type', 'Le type de logement doit être renseigné.'))
    if not property_obj.province or not property_obj.city_or_territory or not property_obj.neighborhood:
        missing.append(('localisation', 'La province, la ville ou le territoire et le quartier sont obligatoires.'))
    if not property_obj.avenue_street or not property_obj.address_number:
        missing.append(('adresse', 'L’avenue ou la rue et le numéro doivent être renseignés.'))
    if property_obj.monthly_rent is None or property_obj.monthly_rent <= 0:
        missing.append(('loyer', 'Le loyer mensuel doit être renseigné.'))
    if property_obj.max_occupants < 1:
        missing.append(('capacite', 'La capacité maximale doit être supérieure à zéro.'))
    photos = property_obj.photos.all()
    if not photos.filter(category='EXTERIOR').exists():
        missing.append(('photos', 'Ajoutez au moins une photo de l’extérieur.'))
    required_categories = []
    if property_obj.living_room_count:
        required_categories.append(('LIVING_ROOM', 'salon'))
    if property_obj.bedroom_count:
        required_categories.append(('BEDROOM', 'chambre'))
    if property_obj.has_kitchen:
        required_categories.append(('KITCHEN', 'cuisine'))
    if property_obj.bathroom_count:
        required_categories.append(('BATHROOM', 'salle de bain'))
    if property_obj.toilet_count:
        required_categories.append(('TOILET', 'toilette'))
    for category, label in required_categories:
        if not photos.filter(category=category).exists():
            missing.append((f'photo_{category.lower()}', f'Ajoutez au moins une photo pour chaque {label}.'))
    declaration = getattr(publication, 'declaration', None)
    consent = getattr(publication, 'collaboration_consent', None)
    if not declaration or not declaration.accepted_at:
        missing.append(('declaration', 'La déclaration du propriétaire doit être entièrement acceptée.'))
    if not consent or not consent.accepted_at:
        missing.append(('consentement', 'Les conditions de collaboration avec Fasthome doivent être entièrement acceptées.'))
    return missing


@login_required
def my_properties(request):
    properties = (Property.objects.filter(owner=request.user).select_related('property_type', 'publication').prefetch_related('photos').order_by('-updated_at', '-created_at'))
    counts = {
        'all': properties.count(),
        'available': properties.filter(status='AVAILABLE').count(),
        'review': properties.filter(Q(status='UNDER_REVIEW') | Q(publication__status__in=['SUBMITTED', 'UNDER_REVIEW'])).distinct().count(),
        'draft': properties.filter(Q(publication__isnull=True) | Q(publication__status='DRAFT')).distinct().count(),
        'rented': properties.filter(Q(status='RENTED') | Q(publication__status='RENTED')).distinct().count(),
    }
    visits = (VisitRequest.objects.filter(property__owner=request.user)
              .select_related('property', 'property__property_type', 'requester')
              .prefetch_related('property__photos')
              .order_by('requested_date', 'requested_time_slot', '-created_at')[:6])
    rented_properties = (properties.filter(Q(status='RENTED') | Q(publication__status='RENTED'))
                         .prefetch_related('photos')[:6])
    return render(request, 'dashboard/my_properties.html', {
        'properties': properties,
        'counts': counts,
        'visits': visits,
        'rented_properties': rented_properties,
    })


@login_required
def property_manage(request, property_id):
    property_obj = get_object_or_404(Property.objects.filter(owner=request.user).select_related('property_type', 'publication').prefetch_related('photos', 'features'), property_id=property_id)
    publication = getattr(property_obj, 'publication', None)
    visit_requests = VisitRequest.objects.filter(property=property_obj).order_by('-created_at')[:10]
    checklist = _publication_checklist(property_obj, publication) if publication else [('publication', 'La publication n’existe pas encore.')]
    return render(request, 'dashboard/property_manage.html', {'property': property_obj, 'publication': publication, 'photos': property_obj.photos.all().order_by('order', 'id'), 'visit_requests': visit_requests, 'checklist': checklist, 'ready_for_submission': not checklist and publication and publication.status in {'DRAFT', 'CORRECTION_REQUIRED'}})


@login_required
def property_review(request, property_id):
    property_obj = get_object_or_404(Property.objects.filter(owner=request.user).select_related('property_type', 'publication'), property_id=property_id)
    publication = get_object_or_404(PropertyPublication, property=property_obj)
    checklist = _publication_checklist(property_obj, publication)
    return render(request, 'dashboard/property_review.html', {'property': property_obj, 'publication': publication, 'checklist': checklist, 'ready_for_submission': not checklist and publication.status in {'DRAFT', 'CORRECTION_REQUIRED'}})


@login_required
@require_POST
def property_submit(request, property_id):
    with transaction.atomic():
        property_obj = get_object_or_404(Property.objects.select_for_update().filter(owner=request.user).select_related('publication', 'property_type'), property_id=property_id)
        publication = get_object_or_404(PropertyPublication.objects.select_for_update(), property=property_obj)
        if publication.status not in {'DRAFT', 'CORRECTION_REQUIRED'} or property_obj.status != 'DRAFT':
            messages.error(request, 'Cette publication ne peut plus être envoyée dans son état actuel.')
            return redirect('property_manage', property_id=property_id)
        missing = _publication_checklist(property_obj, publication)
        if missing:
            messages.error(request, 'La publication n’est pas prête. Corrigez les éléments indiqués avant de l’envoyer.')
            return redirect('property_review', property_id=property_id)
        now = timezone.now()
        publication.status = 'UNDER_REVIEW'
        publication.submitted_at = now
        publication.correction_message = ''
        publication.save(update_fields=['status', 'submitted_at', 'correction_message', 'updated_at'])
        property_obj.status = 'UNDER_REVIEW'
        property_obj.save(update_fields=['status', 'updated_at'])
        publication_submitted(publication)
    messages.success(request, 'Votre publication est maintenant en cours de vérification par Fasthome.')
    return redirect('property_manage', property_id=property_id)


@login_required
@require_POST
def property_delete_draft(request, property_id):
    with transaction.atomic():
        property_obj = get_object_or_404(Property.objects.select_for_update().filter(owner=request.user), property_id=property_id)
        publication = getattr(property_obj, 'publication', None)
        if not publication or publication.status != 'DRAFT' or property_obj.status != 'DRAFT':
            messages.error(request, 'Seul un véritable brouillon peut être supprimé.')
            return redirect('property_manage', property_id=property_id)
        property_obj.delete()
    messages.success(request, 'Le brouillon a été supprimé définitivement.')
    return redirect('my_properties')

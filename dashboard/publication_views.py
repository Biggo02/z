from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test

from notifications.services import publication_approved, publication_correction_required
from properties.models import Property, PropertyPublication


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)


@staff_required
def office_publications(request):
    publications = (PropertyPublication.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW', 'CORRECTION_REQUIRED']).select_related('property', 'property__owner', 'property__property_type').order_by('-submitted_at', '-created_at'))
    return render(request, 'dashboard/office_publications.html', {'publications': publications})


@staff_required
@require_POST
def office_publication_decision(request, publication_id):
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()
    with transaction.atomic():
        publication = get_object_or_404(PropertyPublication.objects.select_for_update().select_related('property', 'property__owner'), publication_id=publication_id)
        if publication.status not in {'SUBMITTED', 'UNDER_REVIEW', 'CORRECTION_REQUIRED'}:
            messages.error(request, 'Cette publication n’est plus modifiable dans son état actuel.')
            return redirect('office_publications')
        if action == 'approve':
            declaration = getattr(publication, 'declaration', None)
            consent = getattr(publication, 'collaboration_consent', None)
            property_obj = Property.objects.select_for_update().get(pk=publication.property_id)
            if not declaration or not declaration.accepted_at or not consent or not consent.accepted_at:
                messages.error(request, 'Les déclarations et consentements obligatoires doivent être validés avant publication.')
                return redirect('office_publications')
            if property_obj.status != 'UNDER_REVIEW':
                messages.error(request, 'Le logement doit être en vérification avant publication.')
                return redirect('office_publications')
            publication.status = 'PUBLISHED'; publication.approved_at = timezone.now(); publication.published_at = timezone.now(); publication.correction_message = ''
            publication.save(update_fields=['status', 'approved_at', 'published_at', 'correction_message', 'updated_at'])
            property_obj.status = 'AVAILABLE'; property_obj.save(update_fields=['status', 'updated_at'])
            publication_approved(publication)
            messages.success(request, f'Publication {publication.publication_id} publiée.')
        elif action == 'correction':
            if not reason:
                messages.error(request, 'Indiquez les corrections demandées au propriétaire.')
                return redirect('office_publications')
            publication.status = 'CORRECTION_REQUIRED'; publication.correction_message = reason
            publication.save(update_fields=['status', 'correction_message', 'updated_at'])
            property_obj = Property.objects.select_for_update().get(pk=publication.property_id)
            property_obj.status = 'DRAFT'; property_obj.save(update_fields=['status', 'updated_at'])
            publication_correction_required(publication, reason)
            messages.success(request, 'Demande de correction envoyée au propriétaire.')
        else:
            messages.error(request, 'Action de publication invalide.')
    return redirect('office_publications')

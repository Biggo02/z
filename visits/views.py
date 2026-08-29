from datetime import date
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from leasing.models import RentalCase
from notifications.services import (
    visit_requested, visit_landlord_approved, visit_landlord_refused,
    visit_fasthome_approved, visit_fasthome_refused, visit_confirmed,
    visit_completed, rental_case_created,
)
from properties.models import Property
from .models import VisitRequest

MAX_ACTIVE_VISITS_PER_TENANT = 2


def _staff_required(request):
    return request.user.is_active and request.user.is_staff


@login_required
@require_http_methods(['GET', 'POST'])
def request_visit(request, property_id):
    prop = get_object_or_404(Property, property_id=property_id, status='AVAILABLE')

    if request.method == 'GET':
        return render(request, 'visits/request_visit.html', {
            'property': prop,
            'today': timezone.localdate(),
        })

    if not request.user.is_certified:
        messages.error(request, 'Un compte certifié est nécessaire pour demander une visite.')
        return redirect('property_detail', property_id=property_id)

    requested_date = request.POST.get('requested_date', '').strip()
    try:
        parsed_date = date.fromisoformat(requested_date)
    except ValueError:
        messages.error(request, 'La date de visite est invalide.')
        return redirect('request_visit', property_id=property_id)

    if parsed_date < timezone.localdate():
        messages.error(request, 'La date de visite doit être aujourd’hui ou dans le futur.')
        return redirect('request_visit', property_id=property_id)

    with transaction.atomic():
        requester = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        prop = get_object_or_404(Property.objects.select_for_update(), property_id=property_id, status='AVAILABLE')
        if prop.owner_id == requester.pk:
            messages.error(request, 'Vous ne pouvez pas demander une visite de votre propre logement.')
            return redirect('property_detail', property_id=property_id)
        active_count = VisitRequest.objects.filter(requester=requester, status__in=['REQUESTED', 'CONFIRMED']).count()
        if active_count >= MAX_ACTIVE_VISITS_PER_TENANT:
            messages.error(request, 'Vous pouvez avoir au maximum deux demandes de visite actives à la fois.')
            return redirect('activity')
        if VisitRequest.objects.filter(property=prop, requester=requester, status__in=['REQUESTED', 'CONFIRMED']).exists():
            messages.error(request, 'Vous avez déjà une demande de visite active pour ce logement.')
            return redirect('property_detail', property_id=property_id)
        visit = VisitRequest.objects.create(
            property=prop,
            requester=requester,
            requested_date=parsed_date,
            requested_time_slot=request.POST.get('requested_time_slot', '').strip()[:80],
        )
        visit_requested(visit)
        messages.success(request, f'Demande {visit.visit_id} envoyée à Fasthome et au bailleur.')
    return redirect('property_detail', property_id=prop.property_id)


@login_required
@require_http_methods(['POST'])
def fasthome_visit_decision(request, visit_id):
    if not _staff_required(request):
        messages.error(request, 'Accès réservé aux intervenants Fasthome autorisés.')
        return redirect('activity')
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property', 'requester'), visit_id=visit_id, status='REQUESTED')
        action = request.POST.get('action')
        if action == 'approve':
            visit.fasthome_approved = True
            if visit.landlord_approved:
                visit.status = 'CONFIRMED'
            visit.save(update_fields=['fasthome_approved', 'status'])
            if visit.status == 'CONFIRMED':
                visit_confirmed(visit)
            else:
                visit_fasthome_approved(visit)
        elif action == 'refuse':
            visit.status = 'REFUSED'
            visit.save(update_fields=['status'])
            visit_fasthome_refused(visit)
        else:
            messages.error(request, 'Action de visite invalide.')
            return redirect('activity')
    return redirect('activity')


@login_required
@require_http_methods(['POST'])
def landlord_visit_decision(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property', 'requester'), visit_id=visit_id, property__owner=request.user)
        if visit.status != 'REQUESTED':
            messages.error(request, 'Cette demande de visite n’est plus en attente.')
            return redirect('activity')
        action = request.POST.get('action')
        if action == 'approve':
            visit.landlord_approved = True
            if visit.fasthome_approved:
                visit.status = 'CONFIRMED'
            visit.save(update_fields=['landlord_approved', 'status'])
            if visit.status == 'CONFIRMED':
                visit_confirmed(visit)
            else:
                visit_landlord_approved(visit)
        elif action == 'refuse':
            visit.status = 'REFUSED'
            visit.save(update_fields=['status'])
            visit_landlord_refused(visit)
        else:
            messages.error(request, 'Action de visite invalide.')
            return redirect('activity')
    return redirect('activity')


@login_required
@require_http_methods(['POST'])
def mark_visit_completed(request, visit_id):
    if not _staff_required(request):
        messages.error(request, 'Seuls les intervenants Fasthome autorisés peuvent clôturer une visite.')
        return redirect('activity')
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update(), visit_id=visit_id, status='CONFIRMED')
        visit.status = 'COMPLETED'
        visit.completed_at = timezone.now()
        visit.completed_by = request.user
        visit.save(update_fields=['status', 'completed_at', 'completed_by'])
        visit_completed(visit)
    return redirect('activity')


@login_required
@require_http_methods(['POST'])
def tenant_decision(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property'), visit_id=visit_id, requester=request.user, status='COMPLETED')
        action = request.POST.get('action')
        if action == 'take':
            case, created = RentalCase.objects.get_or_create(visit=visit, defaults={'property': visit.property, 'tenant': request.user, 'status': 'OPEN'})
            if not created:
                messages.info(request, f'Votre dossier {case.case_id} existe déjà.')
                return redirect('activity')
            visit.property.status = 'UNDER_REVIEW'
            visit.property.save(update_fields=['status', 'updated_at'])
            rental_case_created(case)
            messages.success(request, 'Votre choix a été enregistré. Fasthome traite maintenant votre dossier.')
            return redirect('activity')
        if action == 'decline':
            messages.success(request, 'Votre décision de ne pas prendre le logement a été enregistrée.')
            return redirect('activity')
        messages.error(request, 'Choix invalide.')
    return redirect('activity')

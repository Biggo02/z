import calendar
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from properties.models import Favorite, Property
from visits.models import VisitRequest
from visits.views import (
    visit_fasthome_approved, visit_fasthome_refused, visit_confirmed, visit_completed,
)
from leasing.models import RentalCase, Lease, RenewalRequest, LeaseExit
from contracts.models import Contract
from inspections.models import InspectionReport
from payments.models import PaymentReceipt, LandlordPayout, RentInstallment
from notifications.models import Notification
from notifications.services import contract_created, contract_uploaded, contract_validated, inspection_validated, payment_recorded, payout_completed, lease_officialized, rental_case_accepted
from users.models import IdentityVerification, User
from .office_forms import ReceiptForm, PayoutForm


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)

def admin_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_superuser)(view)

def _next_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))

def _ensure_next_installment(lease, from_installment=None):
    due_date = _next_month(from_installment.due_date) if from_installment is not None else (lease.start_date or timezone.localdate())
    installment, _ = RentInstallment.objects.get_or_create(lease=lease, due_date=due_date, defaults={'amount_due': lease.monthly_rent, 'status': 'UPCOMING'})
    return installment

@login_required
def favorites(request):
    items = (Favorite.objects.filter(user=request.user).select_related('property', 'property__property_type', 'property__owner').prefetch_related('property__photos').order_by('-created_at'))
    return render(request, 'dashboard/favorites.html', {'items': items})

@login_required
@require_POST
def toggle_favorite(request, property_id):
    prop = get_object_or_404(Property.objects.only('pk', 'property_id'), property_id=property_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, property=prop)
    if not created: favorite.delete()
    liked = created
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    if wants_json: return JsonResponse({'success': True, 'liked': liked, 'property_id': prop.property_id})
    messages.success(request, 'Logement ajouté aux favoris.' if liked else 'Logement retiré des favoris.')
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home')

@login_required
def notifications(request):
    qs = request.user.notifications.all().order_by('-created_at')
    unread_count = qs.filter(is_read=False).count()
    items = list(qs[:100])
    return render(request, 'dashboard/notifications.html', {'items': items, 'unread_count': unread_count})

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, notification_id=notification_id, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return JsonResponse({'success': True, 'unread_count': request.user.notifications.filter(is_read=False).count()})

@login_required
@require_POST
def mark_all_notifications_read(request):
    updated = request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True, 'updated': updated, 'unread_count': 0})

@login_required
def notification_unread_count(request):
    return JsonResponse({'success': True, 'unread_count': request.user.notifications.filter(is_read=False).count()})

@login_required
def activity(request):
    visits = request.user.visit_requests.select_related('property', 'property__property_type').prefetch_related('property__photos').order_by('-created_at')[:20]
    landlord_visits = VisitRequest.objects.filter(property__owner=request.user, status='REQUESTED').select_related('property', 'property__property_type').order_by('-created_at')[:20]
    cases = request.user.rental_cases_as_tenant.select_related('property', 'property__property_type', 'visit').order_by('-created_at')[:20]
    leases = request.user.leases_as_tenant.select_related('property', 'property__property_type', 'landlord').order_by('-created_at')[:20]
    properties = request.user.properties.select_related('property_type', 'publication').prefetch_related('photos').order_by('-created_at')[:20]
    landlord_leases = request.user.leases_as_landlord.select_related('property', 'property__property_type', 'tenant').order_by('-created_at')[:20]
    return render(request, 'dashboard/activity.html', {'visits': visits, 'landlord_visit_requests': landlord_visits, 'cases': cases, 'leases': leases, 'properties': properties, 'landlord_leases': landlord_leases})

@login_required
def visits_page(request):
    visits = request.user.visit_requests.select_related('property', 'property__property_type').prefetch_related('property__photos').order_by('-created_at')[:50]
    landlord_visit_requests = VisitRequest.objects.filter(property__owner=request.user).select_related('property', 'property__property_type').prefetch_related('property__photos').order_by('-created_at')[:50]
    return render(request, 'dashboard/visits.html', {'visits': visits, 'landlord_visit_requests': landlord_visit_requests})

@login_required
def lease_detail(request, lease_id):
    lease = get_object_or_404(Lease.objects.select_related('property', 'property__property_type', 'tenant', 'landlord'), lease_id=lease_id)
    if not (request.user.is_staff or request.user.is_superuser or request.user.pk in {lease.tenant_id, lease.landlord_id}): return redirect('activity')
    contracts = lease.contracts.all().select_related('lease')
    reports = lease.inspection_reports.all().select_related('property')
    installments = lease.installments.all().order_by('due_date')
    receipts = lease.payment_receipts.all().order_by('-received_at')
    payouts = lease.landlord_payouts.all().order_by('-paid_at')
    return render(request, 'dashboard/lease_detail.html', {'lease': lease, 'contracts': contracts, 'reports': reports, 'installments': installments, 'receipts': receipts, 'payouts': payouts})

@staff_required
def office_dashboard(request):
    return render(request, 'dashboard/office.html', {'pending_publications': Property.objects.filter(publication__status__in=['SUBMITTED', 'UNDER_REVIEW', 'CORRECTION_REQUIRED']).count(), 'pending_verifications': IdentityVerification.objects.filter(status__in=['PENDING', 'IN_REVIEW', 'RETRY']).count(), 'pending_visits': VisitRequest.objects.filter(status='REQUESTED').count(), 'cases': RentalCase.objects.filter(status__in=['OPEN', 'UNDER_REVIEW']).count(), 'pending_contracts': Contract.objects.filter(status__in=['PENDING', 'UPLOADED']).count(), 'pending_reports': InspectionReport.objects.filter(status='DRAFT').count(), 'lifecycle_requests': RenewalRequest.objects.filter(status='REQUESTED').count() + LeaseExit.objects.filter(status='REQUESTED').count(), 'payments': PaymentReceipt.objects.count(), 'payouts': LandlordPayout.objects.count(), 'is_admin': request.user.is_superuser})

@admin_required
def office_users(request):
    users = User.objects.order_by('-created_at')[:250]
    return render(request, 'dashboard/office_users.html', {'users': users})

@staff_required
@require_POST
def office_approve_visit(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property', 'requester'), visit_id=visit_id)
        if visit.status != 'REQUESTED': messages.error(request, 'Cette demande de visite n’est plus en attente.'); return redirect('office_visits')
        if request.POST.get('action') == 'approve':
            visit.fasthome_approved = True
            if visit.landlord_approved: visit.status = 'CONFIRMED'
            visit.save(update_fields=['fasthome_approved', 'status'])
            if visit.status == 'CONFIRMED': visit_confirmed(visit)
            else: visit_fasthome_approved(visit)
        elif request.POST.get('action') == 'refuse':
            visit.status = 'REFUSED'; visit.save(update_fields=['status']); visit_fasthome_refused(visit)
        else: messages.error(request, 'Action invalide.'); return redirect('office_visits')
    return redirect('office_visits')

@staff_required
@require_POST
def office_complete_visit(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property', 'requester'), visit_id=visit_id)
        if visit.status != 'CONFIRMED': messages.error(request, 'La visite n’est plus confirmée.'); return redirect('office_visits')
        visit.status = 'COMPLETED'; visit.completed_at = timezone.now(); visit.completed_by = request.user; visit.save(update_fields=['status', 'completed_at', 'completed_by']); visit_completed(visit)
    return redirect('office_visits')

@staff_required
def office_visits(request):
    visits = VisitRequest.objects.select_related('property', 'property__property_type', 'requester').prefetch_related('property__photos').order_by('-created_at')
    return render(request, 'dashboard/office_visits.html', {'visits': visits})

@staff_required
def office_cases(request):
    cases = RentalCase.objects.select_related('property', 'property__property_type', 'tenant', 'visit').order_by('-created_at')
    return render(request, 'dashboard/office_cases.html', {'cases': cases})

@staff_required
@require_POST
def office_accept_case(request, case_id):
    with transaction.atomic():
        case = get_object_or_404(RentalCase.objects.select_for_update().select_related('property', 'tenant', 'visit'), case_id=case_id)
        if case.status not in {'OPEN', 'UNDER_REVIEW'} or case.visit.status != 'COMPLETED': messages.error(request, 'Ce dossier n’est pas éligible à la contractualisation.'); return redirect('office_cases')
        property_obj = Property.objects.select_for_update().select_related('owner').get(pk=case.property_id)
        active_lease_exists = Lease.objects.filter(property_id=property_obj.pk, status__in=['PENDING', 'ACTIVE', 'RENEWAL', 'TERMINATION']).exists()
        if active_lease_exists: messages.error(request, 'Ce logement fait déjà l’objet d’une location en cours de contractualisation ou active.'); return redirect('office_cases')
        lease, _ = Lease.objects.select_for_update().get_or_create(rental_case=case, defaults={'property': property_obj, 'tenant': case.tenant, 'landlord': property_obj.owner, 'monthly_rent': property_obj.monthly_rent or Decimal('0'), 'guarantee_amount': property_obj.guarantee_amount, 'status': 'PENDING'})
        tenant_contract, tenant_created = Contract.objects.get_or_create(lease=lease, contract_type='TENANT')
        landlord_contract, landlord_created = Contract.objects.get_or_create(lease=lease, contract_type='LANDLORD')
        if tenant_created: contract_created(tenant_contract)
        if landlord_created: contract_created(landlord_contract)
        InspectionReport.objects.get_or_create(lease=lease, property=lease.property, report_type='ENTRY', defaults={'status': 'DRAFT'})
        case.status = 'CONTRACTING'; case.save(update_fields=['status']); rental_case_accepted(case)
    return redirect('office_cases')

@staff_required
def office_contracts(request):
    contracts = Contract.objects.select_related('lease', 'lease__property', 'lease__property__property_type', 'lease__tenant', 'lease__landlord').order_by('-contract_id')
    return render(request, 'dashboard/office_contracts.html', {'contracts': contracts})

@staff_required
@require_POST
def office_contract_upload(request, contract_id):
    contract = get_object_or_404(Contract, contract_id=contract_id)
    if not request.FILES.get('signed_document'): messages.error(request, 'Aucun document signé fourni.'); return redirect('office_contracts')
    with transaction.atomic():
        contract = Contract.objects.select_for_update().get(pk=contract.pk)
        if contract.status not in {'PENDING', 'REJECTED'}: messages.error(request, 'Ce contrat ne peut plus être téléversé.'); return redirect('office_contracts')
        contract.signed_document = request.FILES['signed_document']; contract.status = 'UPLOADED'; contract.uploaded_at = timezone.now(); contract.uploaded_by = request.user; contract.save(); contract_uploaded(contract)
    return redirect('office_contracts')

@staff_required
@require_POST
def office_contract_validate(request, contract_id):
    with transaction.atomic():
        contract = get_object_or_404(Contract.objects.select_for_update(), contract_id=contract_id)
        if contract.status != 'UPLOADED' or not contract.signed_document or not contract.uploaded_by_id: messages.error(request, 'Ce contrat ne peut pas être validé.'); return redirect('office_contracts')
        contract.status = 'VALIDATED'; contract.signed_at = timezone.now(); contract.save(update_fields=['status', 'signed_at']); contract_validated(contract)
    return redirect('office_contracts')

@staff_required
def office_reports(request):
    reports = InspectionReport.objects.select_related('lease', 'lease__property', 'property', 'property__property_type').order_by('-created_at')
    return render(request, 'dashboard/office_reports.html', {'reports': reports})

@staff_required
@require_POST
def office_report_validate(request, report_id):
    with transaction.atomic():
        report = get_object_or_404(InspectionReport.objects.select_for_update(), report_id=report_id)
        if report.status != 'DRAFT': messages.error(request, 'Ce PV n’est plus en brouillon.'); return redirect('office_reports')
        report.status = 'VALIDATED'; report.save(update_fields=['status']); inspection_validated(report)
    return redirect('office_reports')

@staff_required
@require_POST
def office_officialize_lease(request, lease_id):
    with transaction.atomic():
        lease = get_object_or_404(Lease.objects.select_for_update().select_related('rental_case'), lease_id=lease_id)
        if lease.status != 'PENDING': messages.error(request, 'Cette location n’est plus en attente.'); return redirect('office_dashboard')
        contracts = list(lease.contracts.all()); reports = list(lease.inspection_reports.filter(report_type='ENTRY'))
        if len([c for c in contracts if c.status == 'VALIDATED']) != 2 or not any(r.status == 'VALIDATED' for r in reports): messages.error(request, 'Les deux contrats et le PV d’entrée doivent être validés.'); return redirect('office_dashboard')
        property_obj = Property.objects.select_for_update().get(pk=lease.property_id); lease.status = 'ACTIVE'; lease.save(update_fields=['status']); property_obj.status = 'RENTED'; property_obj.save(update_fields=['status', 'updated_at']); _ensure_next_installment(lease); lease_officialized(lease)
    return redirect('office_dashboard')

@staff_required
@require_POST
def office_receipt(request):
    form = ReceiptForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            installment = RentInstallment.objects.select_for_update().get(pk=form.cleaned_data['installment'].pk)
            receipt = form.save(commit=False); receipt.installment = installment; receipt.lease = installment.lease; receipt.recorded_by = request.user; receipt.save(); installment.refresh_from_db(); payment_recorded(receipt)
            if installment.status == 'PAID': _ensure_next_installment(installment.lease, installment)
        return redirect('office_dashboard')
    return render(request, 'dashboard/office_receipt.html', {'form': form})

@staff_required
@require_POST
def office_payout(request):
    form = PayoutForm(request.POST or None)
    if request.method == 'POST' and form.is_valid(): payout = form.save(commit=True); payout_completed(payout); return redirect('office_dashboard')
    return render(request, 'dashboard/office_payout.html', {'form': form})

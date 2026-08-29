from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from notifications.services import verification_in_review, verification_decided
from users.models import IdentityVerification, IdentityVerificationEvent


def kyc_staff_required(view):
    return user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or (u.is_staff and u.can_review_kyc))
    )(view)


def _get_accessible_verification(verification_id, user):
    queryset = IdentityVerification.objects.select_related('user', 'assigned_reviewer', 'analysis')
    if user.is_superuser:
        return get_object_or_404(queryset, pk=verification_id)
    return get_object_or_404(queryset, pk=verification_id, assigned_reviewer=user, user__isnull=False)


@kyc_staff_required
def office_verifications(request):
    queryset = (
        IdentityVerification.objects.select_related('user', 'analysis', 'assigned_reviewer')
        .prefetch_related('events')
        .filter(status__in=['PENDING', 'IN_REVIEW', 'RETRY', 'REJECTED'])
        .order_by('submitted_at')
    )
    if not request.user.is_superuser:
        queryset = queryset.filter(assigned_reviewer=request.user)
    return render(request, 'dashboard/office_verifications.html', {'verifications': queryset})


@kyc_staff_required
@require_GET
def office_verification_document(request, verification_id):
    verification = _get_accessible_verification(verification_id, request.user)
    try:
        document = verification.document_file
        if not document or not document.name:
            raise Http404('Document introuvable.')
        document.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404('Document introuvable.')
    IdentityVerificationEvent.objects.create(
        verification=verification,
        actor=request.user,
        event_type='DOCUMENT_ACCESSED',
        from_status=verification.status,
        to_status=verification.status,
        from_facial_status=verification.facial_status,
        to_facial_status=verification.facial_status,
        reason='Consultation du document par un agent/admin.',
    )
    return FileResponse(document, as_attachment=True, filename=document.name.rsplit('/', 1)[-1])


@kyc_staff_required
@require_POST
def office_verification_decision(request, verification_id):
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()
    with transaction.atomic():
        verification = _get_accessible_verification(verification_id, request.user)
        verification = IdentityVerification.objects.select_for_update().select_related('user', 'assigned_reviewer', 'analysis').get(pk=verification.pk)
        old_status = verification.status
        old_face = verification.facial_status

        if action == 'verify_document':
            verification.status = 'VERIFIED'
            verification.verified_at = None
            if verification.facial_status in {'RETRY', 'VERIFIED'}:
                verification.facial_status = 'PENDING'
            message = 'Document validé manuellement.'

        elif action == 'verify_face':
            if verification.status != 'VERIFIED':
                messages.error(request, 'Validez d’abord la pièce d’identité.')
                return redirect('office_verifications')
            if not verification.facial_photo:
                messages.error(request, 'Aucune photo faciale n’est enregistrée.')
                return redirect('office_verifications')
            verification.facial_status = 'VERIFIED'
            verification.verified_at = timezone.now()
            message = 'Vérification faciale validée manuellement.'

        elif action == 'reject':
            if not reason:
                messages.error(request, 'Indiquez le motif du refus.')
                return redirect('office_verifications')
            verification.status = 'RETRY'
            verification.facial_status = 'RETRY'
            verification.rejection_reason = reason
            verification.verified_at = None
            message = 'Dossier refusé avec motif.'

        else:
            messages.error(request, 'Action de certification invalide.')
            return redirect('office_verifications')

        verification.save()
        IdentityVerificationEvent.objects.create(
            verification=verification,
            actor=request.user,
            event_type='MANUAL_DECISION',
            from_status=old_status,
            to_status=verification.status,
            from_facial_status=old_face,
            to_facial_status=verification.facial_status,
            reason=reason or message,
            metadata={'action': action},
        )
        verification_decided(verification, verification.user.is_certified, reason=reason)
    messages.success(request, message)
    return redirect('office_verifications')
